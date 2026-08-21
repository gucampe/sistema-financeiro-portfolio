# Análise de arquitetura: importação de extratos bancários em PDF

**Data de criação:** 21 de agosto de 2026  
**Status:** análise — sem implementação  
**Produto:** GranaGo

---

## 1. Objetivo

Permitir que o usuário envie um PDF de extrato bancário (em geral gerado pelo aplicativo do banco) e que o GranaGo transforme esse documento em transações financeiras estruturadas, com alto grau de confiabilidade:

- sem inventar lançamentos;
- sem perder movimentações reais;
- sem duplicar o que já está no ledger;
- com revisão humana sempre que a confiança for insuficiente.

O fluxo alvo é:

**Banco → app → gerar/baixar PDF → enviar ao GranaGo → extrato convertido em movimentações.**

Isso precisa funcionar de forma **ampla** (vários bancos e vários layouts), não como um parser pontual de um único banco.

---

## 2. Diagnóstico do GranaGo hoje

A importação já existe e é madura para formatos **estruturados**. O PDF não deve ser um terceiro parser “no mesmo estilo”; deve **desaguar no mesmo contrato** depois de extraído e validado.

### 2.1 O que já existe e deve ser reutilizado

| Peça | Onde | Papel |
|------|------|--------|
| Formato intermediário | `transacoes/ofx_parse.py` → `LinhaOfx` | `data`, `valor` (magnitude positiva), `tipo` (`receita`/`despesa`/`ajuste`), `descricao`, `ofx_fitid` opcional |
| Parser OFX | `parse_ofx_bytes` | Síncrono, em memória |
| Parser Excel | `transacoes/xlsx_parse.py` → `parse_planilha_padrao_bytes` | Layout **fixo** (`data \| descricao \| valor`); devolve a mesma `LinhaOfx` |
| Preview compartilhado | `_payload_preview_importacao` em `transacoes/views.py` | Linhas + flags de duplicata + categorias; **sem** categorização automática |
| Confirmação compartilhada | `importar_ofx_confirmar` | JSON do cliente; validação; `bulk_create` atômico; **não reparseia** o arquivo |
| Deduplicação | `transacoes/ofx_duplicatas.py` | FITID forte + heurística `data + valor + descrição normalizada` |
| UI de revisão | modal OFX/planilha no histórico | Conta → upload → preview editável → confirmar; IA de categoria é passo **opcional e posterior** |
| Jobs assíncronos | `ExportJob` + Celery (`relatorios/`) | Padrão de fila, status, TTL de arquivo, rate limit, dispatch `celery`/`thread`/`sync` |
| LLM já em produção | Gemini (`categorizacao/services/llm/`) | Só para **sugerir categoria**, com minimização forte de dados |
| Mídia protegida | `PROTECT_MEDIA` + ownership | Exports e fotos não são públicos |

Limites atuais relevantes: upload de 6 MB (`DATA_UPLOAD_MAX_MEMORY_SIZE` / `_MAX_OFX_BYTES` / `_MAX_XLSX_BYTES`); até **2000 linhas** por lote.

### 2.2 O que o PDF **não** pode herdar cegamente

1. **Sincronismo no request.** OFX/XLSX cabem no request HTTP. PDF com OCR, tabelas multipágina e fallback de modelo **não cabe**. Precisa de job, como os exports.
2. **Layout único.** A planilha só aceita um cabeçalho oficial. Extrato PDF não tem schema.
3. **FITID.** Quase nenhum PDF de banco brasileiro expõe identificador estável por lançamento. A deduplicação forte do OFX não existe aqui.
4. **Confiança binária.** OFX parseado ou falha. PDF pode “quase” funcionar: 47 de 48 linhas certas, uma descrição colada, um saldo que não fecha. Isso exige **estado de revisão**, não só preview.
5. **Política de LLM.** O DPIA atual (`docs/seguranca/DPIA_CATEGORIZACAO_LLM.md`) **proíbe** enviar arquivo bruto e valor exato ao Gemini. Mandar o PDF inteiro (ou a imagem do extrato) para um modelo de visão **quebra essa política**. Extração de lançamentos **não** pode reutilizar o mesmo contrato da categorização.

### 2.3 Modelo de dados atual (lacunas)

`Transacao` tem `ofx_fitid` (único por conta quando preenchido) e não tem:

- origem da importação (`ofx` / `xlsx` / `pdf` / `manual`);
- identificador de lote;
- hash do arquivo de origem;
- fingerprint sintético estável para PDF;
- metadados de confiança da extração.

