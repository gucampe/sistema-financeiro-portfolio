# Análise de arquitetura: importação de extratos bancários em PDF

**Data de criação:** 21 de agosto de 2026  
**Atualizado em:** 22 de agosto de 2026  
**Status:** estado da arte da análise — **sem implementação**  
**Produto:** GranaGo  

Documento canônico desta feature. Medições de laboratório estão em [`ANALISE_SPIKE_IMPORTACAO_PDF.md`](ANALISE_SPIKE_IMPORTACAO_PDF.md) e nos scripts em `docs/arquitetura/spike_importacao_pdf/`. PDFs bancários reais **não** entram no git.

O spike registrou hipóteses anteriores (Celery no v1, lib em aberto). **Este arquivo prevalece** onde houver conflito.

Trata a feature como:

> um pipeline seguro de transformação de um documento bancário altamente sensível em um conjunto mínimo de transações necessárias ao GranaGo.

Não como “um leitor de PDF” nem como “um detector de tabela de biblioteca”.

Prioridade: (1) segurança e privacidade, (2) correção financeira, (3) minimização, (4) confiabilidade, (5) vários layouts, (6) performance, (7) UX.

Afirmações abaixo distinguem **requisito técnico**, **boa prática de segurança** e **ponto jurídico**. Isto **não** substitui revisão jurídica profissional.

---

## 1. Parecer de viabilidade

**A feature é viável para produção incremental. Não é viável como “chamar detector de tabela e importar”.**

Foram medidos **6 PDFs reais** (anexos locais, sem PII neste repositório):

| PDF | Tipo | Transações localizáveis sem OCR? | Como |
| --- | --- | --- | --- |
| Santander (11 p., ~208 KB, dossiê Compart) | digital | Sim | `dd/mm` sem ano + valor na mesma faixa Y |
| Bradesco (5 p., ~17 KB) | digital | Sim | cabeçalhos C/D/saldo; duas colunas de data; Y mais folgado |
| Nubank (2 p., ~23 KB, HTML→PDF) | digital | Sim | data = dia + mês por extenso como **cabeçalho de grupo**; valores herdam a data |
| Nubank (5 p., ~37 KB, HTML→PDF) | digital | Sim | mesma família; 61 candidatos no interpretador do spike (4 libs empatam) |
| Caixa (1 p., ~367 KB) | **raster** (JPEG 1957×3230, zero texto) | Não no v1 | recusar; sugerir OFX/Excel |
| Comprovante 2 p. (~981 KB) | **raster** (2× JPEG 1957×3230, pdfmake) | Não no v1 | mesmo padrão do Caixa; recusar |

Nos seis, `find_tables()` / `extract_tables()` **não devolveram a lista de lançamentos**. Nos quatro digitais o texto está lá; o caminho é **palavras + coordenadas**. Os dois rasters são foto da página (pdfmake).

**Não prometer “todos os bancos do Brasil”.** Prometer: PDF com texto, revisão humana, recusa de imagem, famílias de data (`dd/mm` e cabeçalho de mês).

Há informação suficiente para **implementar o v1**. Não há spike de biblioteca pendente. Falta, no PR, micro-benchmark de RSS do pypdfium2 (o spike mediu tempo; pico de memória ficou para o código).

---

## 2. Decisão de produto: terceira origem do import atual

```text
OFX  ─┐
XLSX ─┼─► preview editável ─► categorização inteligente (opcional) ─► confirmar ─► Transacao
PDF  ─┘
```

Depois de extraído, o PDF usa o **mesmo contrato** que OFX e Excel: revisar, categorizar (pipeline híbrido atual, sob demanda), confirmar em `importar_ofx_confirmar`, mesmo ledger.

A extração é o único trecho novo. Unificar o botão “Importar extrato” fica para depois do v1.

Manter **`LinhaOfx`** no v1 (`ofx_fitid=None`). Não inventar FITID.

---

## 3. Dados: o mínimo necessário

Um comprovante consolidado **não** é só lançamentos. Encontrar no PDF não é motivo para extrair.

**Necessários para `Transacao`:** data, descrição da linha de movimentação (≤ 255), valor, direção, identificação da região de movimento (só no processamento).