`Conta` não tem banco, agência, número mascarado nem fingerprint institucional. O usuário escolhe a conta no upload; o sistema **não** infere a conta a partir do PDF (e não deve, no v1, para evitar gravar no lugar errado).

---

## 3. Princípios de produto e engenharia

1. **PDF é evidência, não verdade.** A verdade só existe depois de extração + interpretação + validação + (quando necessário) revisão humana.
2. **Não inventar.** Na dúvida, omitir a linha ou marcar para revisão. Nunca “completar” valor, data ou sentido (crédito/débito) por palpite.
3. **Não perder.** Se o saldo do extrato não fecha com as linhas extraídas, o lote **não** entra automaticamente.
4. **Um único ledger.** Depois de normalizado, o PDF usa o mesmo preview, a mesma confirmação e as mesmas regras de `Transacao` que OFX/Excel.
5. **Adapters são aceleradores, não o produto.** A arquitetura precisa funcionar para um banco **desconhecido**. Parsers por instituição vêm depois, para layouts que o caminho genérico falha.
6. **Reconciliação é o gate de qualidade.** Saldo inicial + movimentações = saldo final (com tolerância de R$ 0,01) é o critério objetivo de “deu certo”.
7. **Privacidade primeiro.** Extrato PDF contém CPF, agência, conta, endereço, PIX. Retenção curta, acesso autenticado, sem treinar modelo com dado do usuário, sem enviar documento bruto a terceiro sem base legal e opt-in explícitos.
8. **Revisão humana é feature, não falha.** Especialmente em OCR e em layouts novos.

---

## 4. Por que um parser por banco não escala

Layouts reais variam por:

- banco;
- produto (corrente, poupança, pagamento, cartão — **cartão fica fora do v1 de conta corrente**, ver §15);
- canal (app iOS, app Android, internet banking, e-mail);
- período (redesigns frequentes);
- página (cabeçalho/rodapé, tabela quebrada, “continua”);
- tipo de PDF (texto selecionável vs imagem/scan/foto da tela).

Uma solução “Santander v1 e depois a gente vê” cria dívida: cada banco vira um regex frágil, e o usuário do banco N+1 continua bloqueado. O desenho certo é um **pipeline de documento** com camadas, e adapters opcionais por *fingerprint* de layout.

```
                    ┌─────────────────────────┐
                    │  PDF (bytes) + conta    │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Ingestão e higiene     │
                    │  (tipo, tamanho, hash)  │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Análise do documento   │
                    │  texto vs imagem        │
                    │  fingerprint de layout  │
                    └───────────┬─────────────┘
                                ▼
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
     Extração textual                      OCR (só se preciso)
     (layout/tabelas)                      (fila pesada)
              └─────────────────┬─────────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Interpretação          │
                    │  genérico → adapter     │
                    │  → LLM estruturado      │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Normalização           │
                    │  → LinhaImportacao      │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Validação / saldo      │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Deduplicação           │
                    └───────────┬─────────────┘
                                ▼
                    ┌─────────────────────────┐
                    │  Revisão (UI)           │
                    │  → confirmar existente  │
                    └─────────────────────────┘
```

Cada etapa tem contrato de entrada/saída. Falha **não** derruba o pipeline inteiro: degrada a confiança e empurra para revisão.

---

## 5. Contrato canônico (o ponto de união)

Hoje `LinhaOfx` é o contrato de fato, mas o nome mente (já é usado pelo Excel). Para PDF, evoluir para um tipo de importação **agnóstico de origem**, sem quebrar OFX/XLSX.

### 5.1 `LinhaImportacao` (proposto)

Campos que o confirmar **já entende**:

- `data: date`
- `valor: Decimal` (sempre ≥ 0)
- `tipo: receita | despesa | ajuste`
- `descricao: str` (≤ 255, mesma regra atual)
- `identificador_externo: str | None` — no OFX é o FITID; no PDF em geral `None`

Campos **novos**, só de extração (não precisam ir para `Transacao` no v1, mas devem ir ao preview):

- `origem: ofx | xlsx | pdf`
- `confianca: float` (0–1) da linha
- `motivo_baixa_confianca: str | None` (descrição quebrada, valor ambíguo, data inferida, etc.)
- `saldo_apos: Decimal | None` (se o extrato tiver coluna de saldo)
- `pagina: int | None`
- `texto_bruto: str` (recorte da região, para o usuário conferir)
- `indice_no_documento: int` (ordem no extrato, estável)

Regra de ouro: **o endpoint `importar_ofx_confirmar` continua sendo o único gravador de lote.** O PDF só produz o JSON de preview no mesmo formato (`data`, `valor`, `tipo`, `descricao`, flags de duplicata). Não criar um segundo `bulk_create`.

### 5.2 Objeto de documento (lote)

Além das linhas, o job precisa persistir um resumo do extrato:

- banco/layout detectado (`desconhecido` é um valor válido);
- período declarado (`data_inicio`, `data_fim`);
- saldo inicial e saldo final extraídos (se existirem);
- soma de créditos / débitos;
- `reconciliacao_ok: bool`;
- `delta_saldo: Decimal | None`;
- `modo_extracao: text | ocr | hibrido`;
- `parser_id` + versão (ex.: `generic_table@1`, `adapter:nubank_cc@3`, `llm_struct@1`);
- `sha256` do arquivo;
- `precisa_revisao: bool` e lista de *blockers*.

Sem esse objeto, a UI não consegue explicar “por que não importamos automaticamente”.

---

## 6. Camadas do pipeline

### 6.1 Ingestão

**Entrada:** multipart (`conta_id` + arquivo PDF), usuário autenticado, conta ativa do usuário.

Responsabilidades:

- Validar `Content-Type` **e** magic bytes (`%PDF`), não só a extensão.
- Limite de tamanho próprio (sugerido: **10 MB**; extrato mensal típico é bem menor; foto de tela infla).
- Recusar PDF criptografado com senha (mensagem clara: “remova a senha e envie de novo”).
- Calcular `sha256`; se o mesmo usuário + mesma conta + mesmo hash já tiver lote importado ou em revisão, **não reprocessar**: reabrir o lote existente (idempotência de arquivo).
- Persistir o arquivo em mídia **protegida**, path `imports/pdf/{user_id}/{job_uuid}.pdf`, ownership igual a `ExportJob`.
- Criar `ImportJob` (`pending`) e responder **202** com `job_id` + URL de polling. Não parsear no Gunicorn.

Rate limit: espelhar exports (ex.: N jobs/hora e no máximo 1–2 PDF em processamento por usuário). Fila Celery **separada** (`imports`) para não competir com geração de relatório.

### 6.2 Análise do documento (classificação)

Objetivo: decidir **como** extrair, não ainda **o que** são as transações.

Sinais:

| Sinal | Uso |
|-------|-----|
| Há texto extraível com densidade mínima? | Caminho textual vs OCR |
| Metadata `Producer`/`Creator` | Às vezes identifica o gerador do banco |
| Texto da 1ª página (razão social, CNPJ, “extrato”, “conta corrente”) | Fingerprint de instituição |
| Cabeçalhos de coluna (“Data”, “Histórico”, “Valor”, “Saldo”, “D/C”) | Fingerprint de **layout**, mais estável que o nome do banco |
| Número de páginas, páginas só com imagem | OCR seletivo por página |

Saída: `DocumentoAnalise` com `kind = digital_text | scanned | mixed`, `layout_key`, `banco_candidato` (opcional), `ocr_necessario`.

**Fingerprint de layout, não de marca.** “Tabela com colunas Data | Lançamento | Valor | Saldo, valores `1.234,56`, débito à esquerda” é mais reutilizável do que “parser Santander 2024”. Vários bancos compartilham famílias de layout (especialmente PDFs gerados por núcleos de internet banking antigos).

### 6.3 Extração

Dois motores, mesma saída: **páginas com elementos** (texto, retângulos, palavras com bounding box, imagens).

**Caminho A — PDF digital (prioritário, v1)**

Bibliotecas candidatas (a escolher na implementação, com prova em fixtures reais):

- **PyMuPDF (`fitz`)**: rápido, texto + coordenadas, rasterização para OCR pontual.
- **pdfplumber**: melhor para **tabelas** (estratégia lines/text), muito usado em extratos.

Não usar só `pypdf.extract_text()`: perde estrutura, junta colunas e quebra a reconciliação.

**Caminho B — PDF imagem / scan / foto (v2)**

- Rasterizar página (300 DPI).
- OCR local (Tesseract `por`+`eng` ou PaddleOCR). Preferir **local** por LGPD.
- OCR de nuvem (Document AI / Textract / Gemini Vision) só como **opt-in explícito**, fila própria, DPIA novo.

Páginas mistas: OCR só onde a densidade de texto for baixa.

Saída desta camada: ainda **não** são transações. São `tokens` + `tabelas candidatas` + `blocos de texto` com posição. Inventar lançamentos aqui é o erro mais caro do sistema.