**Só em memória:** saldo da **mesma** região, totais C/D, período, `layout_key`.

**Não no v1:** titular, agência/conta, ISPB, comprovantes TED/Pix detalhados, crédito, investimentos, perfil de risco.

**Terceiros:** na descrição, só o histórico da linha (como OFX). Strip de CPF/CNPJ. Não parsear seção de comprovantes.

---

## 4. Evidência do spike (o que mudou a hipótese)

Detalhe: [`ANALISE_SPIKE_IMPORTACAO_PDF.md`](ANALISE_SPIKE_IMPORTACAO_PDF.md) §§E–E5.

1. PDF digital ≠ PDF fácil. Detector de tabela da lib não é o produto.
2. Tabela detectada ≠ extração correta (sintético 05: células podres; pdfplumber ainda inventa o **valor** em `extract_words`).
3. Santander real: 27 tabelas, 0 linhas de movimento nelas; words em dezenas de ms.
4. **pypdfium2** (Apache/BSD) acerta o 05, empata com PyMuPDF nos 6 reais, abre **bytes**. PyMuPDF só com licença Artifex (AGPL). pdfplumber erra valor no 05. pypdf quebra nos reais. pdf-oxide (MIT, 0.3) fica como reserva, não v1.
5. `extract_text()` segue ordem de desenho. Ordenar palavras por `(y, x)` no espaço da página.
6. Logo ≠ scan. Scan = nenhuma página com texto extraível.

---

## 5. Arquitetura recomendada (v1)

### 5.1 Biblioteca

**Engine: `pypdfium2`.** Isolada atrás de uma camada que só devolve palavras + bounding boxes (origem top-left, ordem visual). O parser financeiro não importa PDFium direto.

Motivo: licença permissiva para SaaS fechado; no spike resolveu o caso em que o pdfplumber inventou o valor; nos 6 reais empatou com PyMuPDF. Atribuição Apache/NOTICE do wheel no deploy (compliance, não feature).

`find_tables` **desligado no default**.

### 5.2 Pipeline — síncrono, como OFX

**Revogado (22/08/2026):** Celery fila `imports` no v1; tempfile como caso normal; “Gunicorn não carrega a lib”.

Evidência de tempo com pypdfium2: Santander ~0,27 s; 40 páginas sintéticas ~0,7 s. OFX/XLSX já parseiam arquivo de usuário no request. Celery no v1 **piora privacidade** (precisaria persistir `linhas_json` para poll) e cria um terceiro fluxo de UX sem evidência de timeout.

```text
[UI] 3º botão Importar PDF → conta GranaGo + arquivo
        │
        ▼
Higiene no web (auth, CSRF, magic %PDF, ≤6 MB, ≤30 págs, senha, rate)
        │
        ▼
Bytes em memória (upload.read() / BytesIO)
  — pypdfium2 aceita bytes/stream/path
  — NÃO MEDIA_ROOT, NÃO S3, NÃO Redis, NÃO FileField
        │
        ▼
Parse síncrono no request (mesmo molde OFX)
  - nenhuma página com texto → SCANNED_PDF
  - senha / malformado → recusar
  - palavras + bbox, ordem (y, x)
  - propor regiões LÓGICAS (podem atravessar páginas)
  - classificar: movimento vs outro (investimento/cartão/comprovante ≠ opção)
  - 0 movimento → recusar
  - 1 movimento → preview
  - 2+ movimento → usuário escolhe UMA; nunca fundir; nunca pegar a maior
  - generic_table_v1 (registry; adapters vazios)
  - LinhaOfx[] + validação + estado do lote
  - fechar o PdfDocument no finally
        │
        ▼
JSON de preview (cliente) — igual OFX
        │
        ▼
Revisão → categorizar-import-batch (contexto import_pdf) → importar_ofx_confirmar
```

Tempfile `0700` **só** se alguma API futura exigir path. Janitor só se existir esse dir. Caso normal: nada em disco.

**Quando voltar a Celery:** P95 de extração > ~5–8 s, worker no `MemoryMax`, ou CVE de PDFium com blast no HTTP. Aí: fila `imports`, apagar PDF **antes** do `ready`, persistir só linhas + metadados técnicos, TTL curto. Não misturar com export WeasyPrint.