### 6.4 Interpretação estrutural (o coração)

Três estratégias em cascata. A primeira que passar na validação (§6.6) ganha. Se nenhuma passar, o lote vai para revisão com o melhor candidato **marcado como incompleto**.

#### Estratégia 1 — Intérprete genérico de tabela (default)

Heurísticas, sem nome de banco:

1. Detectar região de tabela (linhas/colunas por alinhamento de x).
2. Identificar linha de cabeçalho por vocabulário (`data`, `históric`, `descri`, `valor`, `crédito`, `débito`, `saldo`, `documento`, `d/c`).
3. Mapear colunas para papéis: `DATA`, `DESCRICAO`, `VALOR_UNICO`, `CREDITO`, `DEBITO`, `SINAL`, `SALDO`, `IGNORAR`.
4. Percorrer o corpo:
   - linha com data → inicia lançamento;
   - linhas seguintes **sem** data e sem valor, alinhadas à coluna de descrição → **continuação** (concatenar);
   - ignorar cabeçalhos repetidos, rodapés, “total do dia”, “saldo do dia”, “a transportar”, “de transporte”, numeração de página.
5. Interpretar valor:
   - `1.234,56` / `1,234.56` / `1234.56`;
   - parênteses = débito;
   - colunas C e D separadas;
   - sufixo `C`/`D` / `CR`/`DB`;
   - **nunca** usar cor como único sinal (extração textual perde cor).
6. Recortar saldo inicial/final em blocos fora da tabela (“Saldo anterior”, “Saldo final”, “Saldo disponível” — este último **não** é saldo contábil do período; não usar para reconciliação).

Esta estratégia sozinha já cobre uma fração grande dos PDFs de app/internet banking brasileiros, que são tabelas com texto selecionável.

#### Estratégia 2 — Adapter de layout conhecido

Registry:

```text
layout_key  →  Adapter
```

O adapter só entra se o fingerprint bater com confiança alta. Ele não substitui o genérico: **corrige** o que o genérico erra naquele layout (ex.: descrição em duas colunas, TED com favorecido na linha de baixo, PIX com chave na terceira linha, valores em fonte menor).

Contrato do adapter:

- entrada: páginas extraídas (não o PDF bruto, se possível);
- saída: `list[LinhaImportacao]` + `DocumentoResumo`;
- testes golden obrigatórios;
- versão no `parser_id`.

**Ordem de construção dos adapters:** os layouts com PDF digital + saldo no extrato + volume de usuários, **não** “começar pelo Santander”. Santander entra na fila se o genérico falhar nele, como qualquer outro.

Esboço de priorização técnica (a validar com corpus real):

| Prioridade | Família típica | Por quê |
|------------|----------------|---------|
| P0 | PDF digital com tabela + coluna de saldo | Reconciliação possível; genérico tende a funcionar |
| P1 | PDF digital sem saldo, mas com totais de período | Dá para validar soma, não running balance |
| P2 | Layouts conhecidos que quebram o genérico (descrição multilinha agressiva, duas tabelas, cartão disfarçado de extrato) | Adapter pontual |
| P3 | Scan/foto | OCR + mesmo intérprete |
| P4 | PDF de investimento, TED agrupado, comprovante (não é extrato) | Recusar com mensagem, não “forçar” |

Bancos/formatos a **provar com fixtures** (não a hardcodar no dia 1): Nubank, Inter, C6, Itaú, Bradesco, Banco do Brasil, Caixa, Santander, PicPay, Mercado Pago, BTG. A lista é de **corpus de teste**, não de parsers.

#### Estratégia 3 — Interpretação assistida por modelo (fallback, nunca sozinha)

Usar LLM **somente** se 1 e 2 falharem a reconciliação, e somente sobre **texto já extraído e minimizado**:

- recortar só a região da tabela (sem cabeçalho com CPF/endereço, sem agência/conta completos);
- pedir JSON com schema rígido (data ISO, valor string, sentido, descrição, saldo_apos opcional);
- `temperature = 0`;
- **validar** cada linha (data no período, valor parseável, sentido explícito);
- se o modelo devolver N linhas e o saldo não fechar, **descartar a saída do modelo** e ir para revisão humana com a extração bruta — não “aceitar o palpite”.

Proibido no v1:

- enviar o PDF/imagem completo a um modelo de visão por padrão;
- usar a saída do LLM sem reconciliação;
- persistir o extrato bruto em log de prompt.

Isso exige DPIA específico (`DPIA_IMPORTACAO_PDF_LLM.md`) **antes** de ligar a estratégia 3 em produção.

### 6.5 Normalização

Regras alinhadas ao ledger atual (`valor_e_tipo_de_importacao`):

- valor sempre positivo;
- saída da conta → `despesa`; entrada → `receita`; zero → `ajuste` (raro em extrato; tratar com baixa confiança);
- data em `date` (sem timezone; extrato brasileiro = calendário civil);
- descrição: colapsar espaços, limitar 255, preservar informação útil (favorecido PIX, se existir);
- **não** categorizar nesta etapa (o pipeline de categorização já existe e é posterior).

Datas parciais (`10/03` sem ano): completar com o ano do período do extrato; se o período cruzar virada de ano, usar a página/contexto; se ambíguo, linha em revisão.

### 6.6 Validação (gate)

Um lote só pode ser oferecido como “pronto para confirmar com confiança alta” se passar nos checks abaixo. Falha = `precisa_revisao = true` e, em blockers, **não** pré-selecionar “importar todas”.

| Check | Blocker? | Notas |
|-------|----------|--------|
| Pelo menos 1 lançamento | Sim | Senão, erro de extração |
| Todas as linhas têm data + valor + tipo + descrição | Sim as incompletas | Incompletas ficam desmarcadas |
| Datas dentro do período do extrato (folga de 1 dia) | Não | Flag por linha |
| `saldo_inicial + créditos − débitos = saldo_final` (± R$ 0,01) | **Sim para auto-confiança** | Se não houver saldos, usar totais do período se existirem; se não houver nenhum âncora, revisão obrigatória |
| Running balance (se houver coluna saldo) consistente linha a linha | Não | Detecta linha pulada no meio |
| Ordem cronológica razoável | Não | Extratos às vezes são do mais novo para o mais antigo; aceitar ambos |
| Contagem vs “N lançamentos” declarado no PDF | Não | Se o banco imprimir o total |
| Nenhum valor absurdo (`>= 1e9`, regra já do confirmar) | Sim a linha | |
| Documento parece extrato (não boleto, não comprovante único, não fatura de cartão no v1) | Sim o lote | Mensagem acionável |

**Política de produto recomendada:** nunca auto-confirmar PDF. Sempre preview. O que muda é o *nível de alarme*: lote reconciliado chega com linhas pré-selecionadas; lote quebrado chega com aviso vermelho e linhas duvidosas desmarcadas.

### 6.7 Deduplicação

O FITID não vai salvar o PDF. Usar **várias camadas**, reaproveitando `avaliar_duplicatas_importacao` e estendendo.

1. **Arquivo:** mesmo `sha256` + mesma conta → mesmo lote (já tratado na ingestão).
2. **Heurística atual:** `data + valor + descrição normalizada` na mesma conta — já pega reimportação do mesmo PDF e lançamento manual idêntico.
3. **Fingerprint sintético (opcional, v1.1):** `sha256(conta_id | data | valor | desc_norm | origem=pdf)` persistido em campo novo, **não** em `ofx_fitid`. Sobrecarregar FITID misturaria OFX com PDF e atrapalharia a constraint atual.
4. **Cruzamento OFX × PDF (o caso difícil):** o mesmo mês importado via OFX e depois via PDF (ou o contrário) quase sempre tem **descrições diferentes** (`PIX 123` vs `Pix enviado - Maria Silva`). A heurística atual **não** pega. Mitigações:
   - no preview, se já existir na conta, no mesmo dia, o mesmo valor (magnitude + tipo), marcar `duplicata_por_valor_data` (nova flag **fraca**);
   - se houver *várias* transações iguais no mesmo dia (dois PIX de R$ 50), **não** auto-marcar: mostrar “possível duplicata” e deixar o usuário decidir;
   - nunca bloquear no banco por essa flag fraca.
5. **Sobreposição de período:** se o usuário importar 01–15 e depois 01–30, as linhas da primeira quinzena devem aparecer como duplicata heurística quando a descrição coincidir; quando não coincidir, a flag fraca (item 4) cobre parte.

O usuário continua podendo importar linha marcada (comportamento atual do OFX).

### 6.8 Revisão e importação

Reusar o modal de preview (feed, categorias opcionais, “Organizar automaticamente”, confirmar JSON). Extensões de UX específicas de PDF:

- faixa de status do documento: banco/layout, período, “saldo fecha” / “saldo não fecha (Δ = R$ x,xx)”;
- badge por linha: confiança alta / revisar / possível duplicata;
- texto bruto expansível (“como estava no PDF”);
- ação de **juntar** duas linhas (descrição partida mal interpretada) e **dividir**;
- não confirmar se ainda houver blocker sem o usuário marcar “importar mesmo assim” (opt-in consciente, logado).

Depois do confirmar, o arquivo PDF:

- **recomendação:** apagar ou criptografar e expirar em 24–72 h (igual TTL de export), salvo o usuário ter um “manter comprovante” futuro;
- o ledger não precisa do PDF para existir.

Categorização: **não** misturar com extração. O botão já existente de IA de categoria roda sobre descrições já normalizadas.

---

## 7. Modelo de persistência proposto

Novo app ou módulo `transacoes/importacao/` (preferível módulo, para não fragmentar o domínio).

### 7.1 `ImportJob`

Espelhar `ExportJob` no que já funciona em produção:

- `usuario`, `conta`
- `formato` (`pdf`; o modelo aguenta `ofx`/`xlsx` no futuro se unificarmos)
- `status`: `pending | processing | needs_review | ready | imported | error | expired | cancelled`
- `arquivo` (FileField protegido)
- `sha256`
- `parser_id`, `layout_key`, `banco_detectado`
- `resumo_json` (saldos, período, flags)
- `linhas_json` (resultado normalizado para o preview; tamanho limitado — 2000 linhas)
- `mensagem_erro` (amigável) + `erro_interno` (não vazar ao cliente)
- `task_id`, tentativas, timestamps, `expira_em`

`needs_review` vs `ready`: ambos mostram preview; `ready` significa reconciliação OK.

### 7.2 Evolução de `Transacao` (mínima e justificada)

Não é obrigatório no primeiro corte. Quando for:

- `origem_importacao` (`CharField` nullable) — analítica e suporte;
- `import_job_id` FK nullable — rastreio;
- **não** criar `pdf_fitid`.

Evitar migration pesada só para telemetria. O lote já guarda a origem.

### 7.3 Registry de adapters (código, não tabela no v1)

```text
transacoes/importacao/pdf/
  ingest.py
  analyze.py
  extract/
    text.py
    ocr.py
  interpret/
    generic_table.py
    adapters/          # um módulo por layout_key
    llm_struct.py      # desligado por flag
  normalize.py
  validate.py
  registry.py
```

`registry.py` escolhe adapter por `layout_key`; fallback sempre `generic_table`.

Adicionar um layout novo = fixture golden + módulo adapter + registro. Sem if-spaghetti na view.

---

## 8. Integração HTTP e UX

### 8.1 Endpoints

| Método | Caminho (proposta) | Papel |
|--------|-------------------|--------|
| `POST` | `/transacoes/importar/pdf/` | Cria job, 202 |
| `GET` | `/transacoes/importar/pdf/<uuid>/` | Polling: status + progresso |
| `GET` | `/transacoes/importar/pdf/<uuid>/preview/` | Payload compatível com `_payload_preview_importacao` quando `ready`/`needs_review` |
| `POST` | `/transacoes/importar/ofx/confirmar/` | **Reutilizado** (linhas JSON) |
| `POST` | `/transacoes/importar/pdf/<uuid>/descartar/` | Cancela, apaga arquivo |

Não reparsear o PDF no confirmar. O preview congela `linhas_json` no job (como o OFX congela no cliente). O servidor **valida** o JSON como hoje.

### 8.2 UI no histórico

Hoje há dois botões: Importar OFX e Importar planilha. Opções:

- **A (recomendado no v1):** terceiro botão “Importar PDF”, modal irmão, para não arriscar regressão nos fluxos estáveis.
- **B (v1.1):** um único “Importar extrato” que detecta OFX / XLSX / PDF.

Fluxo PDF: upload → spinner com etapas reais (“Lendo PDF”, “Detectando tabela”, “Conferindo saldo”) via polling → o **mesmo** feed de preview.

Tempo esperado: digital 2–15 s; OCR 20–90 s. Por isso job + polling, não overlay mudo de 70 s.

### 8.3 Mensagens quando não der

Exemplos acionáveis (não “erro genérico”):

- “Este PDF parece uma imagem. No momento importamos melhor extratos com texto selecionável. Você pode baixar o OFX no internet banking ou tentar um PDF gerado pelo app (não uma foto).”
- “Encontramos a tabela, mas o saldo do extrato não fecha com as linhas (diferença de R$ 12,30). Revise as linhas destacadas.”
- “Este arquivo parece fatura de cartão. A importação por PDF no momento é só para conta.”
- “PDF protegido por senha.”