### 5.3 Contrato e categorização

Confirmar: `data`, `valor` ≥ 0, `tipo`, `descricao`, `ofx_fitid=None`.

Só no preview: `origem=pdf`, estado do lote, `parser_id`, `layout_key`, flags de duplicata. Sem `texto_bruto` no banco. Confirmar **não** reparseia o PDF.

Categorização: **nenhuma mudança de algoritmo**. Gemini, se ligado, continua com `redact_pii_for_llm` e **sem** o arquivo. Botão de IA sob demanda.

---

## 6. Scan, regiões, parser, fingerprint, adapters

### 6.1 Classe do documento

Classificar **por página** (tem texto / não tem). O documento é `SCANNED_PDF` só se **nenhuma** página tiver texto extraível. Páginas só-imagem no meio de um digital são ignoradas.

| Classe | Sinal | v1 |
| ------ | ----- | --- |
| `raster` | 0 páginas com texto e há imagem de página | recusar (`SCANNED_PDF`); UI pode citar foto/OFX/Excel |
| `textual_aligned` | colunas por X; datas e valores | **caminho principal** |
| `textual_tabular` | tabela da lib com linhas de movimento úteis | raro; não é o default |
| `textual_linear` | texto sem grade | recusar ou `baixa` |
| `encrypted` / `malformed` | flags | recusar |

Híbrido com pouquíssimo texto e o resto foto: **não** é `SCANNED_PDF`; cai em `NENHUMA_REGIAO_MOVIMENTO`. Mensagem pode mencionar também scan/foto. Sem threshold de densidade (`chars/página < 40` já mentiu no Santander).

PDF OCRizado ruim entra como textual; o preview e a confiança (`baixa`) são a rede. Texto invisível é risco residual.

### 6.2 Região = tabela lógica, não página

Sinais: geometria, alinhamento de colunas, cabeçalhos, datas, dinheiro, continuidade entre páginas, vocabulário positivo/negativo. Título de seção é **auxiliar**.

Mesma CC em 3 páginas, cabeçalho incompleto na seguinte (visto no Santander) = **uma** região (mesmos papéis + X relativo ±1 décimo + datas em sequência).

| Situação | v1 |
| -------- | -- |
| 0 movimento | recusar |
| 1 movimento | preview |
| CC + poupança | 2 opções; usuário escolhe; sem pré-seleção |
| CC + investimentos / cartão / comprovante | **não** oferecer; não é movimento de conta |
| Fatura de cartão | fora do v1 |

### 6.3 `generic_table_v1`

O nome não deve esconder que o núcleo é **palavras + colunas**, não `find_tables`. No lançamento o registry só tem esse interpreter.

**Obrigatório no v1:**

- `Data | Histórico | Valor` e `… | Valor | Saldo`
- `Data | Histórico | Débito | Crédito` (± saldo)
- valores BR; sinal
- `dd/mm` com ano do **período** do extrato
- descrição multilinha **sem** virar segundo lançamento
- **herança de data** (família Nubank: dia+mês como cabeçalho de grupo) — genérico de família, não `nubank.py`

**Fora:** cartão; direção só por cor; OCR.

**Errar com sucesso (prioridade de testes):** valor = saldo; tipo invertido; data/ano herdados errados; duas colunas de data (Bradesco); continuação da descrição com número; rodapé “saldo inicial/final”; investimento com várias colunas `valor`.

### 6.4 Fingerprint (`layout_key`)

Determinístico, sem ML, sem PII. No primeiro PR pode ser pobre (cabeçalhos ordenados + nº de colunas) só para log. Não escolhe parser enquanto o registry de adapters estiver vazio.

**Entram:** tokens de cabeçalho normalizados; papéis (DATE, DESC, DEBIT, CREDIT, AMOUNT, BALANCE); X relativo de DATE e AMOUNT em décimos da largura; família de data (`ddmm` vs `mes_extenso`).

**Não entram:** nome, agência, conta, CPF, Producer, logo, cor, marca do banco, texto de lançamento.

Exemplo: `h:data+historico+debito+credito+saldo|c5|x:date1,amt8|d:ddmm|v1`

Redesign de colunas → chave nova → genérico.

### 6.5 Adapters