---

## 9. Segurança, LGPD e operação

### 9.1 Dados especialmente sensíveis

Extrato PDF é **dado financeiro identificável** (categoria LGPD de alto cuidado): identificação civil, conta, histórico de consumo, PIX para pessoas.

Controles:

- mídia autenticada (já existe o padrão);
- path com `user_id` + UUID, sem nome original do arquivo;
- TTL curto + comando de purge (espelhar `limpar_exports_expirados`);
- exclusão de conta apaga jobs e arquivos (cascade + file cleanup);
- logs: hash, `parser_id`, status, **nunca** dump de linhas com nomes de favorecidos;
- staff: mesmo cuidado de exports (acesso a mídia é ponto já marcado como parcial na política de segurança).

### 9.2 LLM e subprocessadores

Alinhar com o DPIA de categorização:

- extração **local** é o caminho padrão;
- qualquer envio a Gemini/outro provedor = minimização + opt-in + subprocessador documentado + retenção zero do documento;
- não reutilizar `GEMINI_API_KEY` da categorização sem orçamento e circuit breaker **separados** (custo de visão/documento é outra ordem de grandeza).

### 9.3 Abuso e robustez

- PDF enorme, mil páginas, zip bomb de streams: limites de páginas (ex.: 50) e de tempo (soft/hard Celery, fila `imports`).
- Arquivo malicioso: não executar JavaScript de PDF; bibliotecas de extração em worker isolado; atualizar dependências.
- Não interpolar caminho do usuário em shell (Ghostscript/Tesseract só com args controlados).

### 9.4 Infra atual

A VPS já tem Celery para export. PDF entra na mesma família operacional, **fila distinta** e timeout maior para OCR. Disco efêmero continua sendo risco (já apontado para media/exports): jobs em processamento morrem no redeploy; reconciliar órfãos como em `ExportJob`.

---

## 10. Testes e corpus (condição de qualidade)

PDF sem golden set vira teatro. Antes de produção:

1. **Corpus interno** (não versionar PII): PDFs reais anonimizados (mascarar CPF, agência, nomes) em storage privado de fixtures.
2. **Fixtures sintéticas** no git: PDFs mínimos gerados (reportlab) cobrindo tabela simples, multilinha, duas páginas, cabeçalho repetido, `1.234,56`, colunas C/D.
3. **Invariantes** (estender `transacoes/tests/helpers/ledger_invariants.py`):
   - reconciliação quando o fixture declara saldo;
   - nenhuma linha sem data/valor;
   - confirmar PDF usa o mesmo `bulk_create` e não duplica FITID de OFX;
   - reenvio do mesmo hash não cria segundo lote importado.
4. **Fuzz:** PDF truncado, só imagem, 0 páginas, 2000+ linhas, valores `R$`.
5. **E2E:** um caminho feliz digital + um caminho `needs_review`, reusando `e2e/specs/import/`.

Critério de “banco suportado”: não é ter adapter. É **taxa de reconciliação** no corpus daquele layout (ex.: ≥ 95% dos PDFs fecham saldo, e 100% dos que não fecham caem em revisão sem gravar sozinhos).

---

## 11. Fases de entrega (sem atalho Santander)

Implementação **ainda não** está neste documento; isto é o recorte de risco.

### Fase 0 — Fundação (desbloqueia tudo)

- `ImportJob` + worker Celery fila `imports` + storage protegido + TTL.
- `LinhaImportacao` e preview/confirm reutilizados.
- UI: upload PDF + polling + preview existente.
- Extração textual + intérprete genérico + validação de saldo.
- Corpus inicial com **vários** bancos digitais (não um).
- Recusar senha, scan, fatura de cartão, não-PDF.

**Saída:** usuário com PDF *digital e tabelado* já importa, com revisão. Vários bancos “ganham de graça” se o genérico reconciliar.

### Fase 1 — Robustez do genérico

- Continuação de descrição multilinha.
- Tabelas que atravessam páginas.
- Totais do período quando não há saldo inicial/final.
- Flag fraca `data+valor` para choque com OFX/manual.
- Telemetria: `layout_key`, `reconciliacao_ok`, `parser_id` (sem PII).

### Fase 2 — Adapters pontuais

Só para `layout_key` com falha sistemática no genérico (medida na telemetria da Fase 1). Cada adapter nasce de evidência, não de lista comercial de bancos.

### Fase 3 — OCR