**Zero no lançamento.** Primeiro adapter só com evidência: mesmo `layout_key` (ou família) em **≥ 3 PDFs de origens distintas**; erro repetível de **valor ou direção**; golden reproduz; corrigir no genérico pioraria outro layout. Não criar `santander.py` por um PDF.

---

## 7. Validação financeira, confiança, duplicatas

Reconciliação (`saldo_inicial + C − D = saldo_final` ± R$ 0,01) só âncora de **`alta`**, só com saldo da **região escolhida**. Pode fechar por coincidência (linha omitida, direções que se cancelam, saldo de outra seção).

Sem saldo → `media` se a estrutura ok (“não validamos”), não recusa. Saldo disponível / limite / aplicação **nunca** âncora. Direção não só por cor. Linha sem data ou valor parseável: incompleta, **não selecionável**.

Estados: `recusado` | `baixa` | `media` | `alta`. Sem score 0–1. Sempre preview. Sem auto-import. Importação parcial ok.

| Estado | UI |
| ------ | -- |
| `recusado` | sem feed; mensagem acionável (OFX, Excel, PDF com texto) |
| `alta` | completas pré-selecionadas |
| `media` | completas pré-selecionadas + aviso |
| `baixa` | desmarcadas; aviso com causa; **checkbox de ciência** (o feed OFX tem “marcar todos”) |

**Duplicata PDF×OFX no v1:** flag fraca `data+valor+tipo` só na origem PDF, no preview, desmarcada, usuário remarca. Sem unique no banco. Sem apagar. OFX/Excel **não** mudam a heurística (`data+valor+descrição`). Falso positivo (dois Pix iguais no dia) é aceitável.

---

## 8. Retenção, privacidade, logs

| Artefato | Persistir? |
| -------- | ---------- |
| PDF | Não (RAM do request; tempfile só se path for inevitável) |
| Texto integral / OCR | Não no v1 |
| Palavras+bbox | RAM; fim do request |
| Linhas | JSON no cliente até confirmar ou fechar o modal |
| `Transacao` | Sim, o que o usuário confirmou |
| Logs | códigos técnicos |
| Backup | PDF nunca |

Pergunta-guia de PR: *vazamento amanhã aumenta o que o atacante leva além das transações confirmadas?*

Logger `importacao.pdf` allowlist: `user_id`, `parser_id`, `layout_key`, `stage`, `error_code`, contagens, `duration_ms` (e RSS no micro-benchmark). Sem texto de célula. Sem attachment de PDF no Sentry.

Auditável para a Política (§3.3 no **go-live**, não neste desenho): nenhum FileField; após preview o temp está vazio; confirmar não reparseia; extração sem Gemini; batch de categoria só linhas; strip de CPF/CNPJ na descrição.

Base legal indicativa da Política atual para OFX: execução de contrato. **Não é parecer jurídico.** Encaminhar redação sobre terceiros; DPIA da extração se o risco mudar (hoje o stub é LLM de categoria). pypdfium2: NOTICE no deploy, não AGPL.

---

## 9. IA e limites

Extração local e determinística. Sem LLM/OCR no v1. Categorização = pipeline atual.

| Controle | v1 |
| -------- | -- |
| Auth / conta | `@login_required`; `Conta` ativa do dono |
| Tamanho / páginas / linhas | 6 MB; 30 páginas; 2000 linhas (espelho OFX) |
| Tipo | `.pdf` + magic `%PDF` |
| Senha / malformado / raster | recusar |
| Timeout extração | ~15–20 s no request (Gunicorn está em 120 s) |
| Rate | teto/hora (espelhar IA de categoria); 1 PDF em voo é desejável, não bloqueante |
| Isolamento | **request síncrono**; sem URL do arquivo |

Não executar JS de PDF.

---

## 10. Impacto no GranaGo atual

**Reutilizar:** `LinhaOfx`, `valor_e_tipo_de_importacao`, `_payload_preview_importacao`, `avaliar_duplicatas_importacao` (estender flag fraca **só** para origem PDF), `importar_ofx_confirmar`, feed OFX, `sugerir_batch`.

**Alterar:** terceiro botão + modal irmão; contexto `import_pdf`; Política §3.3 no lançamento; logger; flag `data+valor+tipo`.