- Worker pesado, Tesseract/Paddle local, mesmas etapas 6.4–6.8.
- Revisão **obrigatória**.
- Limite de páginas mais baixo.

### Fase 4 — Fallback LLM estruturado

- Flag, DPIA, minimização, orçamento, circuit breaker próprio.
- Nunca grava sem reconciliação.

### Fase 5 (paralela, produto)

- Unificar botão “Importar extrato”.
- Open Finance / agregadores (Pluggy, Belvo, etc.) como **alternativa** ao PDF — não substitui o caso “só tenho o PDF do app”, mas reduz volume futuro.

---

## 12. O que deliberadamente não fazer

- Parser único “Santander” como MVP (ensina o time a especializar cedo e deixa o resto de fora).
- Mandar todo PDF para GPT/Gemini Vision como solução principal (custo, alucinação, LGPD, DPIA atual).
- Auto-import sem preview.
- Tratar fatura de cartão no mesmo pipeline no v1 (competência, `Cartao`/`Fatura` são outro domínio; o GranaGo já tem faturas).
- Reparsear o PDF no confirmar.
- Gravar identificador sintético em `ofx_fitid`.
- Confiar em cor, logo ou posição absoluta em pixels como único sinal.
- Manter PDFs para sempre no disco “para debug”.
- Usar o request web (Gunicorn) para OCR.

---

## 13. Riscos e mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Alucinação / linha inventada | Ledger errado, perda de confiança | Reconciliação obrigatória; LLM só fallback; não inventar |
| Linha omitida | Saldo da conta no app ≠ banco | Running balance + Δ de saldo → revisão |
| Duplicata OFX×PDF | Receita/despesa em dobro | Flag `data+valor`; UI clara; nunca unique constraint fraca |
| Layout muda no app do banco | Adapter quebra | Genérico como default; adapter versionado; telemetria |
| PII em LLM/logs | LGPD | Extração local; minimização; TTL; DPIA |
| OCR ruim (foto torta) | Lixo no preview | Recusar confiança baixa; orientar PDF nativo do app |
| Custo de CPU/OCR | Worker saturado | Fila separada, limites, rate limit |
| PDF de 80 páginas de 2 anos | Timeout | Limite de páginas; sugerir recorte mensal |
| Conta errada no select | Lançamentos no lugar errado | Conta escolhida pelo usuário; no v1 não autodetectar conta |

---

## 14. Decisões recomendadas (para quando for implementar)

1. **Caminho padrão = genérico + reconciliação**, não catálogo de bancos.
2. **Sempre preview**; PDF nunca grava direto.
3. **Job assíncrono** no padrão `ExportJob` / Celery.
4. **Confirmar = endpoint atual.**
5. **Categorização continua desacoplada.**
6. **OCR e LLM são fases posteriores**, com revisão obrigatória / DPIA.
7. **Corpus multi-banco no dia 1**, mesmo que só o genérico esteja ligado.
8. **Cartão e comprovante avulso fora do v1.**

---

## 15. Fora de escopo do v1 (explícito)

- Fatura de cartão em PDF.
- Open Finance / sincronização contínua com o banco.
- Foto da tela sem passar por OCR de fase 3.
- Detecção automática da conta GranaGo a partir de agência/conta do PDF.
- Edição do PDF; assinatura digital; conciliação contábil SPED.
- Importar vários PDFs em um clique (pode ser fase seguinte: N jobs).

---

## 16. Relação com o código atual (mapa)

```
PDF ──ImportJob──► extract/interpret/validate
                         │
                         ▼
                  linhas_json ≈ LinhaOfx
                         │
                         ▼
            _payload_preview_importacao()
            avaliar_duplicatas_importacao()
                         │
                         ▼
              UI preview (modal irmão)
                         │
                         ▼
              importar_ofx_confirmar()
                         │
                         ▼
                    Transacao
                         │
                         ▼
           categorizar_import_batch (opcional)
```

O trabalho novo está **à esquerda** do contrato `LinhaOfx`. O ledger, as invariantes, o confirmar e a IA de categoria permanecem.

---

## 17. Próximo passo sugerido (quando houver autorização para implementar)

Não começar por adapter de banco. Começar pela Fase 0: job + extração textual + tabela genérica + reconciliação + preview no histórico, com 5–10 PDFs reais de bancos **diferentes** como aceite.

Se o genérico reconciliar a maioria, o produto já elimina a fricção “preciso ir no internet banking baixar OFX” para muita gente. Os adapters e o OCR passam a ser evolução baseada em evidência, não em palpite de layout.
)