**Criar:** `transacoes/importacao/pdf/` (ingest, extract/pypdfium2, region, interpret/generic, normalize, validate, errors). Fixtures sintéticos no git; reais anonimizados fora.

**Não criar no v1:** FileField, Celery task de import, OCR, LLM de extração, segundo confirmar, inferência de conta, `texto_bruto`, rename de `LinhaOfx`, adapters por banco.

Não migrar OFX para Celery.

---

## 11. Critérios de aceite (verificáveis)

- Nada do PDF em `MEDIA_ROOT` / Redis / backup; bytes liberados no `finally`.
- Golden 05: valor ≠ saldo; F1 identidade do gabarito.
- Golden 06: investimento não vaza se a região for CC.
- Mesma CC em duas páginas = uma região; CC+poupança = escolha.
- Raster e senha recusados; logs sem conteúdo do extrato.
- Preview + categoria + `importar_ofx_confirmar`; IA **não** recebe o PDF.
- `alta` só com reconciliação da região; `baixa` exige ciência; incompletas não selecionáveis.
- Flag fraca `data+valor+tipo` no preview PDF.
- `dd/mm` usa o ano do período; Nubank herda data de cabeçalho de grupo.
- Célula ilegível ≠ valor inventado.
- Extração não chama Gemini/OCR.
- Micro-benchmark: `duration_ms` + RSS de pico (40 p. sintético + um digital real anonimizado).

---

## 12. Fases

0. **Fundação (próximo passo de código):** higiene, pypdfium2 em bytes, words+bbox, genérico (incluindo herança de data e merge multipage), escolha de região, preview/confirmar/categoria, recusa raster/senha, logger, flag duplicata, ciência em `baixa`, goldens sintéticos, RSS no PR.  
1. Calibrar famílias (Y folgado Bradesco; Nubank) com reais anonimizados fora do git.  
2. Adapters só com falha sistemática de valor/direção.  
3. OCR local se a telemetria de `SCANNED_PDF` justificar.  
4. LLM de extração só com DPIA e default off.  
5. Botão único “Importar extrato”; Open Finance como alternativa.

---

## 13. O que não fazer

- FileField / mídia / S3 / Redis para o PDF.  
- Celery no v1 sem evidência de timeout/RSS/CVE.  
- pdfplumber ou pypdf como engine.  
- PyMuPDF sem licença comercial.  
- `find_tables` como verdade.  
- Auto-import; parser “Santander MVP”; fatura de cartão.  
- `ofx_fitid` sintético; inferir conta GranaGo; direção só por cor.  
- Tratar cada página como região independente.  
- Prometer na Política o que o código não faz.

---

## 14. Decisões desta versão (22/08/2026)

1. PDF = terceira origem; mesmo preview, mesma IA de categoria, mesmo confirmar.  
2. Engine **pypdfium2**; camada words+bbox; pdf-oxide reserva; PyMuPDF só com Artifex.  
3. **v1 síncrono** (bytes no request), como OFX. Celery revogado até haver evidência.  
4. Não persistir o PDF; tempfile só se path for inevitável; nunca Redis/mídia.  
5. Extração local; `find_tables` off; sem LLM/OCR na extração.  
6. Scan = nenhuma página com texto.  
7. Região = tabela lógica (pode cruzar página); 2+ movimento → perguntar; investimento não é opção.  
8. `generic_table_v1` com herança de data; zero adapters no lançamento. Manter `LinhaOfx`.  
9. Preview sempre; `baixa` com ciência; flag fraca `data+valor+tipo`.  
10. Feature **viável**; próximo passo é implementar, não novo spike de lib.

---

## 15. Ainda em aberto (não bloqueia o PR de fundação)

- RSS de pico do pypdfium2 em produção (medir no PR).  
- Gabarito humano de identidade em PDF real anonimizado (fora do git).  
- Volume de dossiê consolidado vs extrato curto.  
- Texto jurídico da §3.3 (go-live).

---

## 16. Fora do v1

Fatura de cartão; Open Finance; OCR/foto; detecção automática da conta; guardar comprovante; vários PDFs de uma vez; botão único de importação; Celery; adapters por banco.
