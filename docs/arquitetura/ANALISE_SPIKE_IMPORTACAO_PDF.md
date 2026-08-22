# Spike técnico: importação de extratos bancários em PDF

**Data de criação:** 21 de agosto de 2026  
**Atualizado em:** 21 de agosto de 2026  
**Status:** caderno de laboratório — **sem implementação**  
**Produto:** GranaGo  

A arquitetura canônica (estado da arte) está em [`IMPORTACAO_PDF_EXTRATOS.md`](IMPORTACAO_PDF_EXTRATOS.md) — **atualizado em 22/08/2026** (engine **pypdfium2**, v1 **síncrono**, região lógica). Este arquivo guarda medições, scripts e o rastro do que foi rejeitado na hipótese inicial. Onde a recomendação da §O (Celery, lib em aberto) divergir do canônico, **prevalece o IMPORTACAO**.  
**Corpus medido:** 14 PDFs sintéticos + **6 PDFs bancários reais** (Santander, Bradesco, 2× Nubank, Caixa, comprovante raster 2 p.; **não versionados**, só anexos locais).  
**Bibliotecas do experimento (venv isolada em `/tmp/spike_pdf_venv`, não adicionadas ao `requirements.txt`):** PyMuPDF 1.28.2, pdfplumber 0.11.10, pdfminer.six 20260107  

Este documento **não apaga** a análise em [`IMPORTACAO_PDF_EXTRATOS.md`](IMPORTACAO_PDF_EXTRATOS.md). Trata-a como hipótese e registra o que o spike confirmou, rejeitou ou deixou em aberto.

**PII:** medições do PDF real abaixo são só estrutura, vocabulário de seção e métricas. Nenhum lançamento, nome, agência ou conta foi copiado para o git.

---

## A. Resumo executivo

Três descobertas mudam a hipótese anterior.

1. **“PDF digital” não é “PDF fácil”.** Texto selecionável sem objeto de tabela (`07_aligned_text_no_tableobj.pdf`) fez *as duas* bibliotecas retornarem **zero tabelas**. Esse é o formato típico de app. `find_tables()` / `extract_tables()` não são o produto — o produto é **reconstruir colunas a partir de palavras com coordenadas**.

2. **Parser genérico pode parecer válido e estar errado.** No PDF multipágina com cabeçalho repetido, `find_tables()` “sucesso” (3 tabelas) mas células sangraram: descrição invadiu débito (`ENSA PARA T1E0,S0T0E`). Sucesso da lib ≠ correção financeira.

3. **PyMuPDF é tecnicamente superior em desempenho *e* em assertividade no caso difícil.** Dual **AGPL-3.0 ou licença comercial Artifex**. GranaGo é SaaS fechado. pdfplumber é a alternativa permissiva, mas no PDF de 40 páginas mediu **3,09 s e 187,5 MB RSS** contra **0,46 s e 56,5 MB** do PyMuPDF. No sintético multipage com cabeçalho repetido, o mesmo sangramento de célula visto em `find_tables` aparece em `extract_words()`: F1 identidade **1,0 vs 0,013**. Isolar o parse do Gunicorn deixa de ser “se houver evidência” e vira necessidade se a lib for pdfplumber — e continua recomendável mesmo com PyMuPDF, porque há só **2 workers** web (`WEB_CONCURRENCY` default) e o parser recebe arquivo **não confiável**.

4. **O comprovante Santander real confirma o pior caso do genérico por `find_tables`.** 11 páginas digitais, texto em todas, **27 tabelas detectadas e 0 linhas de movimento** (data+valor na tabela). As movimentações aparecem como texto alinhado (`dd/mm` sem ano, coluna esquerda / valor à direita). `find_tables` ainda custou **2,6 s**. Palavras+bbox: **40 ms**.

Outras conclusões fortes:

- Múltiplas tabelas de movimento (corrente + poupança com o **mesmo** cabeçalho) são extraídas juntas. Escolher automaticamente a “maior” importa a conta errada. **Perguntar ao usuário.**
- `extract_text()` segue ordem de *desenho*, não visual (`08_draw_order_inverted.pdf`). Ordenar palavras por `(y, x)`.
- Scan: 0 caracteres + 1 imagem. Recusar no v1 é viável de detectar.
- Duplicata PDF×OFX **não é secundária**: a heurística atual exige descrição igual; OFX e PDF quase nunca coincidem.
- **Assertividade (21/08/2026):** o mesmo interpretador (palavras+bbox) nas duas libs. Na maioria dos sintéticos e nos digitais reais o acordo é ~1,0. O pdfplumber **não** é equivalente no layout apertado multipage: inventa o valor (usa o saldo) depois de fundir `TESTE`+`10,00` em `T1E0,S0T0E`. Ver §E4. §E3b: +2 PDFs reais (raster 2 p. e Nubank 5 p.).

---

## B. Decisões mantidas

Continuam corretas após o spike:

- PDF deságua no contrato atual (`LinhaOfx` → preview → categorização opcional → `importar_ofx_confirmar`). Sem segundo ledger.
- Não persistir o PDF como produto (`FileField` / `MEDIA_ROOT` / object storage). Backup de mídia e bypass de staff em `/media/` tornam isso inaceitável.
- Extração local; **não** Gemini Vision / OCR cloud no v1.
- OCR fora do v1; recusar raster.
- Adapters por **`layout_key`**, não `if banco ==`.
- `generic_table_v1` como default de *layout desconhecido*, no **mesmo** registry — não “genérico corre e adapter só se falhar”.
- Preview humano obrigatório. Sem auto-import.
- Logs com código técnico, sem linha do extrato.
- Não inferir a `Conta` GranaGo por agência/conta do PDF.
- Não gravar em `ofx_fitid`.
- Categorização inteligente só sobre linhas já normalizadas.
- Não renomear `LinhaOfx` agora.

---

## C. Decisões rejeitadas

| Hipótese anterior | Por que cai | Nova posição |
| ----------------- | ----------- | ------------ |
| Segmentar primeiro por título “Movimentação” | `02_no_title.pdf` ainda é tabela perfeita; bancos reais podem não ter o rótulo | Região por geometria + cabeçalho de **coluna** + padrões; título é sinal fraco |
| “Não olhar o PDF inteiro” | Impossível propor regiões sem varredura estrutural | Varrer geometria; não persistir texto integral; não interpretar região classificada como não-movimento |
| `find_tables` como coração do genérico | Sintético: 0 tabelas no app-like. **Real Santander: 27 tabelas e 0 linhas de movimento; 2,6 s de custo** | Genérico = cluster de palavras `(x,y)`. `find_tables` **desligado no default**; no máximo proposta opcional, nunca verdade |
| Digital vs scan basta | Texto selecionável + tabela inexistente é o caso central | Ver §G: `raster` / `textual_tabular` / `textual_aligned` / `textual_linear` |
| Processar síncrono no Gunicorn “como OFX até haver evidência” | OFX é barato; PDF não. 2 workers. pdfplumber 187 MB / 40 páginas. Parser não confiável. Export já isolou WeasyPrint no Celery | Worker isolado **no v1** (Celery, fila `imports`). Não é cosmética |
| BytesIO no request web é automaticamente mais privado e melhor | Mais privado *se* o parse cabe. Pior para disponibilidade e para CVE de parser | Tempfile 0700 no host único (web+celery na mesma VPS), fora de mídia e de Redis |
| PDF em Redis “porque é efêmero” | Redis Ubuntu default tem RDB; AOF possível. O dossiê iria a disco | **Nunca** payload PDF no Redis |
| Duplicata PDF×OFX pode esperar | Heurística `data+valor+descrição`; descrições divergem | Flag fraca `data+valor+tipo` no preview, no **v1**, sem unique no banco |
| Escolher a maior tabela se houver várias | Poupança e CC no sintético têm o mesmo schema | UI de seleção de região; nunca misturar no silêncio |
| PyMuPDF como default técnico implícito | AGPL | Não entra em `requirements.txt` sem decisão de licença comercial ou parecer jurídico |

---

## D. Questões ainda abertas

1. **Licença PyMuPDF (AGPL vs comercial)** — ainda bloqueia a escolha da lib.  
2. RSS/tempo em **outros** bancos (Nubank, Itaú, etc.). Santander 11 p. já medido (§E2).  
3. **Limiar raster vs textual** em PDF híbrido (logo enorme + pouco texto). Este Santander tem texto em 11/11 páginas + imagens de marca — classificar como raster seria erro.  
4. `extract_tables(strategy="text")` fino do pdfplumber — o default no real também deu 0 linhas data+valor; talvez uma estratégia diferente mude. Baixa prioridade se o genérico for por words.  
5. Quantos usuários mandam **dossiê consolidado** (este PDF) vs extrato só de lançamentos.  
6. Política quando a região de movimento atravessa páginas com cabeçalho incompleto (visto na p. 6).  
7. Comprar PyMuPDF vs pypdfium2 / pdf-oxide — pdfplumber falha no sintético 05; nos digitais reais as libs “sérias” concordam.

Recomendo decidir **isolamento + words/coordenadas + escolha de região + flag de duplicata + datas `dd/mm`** já. Biblioteca: depois da licença.

---

## E. Resultados dos experimentos

Scripts: `docs/arquitetura/spike_importacao_pdf/generate_corpus.py` e `run_spike.py`.  
JSON bruto: `/tmp/spike_pdf_corpus/spike_results.json` (não versionado; contém só sintético).

`rss_max_mb` é `ru_maxrss` do **subprocesso** (inclui interpretador; baseline ~35 MB pdfplumber / ~50 MB PyMuPDF).

| Arquivo | Bytes | PyMuPDF t / RSS / tabelas / classe | pdfplumber t / RSS / tabelas / classe |
| ------- | ----- | ---------------------------------- | ------------------------------------- |
| 01 structured table | 2664 | 0,056 s / 54,6 / 1 / tabular | 0,051 s / 36,0 / 1 / tabular |
| 02 sem título | 2382 | 0,038 / 54,2 / 1 / tabular | 0,044 / 35,6 / 1 / tabular |
| 03 valor com sinal | 2198 | 0,032 / 53,8 / 1 / tabular | 0,035 / 35,5 / 1 / tabular |
| 04 multilinha | 2058 | 0,023 / 53,6 / 1 / tabular | 0,027 / 35,1 / 1 / tabular |
| 05 multipage + header | 6568 | 0,541 / 63,1 / 3 / tabular | 0,573 / 48,2 / 3 / tabular |
| 06 multi-seção | 3861 | 0,080 / 55,1 / **3** / tabular | 0,085 / 37,1 / **3** / tabular |
| 07 texto alinhado **sem Table** | 2229 | 0,034 / 54,2 / **0** / aligned | 0,033 / 35,7 / **0** / aligned |
| 08 ordem de desenho invertida | 2169 | 0,025 / 53,7 / 0 / aligned | 0,034 / 35,5 / 0 / aligned |
| 09 prosa linear | 1872 | 0,034 / 54,2 / 0 / aligned† | 0,035 / 36,1 / 0 / aligned† |
| 10 só imagem | 57583 | 0,035 / 58,0 / 0 / **raster** | 0,006 / 34,6 / 0 / linear (heurística fraca) |
| 11 senha | 3485 | detecta encrypted; senha vazia falha | `PdfminerException` genérica |
| 12 malformado | 532 | `FileDataError` | `PdfminerException` |
| 13 40 páginas | 34076 | **0,46 s / 56,5 MB** / 0 | **3,09 s / 187,5 MB** / 0 |
| 14 vetorial pesado | 43159 | 0,22 s / 60,5 / 0 | 0,60 s / 55,9 / 0 |

† A heurística “span de X > 120 ⇒ aligned” classificou prosa como aligned. **Não usar só span de X.**

### Extração qualitativa

- **Tabela ReportLab (com grid):** ambas as libs extraem cabeçalho e linhas corretamente, inclusive `02` sem o título “Movimentação”.
- **06 multi-seção:** 3 tabelas — CC, poupança (mesmo header `Data|Historico|Debito|Credito|Saldo`) e investimentos (`Produto|...|Perfil risco`). Um genérico “pega toda tabela com datas e dinheiro” **mistura produtos**.
- **04 multilinha:** célula de histórico junta `PIX ENVIADO\nJOAO...\nCPF ***.111.222-**`. Correto estruturalmente; arrasta PII extra para a descrição se não sanitizarmos.
- **05 multipage:** tabelas encontradas, **células erradas** (descrição cortada no meio da palavra, débito vira lixo). Reconciliação por valor parseável deve falhar nessas linhas — se o código “pular linha suja”, cai o recall sem o usuário saber.
- **07 app-like:** `extract_text()` concatena `SALDO ANTERIOR 1.250,00` na mesma linha visual à direita; **sem coordenadas, o parser linear inventa colunas**.
- **08 ordem invertida:** `get_text("text")` começa em `2.687,92` (último lançamento desenhado primeiro). Ordenar words por `(y, x)` recupera a ordem visual (com ressalvas).
- **10 scan:** PyMuPDF `text_len=0`, 1 imagem. Detectável. pdfplumber também 0 texto; minha classificação automática dele errou para `textual_linear`.
- **11 senha:** PyMuPDF: `is_encrypted`, `authenticate("")` falso, `authenticate("user-secret")` verdadeiro. pdfplumber: exceção opaca — **detectar senha com a lib que expõe o flag, ou pelo trailer, antes do parse**.

### E2. PDF real Santander (21/08/2026)

Arquivo local, **não commitado**. Gerador: Compart (`MFFPDF` / Docponent). PDF 1.3, **não criptografado**.

| Métrica | Valor |
| ------- | ----- |
| Páginas | 11 (todas com texto; 0 página só-imagem) |
| Tamanho | 212 744 bytes (~208 KB) |
| Caracteres / palavras | ~25 400 / 3 674 |
| Imagens (marca/logo) | 13 |
| Drawings (vetores) | 2 811 |
| Classe | `textual_aligned` (não raster; **não** `textual_tabular` útil) |
| PyMuPDF `get_text("words")` | **0,040 s**, RSS ~54 MB (+4 MB) |
| PyMuPDF `find_tables()` | **2,61 s**, 27 tabelas |
| pdfplumber `extract_text`+`extract_tables` | **1,85 s**, RSS **130 MB**, 26 tabelas |
| Linhas data+valor **dentro** das tabelas detectadas | **0** (ambas as libs) |
| Vocabulário no documento | conta corrente, movimentação, pix (~119), aplicação, investimento, poupança, limite, crédito, IR/IOF, perfil, agência |

Geometria das movimentações (páginas com maior densidade data+valor na **mesma faixa Y**):

- Datas quase todas `dd/mm` **sem ano** (tokens de 5 caracteres). Regex só `dd/mm/aaaa` pega 1 data/página (o período) e **perde o extrato**.
- Coluna de data estável à esquerda (~x=34); valores à direita (~x=523–530) nas páginas de conta.
- Cabeçalhos de coluna presentes: `data`, `descrição`, `valor`, `débito` — não é preciso o título “Movimentação” para achar a região.
- Tabela de movimento **continua na página seguinte** com cabeçalho parcial (`data`/`valor` só).
- Páginas de investimento: **várias** colunas `valor` (x≈237, 330, 410, 482) + `perfil` — geometria distinta; misturar com CC é o bug de produto.
- Ordem de desenho ≠ ordem visual na capa (`extract_text` vs sort `(y,x)`).
- ~7 linhas candidatas a continuação de descrição (multilinha) numa página de movimento.

Implicações para o genérico:

1. **Não ligar `find_tables` no caminho quente** deste layout: caro e não aponta as transações.  
2. Ano da data = período do extrato (capa / “junho/AAAA”), não a célula.  
3. Fingerprint útil: `date_x_left + amount_x_right + headers{data,descricao,valor}` — sem PII.  
4. Recusar raster neste PDF seria falso negativo (há logos, mas o texto existe). Critério: densidade de caracteres por página, não presença de imagem.

### E3. Bradesco, Nubank e Caixa (21/08/2026)

Arquivos locais, **não commitados**. `find_tables` / `extract_tables`: **0 linhas de movimento** nos três.

| | Bradesco (5 p., 17 KB) | Nubank (2 p., 23 KB) | Caixa (1 p., 367 KB) |
| --- | --- | --- | --- |
| Texto | 5/5 páginas digitais | 2/2 digitais | **0 texto — 1 JPEG 1957×3230** |
| Gerador | (vazio) | openhtmltopdf | pdfmake (a página é imagem) |
| Classe | `textual_aligned` | `textual_aligned` (data como cabeçalho) | **`raster`** |
| Tabelas detectadas | 5 / 0 úteis | 0 | 0 |
| Tokens data / dinheiro | 83 / 149 | 0 no padrão `dd/mm`; ~14 valores | 0 / 0 |
| `words` PyMuPDF | 13 ms | 6 ms | 1 ms |
| pdfplumber | 0,30 s / ~83 MB | 0,09 s / ~87 MB | instantâneo (vazio) |

**Bradesco.** Cabeçalhos `data`, `histórico`, `crédito`, `débito`, `saldo` em todas as páginas. Duas colunas de data (x≈50 e x≈220–230). Data e valor frequentemente **não** estão no mesmo Y estreito (em `tol=3` há ~21 linhas data+valor; com `tol=12` sobe). Genérico “mesma linha Y” do Santander **subconta**. Recuperável com junção de linha mais folgada + papéis de coluna.

**Nubank.** Datas **não** são `dd/mm`. São dia numérico + mês por extenso (`jan`…`dez`) + ano, muitas vezes como **cabeçalho de grupo**: poucas linhas têm dia+mês+valor juntos (2), enquanto há ~14 linhas só de valor. O lançamento herda a data do bloco acima. `find_tables` não vê nada. Ainda é digital e determinístico — família de layout distinta, não OCR.

**Caixa.** Scan/foto da página inteira. Sem camada de texto. **Recusar no v1** (código `SCANNED_PDF`). OCR só numa fase posterior.

### E3b. Mais dois PDFs reais (21/08/2026)

Arquivos locais, **não commitados**. Sem PII abaixo.

| | Comprovante 2 p. (~981 KB) | Nubank jul (5 p., ~37 KB) |
| --- | --- | --- |
| Texto | **0 — 2 JPEG 1957×3230** | 5/5 digitais |
| Gerador | pdfmake (igual ao Caixa) | openhtmltopdf (igual ao Nubank 2 p.) |
| Classe | **`raster`** | `textual_aligned` |
| `find_tables` | 0 | 0 |
| Tokens data / mês / dinheiro | 0 / 0 / 0 | 0 no `dd/mm`; 32 meses; 73 valores |
| Candidatos (interpretador `y_tol=4`) | 0 em **todas** as 5 libs | **61** (PyMuPDF, pdfplumber, pypdfium2, pdf-oxide); pypdf **12** |
| Jaccard mu×pl | 1,0 (ambos vazios) | **1,0** |

**Comprovante 2 p.** É o mesmo padrão do Caixa: pdfmake embrulhando foto da página. Recusar no v1 (`SCANNED_PDF`). Dois scans no corpus (1 p. e 2 p.) confirmam que a recusa não é um caso isolado.

**Nubank 5 p.** Mesma família do Nubank 2 p. (HTML→PDF, data por extenso, `find_tables` = 0). O interpretador atual acha **61** candidatos vs **7** no arquivo curto — mais linhas com dia/mês e valor na mesma faixa Y. As quatro libs “sérias” empatam; o pypdf continua ruim.

Nos **6 PDFs reais**, o detector de tabela **nunca** devolveu o extrato. Nos **4 digitais**, as transações são identificáveis por geometria de palavras. Nos **2 rasters**, zero texto.

### E4. Assertividade PyMuPDF vs pdfplumber (21/08/2026)

Protocolo: o **mesmo** interpretador genérico (cluster de palavras por Y, data+valor na linha, saldo = token monetário mais à direita) recebe `page.get_text("words")` ou `page.extract_words()`. Script: `docs/arquitetura/spike_importacao_pdf/compare_assertiveness.py`. JSON bruto em `/tmp/spike_pdf_corpus/assertiveness.json` (não versionado).

Métrica principal nos sintéticos: **F1 identidade** = acerto de `(data, valor)`, ignorando tipo e descrição. Isso responde “achou o lançamento?”, não “acertou D/C”. Gabarito = gerador (`MOVIMENTOS` etc.). `y_tol = 4`.

PDFs reais: **sem gabarito humano** (PII). Métrica = Jaccard do conjunto hasheado `(página, data, valor, tipo)` entre as duas libs — acordo, não verdade absoluta.

| Arquivo | n ouro | F1 id PyMuPDF | F1 id pdfplumber | Jaccard entre libs |
| ------- | ------ | ------------- | ---------------- | ------------------ |
| 01 tabela com grid | 9 | 0,947 | 0,947 | 1,0 |
| 02 sem título | 9 | 1,0 | 1,0 | 1,0 |
| 03 valor com sinal | 9 | 1,0 | 1,0 | 1,0 |
| 04 multilinha | 4 | 1,0 | 1,0 | 1,0 |
| **05 multipage + header** | **80** | **1,0** | **0,013** | **0,0** |
| 06 multi-seção | 11 | 0,88 | 0,88 | 1,0 |
| 07 texto alinhado sem Table | 9 | 1,0 | 1,0 | 1,0 |
| 08 ordem de desenho invertida | 9 | 0,80 | 0,889 | 0,5 |
| 09 prosa linear | 9 | 1,0 | 1,0 | 1,0 |
| 10 só imagem | 0 | 1,0 | 1,0 | 1,0 |
| 13 40 páginas | 1280 | 1,0 | 1,0 | 1,0 |
| 14 vetorial pesado | 9 | 1,0 | 1,0 | 1,0 |

Notas onde F1 ≠ 1,0 **nas duas** (interpretador, não lib):

- **01:** FP extra do rodapé “Saldo inicial | Saldo final” (as duas).
- **04:** identidade 1,0; F1 com descrição 0,75 (CPF da célula multilinha não entra na mesma linha Y — as duas).
- **06:** recall 1,0 da CC+poupança; 3 FPs de investimento (as duas). Confirma que região precisa de escolha, não de lib.
- **09:** identidade 1,0; descrição falha porque a prosa junta as colunas com `\|` (as duas).

Divergência **entre libs**:

1. **05 (o caso grave).** PyMuPDF: 80/80, valor = débito. pdfplumber: 80 linhas, **79 valores errados**. `extract_words` funde a última palavra da descrição com o débito (`TESTE` + `10,00` → `T1E0,S0T0E`); o interpretador então pega o **saldo** (`990,00`) como movimento. É o mesmo sangramento já visto em `find_tables`, agora no caminho de palavras. Correção financeira: o pdfplumber **inventa o valor** neste layout.

2. **08 (sobreposição de desenho).** PyMuPDF devolve **44** palavras vs **70** do pdfplumber: some linhas de baixo (recall 0,67). pdfplumber recupera mais linhas (F1 0,889) mas mistura glifos sobrepostos (`1E2x/0t3r/2a0t2o6`). Aqui o pdfplumber ganha recall e perde limpeza de texto.

| PDF real | Palavras mu / pl | Candidatos mu / pl | Jaccard |
| -------- | ---------------- | ------------------ | ------- |
| Santander | 3674 / 3595 | 126 / 126 | 0,983 |
| Bradesco | 932 / 932 | 72 / 72 | 1,0 |
| Nubank | 356 / 277 | 7 / 7 | 1,0 |
| Caixa | 0 / 0 | 0 / 0 | 1,0 |
| Comprovante 2 p. | 0 / 0 | 0 / 0 | 1,0 |
| Nubank 5 p. | 1197 / 1197 | 61 / 61 | 1,0 |

Nos digitais deste corpus, PyMuPDF e pdfplumber **concordam** no conjunto de candidatos do interpretador atual. Isso **não** prova gabarito do banco. Nubank 2 p. com 7 candidatos continua subcontagem (cabeçalho de grupo); o Nubank 5 p. sobe para 61, **igual nas duas**.

Conclusão da assertividade: o pdfplumber **não** é “igual, só mais lento”. É igual no extrato app-like e nos digitais reais deste spike; é **inaceitável** no layout de tabela apertada com cabeçalho repetido, exatamente o caso em que o valor financeiro sai errado.

### E5. Outras libs OSS (21/08/2026)

Mesmo interpretador de §E4. Venv `/tmp/spike_pdf_venv`. Script: `docs/arquitetura/spike_importacao_pdf/compare_more_libs.py`.

| Lib | Licença | Por que testar |
| --- | ------- | -------------- |
| **pypdfium2** 5.13 (PDFium/Chromium) | Apache-2.0 + BSD do PDFium | Permissiva, palavras via `get_charbox` |
| **pdf-oxide** 0.3.77 (Rust) | MIT | Permissiva, API `page.words` |
| **pypdf** 6.16 | BSD-3 | Já comum em Python; visitor com posição |

Não testadas de propósito:

- **pdfminer.six** — o pdfplumber já é essa pilha.
- **Poppler / pdftotext** — GPL-2; mesmo problema de copyleft do AGPL para SaaS fechado.
- **Camelot / Tabula** — detector de tabela; o spike já mostrou que esse caminho não acha o extrato.
- **Tesseract / OCR** — fora do v1.
- **borb**, bindings MuPDF — AGPL de novo.

F1 identidade nos sintéticos (trecho relevante):

| Arquivo | PyMuPDF | pdfplumber | pypdfium2 | pdf-oxide | pypdf |
| ------- | ------- | ---------- | --------- | --------- | ----- |
| 01–04, 07, 09, 10, 13, 14 | = | = | = | = | = |
| **05** multipage apertado | **1,0** | **0,013** | **1,0** | **1,0** | **1,0** |
| **08** desenho invertido | 0,80 | 0,889 | **1,0** | 0,80 | **1,0** |
| 06 multi-seção | 0,88 | 0,88 | 0,88 | 0,88 | 0,88 |

PDFs reais (candidatos do interpretador, sem gabarito):

| PDF | PyMuPDF | pdfplumber | pypdfium2 | pdf-oxide | pypdf |
| --- | ------- | ---------- | --------- | --------- | ----- |
| Santander | 126 | 126 | 126 | 126 | **59** |
| Bradesco | 72 | 72 | 72 | 72 | **1** |
| Nubank 2 p. | 7 | 7 | 7 | 7 | **1** |
| Caixa | 0 | 0 | 0 | 0 | 0 |
| Comprovante 2 p. | 0 | 0 | 0 | 0 | 0 |
| Nubank 5 p. | 61 | 61 | 61 | 61 | **12** |

Tempo no Santander (só extração+interpretador, ordem de grandeza): PyMuPDF ~47 ms, pdf-oxide ~76 ms, pypdfium2 ~270 ms, pypdf ~400 ms, pdfplumber ~1,3 s.

Leitura:

- **pypdfium2** e **pdf-oxide** acertam o caso 05 em que o pdfplumber inventa o valor. Nos 6 reais, o número de candidatos bate com o PyMuPDF (pypdf não).
- **pypdfium2** ainda ganha no 08 (não perde as linhas sobrepostas).
- **pdf-oxide** é o mais rápido das permissivas (parecido com PyMuPDF). Pacote jovem (0.3.x) — risco de API/maturidade.
- **pypdf** serve no sintético ReportLab e **quebra** no extrato real (visitor junta/parte mal as células). Não usar no v1.

Implicação de produto: se a licença AGPL impedir o PyMuPDF, **não cair no pdfplumber por default**. A alternativa permissiva que se comporta como o PyMuPDF neste corpus é **pypdfium2** (mais estabelecida) ou **pdf-oxide** (mais rápida, menos madura).

---

## F. Arquitetura recomendada

```text
[UI] 3º botão Importar PDF (v1) → conta GranaGo + arquivo
        │
        ▼
Higiene no web (auth, CSRF, magic %PDF, ≤6 MB, ≤30 págs, rate limit)
        │
        ▼
Tempfile 0700 em /var/lib/financeiro/tmp-import  (NÃO media, NÃO /tmp 1777, NÃO Redis)
        │
        ▼
Celery fila `imports`  (mesmo host; task recebe path sandboxado)
        │
        ▼
Worker: PyMuPDF *ou* pdfplumber (ver licença)
  - raster? recusar
  - senha? recusar
  - palavras + bbox, ordenadas (y,x)
  - propor regiões (find_tables ∪ cluster de colunas)
  - classificar região (movimento vs outro)
  - se 2+ movimento → NÃO fundir; devolver opções
  - interpreter[layout_key] ou generic_table_v1
  - LinhaOfx[] + validação composta + estado do lote
  - unlink PDF no finally
        │
        ▼
Job/resultado TTL curto: só linhas normalizadas + metadados técnicos
        │
        ▼
Poll → mesmo payload de preview OFX
        │
        ├─ N regiões de movimento → passo extra: escolher seção
        │
        ▼
Revisão (feed atual) → categorizar-import-batch (contexto import_pdf)
        │
        ▼
importar_ofx_confirmar → Transacao
```

O web **não** chama a lib PDF no processo Gunicorn.

---

## G. Estratégia de layouts

### Classificação do documento (substitui digital vs scan)

| Classe | Sinal | v1 |
| ------ | ----- | --- |
| `raster` | ~0 texto extraível e há imagens de página | recusar |
| `textual_tabular` | `find_tables`/`extract_tables` com cabeçalho de movimento | interpreter tabular |
| `textual_aligned` | poucas/nenhuma tabela; colunas por clusters de X; coluna de datas | **caminho principal do genérico** |
| `textual_linear` | texto sem grade de colunas | recusar ou baixa (não parece extrato) |
| `encrypted` / `malformed` | flags/exceções | recusar |

Não adotei os nomes “semi-estruturado / desestruturado” porque não são operacionais. As quatro classes acima mapeiam para código.

### Fingerprint → `layout_key`

Usar só sinais **não-PII** e relativamente estáveis:

- tokens de cabeçalho de coluna normalizados e ordenados (`data|historico|debito|credito|saldo`);
- número de colunas;
- papéis detectados (DATE, DESC, DEBIT, CREDIT, AMOUNT, BALANCE);
- posições X **relativas** à largura da página (quantizadas, ex. décimos);
- presença de grid vs só texto.

Não usar: nome do titular, agência, conta, CPF, logos, cores, Producer com caminho de usuário.

`layout_key` exemplo: `cols5_date_desc_d_c_bal_relx_v1`. Marca do banco é atributo opcional de telemetria, não chave de `if`.

Mudança visual pequena (margem, fonte): relativa X costuma sobreviver. Redesign de colunas: chave nova → cai no genérico; adapter antigo **não** deve ser forçado.

### Versionar e aposentar adapter

- Adapter declara `layout_key` + versão.
- Telemetria: `layout_key × estado_lote × % linhas desmarcadas pelo usuário`.
- Se um adapter conhecido passa a ter reconciliação falha **quando âncora existe**, ou usuários desmarcam em massa: marcar `stale`, fallback para genérico, alerta ops.
- Não há regra “5 falhas”. Há **impacto financeiro** (direção/valor errados) vs **frequência**. Um erro de direção sistemático em 20% dos lotes de um layout justifica adapter (ou stale) mais do que 50 recusas de scan.

### Quando criar adapter

Criar quando:

- o genérico erra **valor ou direção** de forma repetível naquela família;
- generalizar o genérico para corrigir isso pioraria outros layouts (overfit);
- o layout é estável o bastante (mesmo `layout_key` em vários PDFs).

Não criar quando:

- o erro é “PDF é scan”;
- o erro é “usuário mandou comprovante avulso”;
- dá para corrigir no genérico com heurística de coluna sem quebrar o resto;
- só um PDF de um usuário.

**Não** começar por `santander.py`.

---

## H. Validação financeira

A reconciliação **não é independente** da extração do saldo. Pode fechar com:

- linha omitida e saldo final lido da mesma seção errada;
- duas linhas fundidas cujo total coincide;
- direção invertida em duas linhas que se cancelam;
- saldo de **outra** tabela (poupança) aplicado na corrente.

Por isso vira **hard gate só para o estado `alta`**, e só quando o saldo âncora veio da **mesma região** classificada como movimento escolhida pelo usuário.

| Check | Papel |
| ----- | ----- |
| Documento `raster` / senha / malformado / 0 região movimento | hard gate → `recusado` |
| Linha sem data parseável ou sem valor parseável | linha incompleta; **não selecionável** |
| Direção só por cor | não inferir; `baixa` se não houver C/D, sinal ou saldo |
| Região investimentos/crédito classificada como movimento | hard gate da região (não emitir linhas) |
| `saldo_inicial + C − D = saldo_final` na região escolhida | hard gate de **`alta`**; falha → “acreditamos que há erro” (`baixa`) |
| Sem saldo na região | “não conseguimos validar” (`media` se estrutura ok) |
| Running balance | sinal; quebra → warning, não recusar o lote |
| Totais C/D impressos | sinal / âncora alternativa se não houver saldo |
| Saldo disponível / limite / saldo de aplicação | **nunca** âncora |
| Duas regiões movimento | não validar o PDF inteiro como um ledger; validar **por região** |

---

## I. Confiança e UX

Quatro estados no **lote** (após o usuário escolher a região, se houver mais de uma) continuam suficientes. Por baixo, guardar `confianca_regiao` e `confianca_extracao` para telemetria; a UI não precisa de dois badges.

Diferenciar:

- **Não validamos** (sem âncora) → `media`, linhas completas pré-selecionadas, aviso amarelo.  
- **Acreditamos que está errado** (saldo da região não fecha; células ilegíveis em massa; mistura de seções evitada por pouco) → `baixa`, desmarcadas, aviso vermelho com a **razão em português**.

Confiança por linha: só o necessário — `completa` vs `incompleta` vs `possivel_duplicata`. Não score 0–1 por linha.

### Selecionar tudo na baixa confiança

A hipótese “desmarcar e deixar o usuário marcar” é **fraca**. O feed OFX já tem “marcar todos”, e a pessoa leiga vai usar.

Comportamento recomendado (sem teatro):

1. Banner persistente com a causa (`O saldo do período não fechou (diferença de R$ x,xx). Revise antes de importar.`).  
2. Linhas incompletas: checkbox **desabilitado**.  
3. `baixa`: confirmar exige um checkbox de ciência (`Li o aviso e quero importar as linhas marcadas`). Sem isso o botão de confirmar não habilita.  
4. “Marcar todos” em `baixa` **não** marca incompletas e **não** dispensa o checkbox de ciência.  
5. Não bloquear confirmar se o usuário marcou 3 linhas boas e deixou o resto fora — importação parcial é desejável.  
6. Não inventei um quarto modal. É o feed atual + uma linha de ciência.

`recusado`: sem feed, mensagem acionável (OFX, Excel, PDF com texto, um extrato por conta).

---

## J. Privacidade / LGPD

Superfície realista (não zero):

| Ponto | Risco | Controle |
| ----- | ----- | -------- |
| RAM do worker | PDF + estruturas da lib (pode ser >> bytes) | isolamento Celery; teto de páginas; timeout; `MemoryMax` já 1200M no celery |
| Swap | páginas do PDF no disco | swap reduzido é ops; não dá para zerar em Python |
| Core dump | dump do worker | `ulimit -c 0` no systemd (hoje não está explícito) |
| Tempfile | arquivo no disco segundos | dir 0700 da app; `PrivateTmp=true` já existe nos units; janitor 15 min; fora do backup de mídia |
| Redis | RDB/AOF persistiria o PDF | **não colocar bytes nem texto do PDF no broker** |
| `MEDIA_ROOT` | backup 30d + staff | não usar |
| Logs / Sentry | linha do Pix | allowlist; exceção sem célula; `send_default_pii=False` |
| Preview no browser | JSON com descrições (nomes Pix) | igual OFX; HTTPS; sessão; não gravar PDF em `localStorage` |
| DevTools | payload HTTP do preview | aceitável e equivalente ao OFX |
| Descrição persistida | nomes e, no sintético, CPF na célula | normalizar: strip de CPF/CNPJ; cap 255; **não** puxar comprovante |
| Terceiros | ISPB/conta na seção comprovante | não parsear essa região |
| Métricas | `layout_key`, contagens | sem valores, sem descrições |

O preview JSON **é** persistência temporária no cliente — igual OFX. Ser honesto na Política: processamos o arquivo, descartamos, e as transações confirmadas (com descrição) permanecem.

Sanitizar CPF na descrição é minimização extra em relação ao OFX; vale a pena porque o PDF multilinha **cola** o CPF na célula, o OFX nem sempre traz isso.

---

## K. Segurança (threat model atualizado)

Mantido: magic bytes, teto 6 MB / 30 páginas / 2000 linhas, senha recusada, sem JS, sem shell, IDOR inexistente (sem URL de arquivo), rate limit.

Novos/reforçados:

- **DoS de memória:** pdfplumber 187 MB em 40 páginas *sintéticas*. Hard limit de páginas **antes** de `pdf.pages[:]`. Timeout do task Celery (ex. 30 s soft / 45 s hard). Não parsear no Gunicorn.
- **CVE do parser:** blast radius = worker `imports`, não os 2 processos HTTP. Atualizar a lib.
- **Path traversal no task:** worker só abre path sob `tmp-import/` com nome UUID gerado pelo web.
- **Celery argument injection:** task recebe UUID, não path cru do cliente.
- **PDF zip-bomb:** teto de bytes já no upload; considerar teto de objetos se a lib expor.

Gunicorn atual: `workers=2`, `threads=2`, `timeout=120`, `MemoryMax=1500M`. Celery: `concurrency=2`, `MemoryMax=1200M`. Fila `imports` **separada** para não empacar export WeasyPrint.

---

## L. Performance e limites

Medido (sintético): ver tabela §E.

Limites recomendados no v1 (conservadores *porque o real não foi medido*):

- 6 MB (igual OFX; o maior sintético foi 58 KB — **não informa** o teto real; 6 MB é consistência, não calibração);
- 30 páginas (o exemplo de produto tem 11; 40 páginas já doeu no pdfplumber);
- timeout de extração 20–30 s;
- 1 PDF em voo por usuário;
- N/hora alinhado ao export.

**Não recomendo** limitar “objetos PDF” até escolhermos a lib e medirmos um extrato real — é especulação.

P50/P95 de produção: instrumentar `duration_ms` + `rss` do worker **sem PII**, depois do primeiro corpus real.

---

## M. Corpus de testes

“6 famílias” era um palpite útil; o spike mostrou **quais** famílias importam, não um número mágico.

### Mínimo para implementar o parser com teses falsificáveis (ainda não go-live)

Sintéticos (já esboçados, versionar geradores, não PII):

1. tabela com grid;  
2. sem título de seção;  
3. C/D vs valor com sinal;  
4. multilinha + PII na célula;  
5. multipage com header repetido (caso de célula podre);  
6. multi-seção CC + poupança + investimento;  
7. texto alinhado sem Table object;  
8. ordem de desenho ≠ visual;  
9. prosa;  
10. raster;  
11. senha;  
12. malformado.

### Mínimo para afirmar “podemos lançar”

Pelo menos **um PDF real anonimizado por família estrutural**, fora do git:

- extrato app, texto alinhado, uma conta;  
- comprovante/dossiê multi-seção;  
- tabela com grid (IB antigo, se existir);  
- sem coluna de saldo;  
- dois produtos (CC+poupança).

Negativos reais: fatura de cartão, comprovante Pix avulso, posição de investimentos.

Não precisamos dos “oito grandes bancos”. Precisamos dessas **formas**. Santander 11 páginas é o caso de dossiê, não o parser.

Métricas de qualidade no corpus rotulado:

- precisão e recall de **linhas de movimento da região escolhida**;  
- falso positivo de outras seções (investimento/poupança quando a escolha foi CC) — **métrica de privacidade e de ledger**;  
- taxa de linhas incompletas;  
- erros de direção e de valor (gabarito);  
- reconciliação quando o gabarito diz que deveria fechar;  
- falsa reconciliação (fechar com gabarito de linhas errado) se conseguirmos injetar.

Métricas de produto (depois do beta): % desmarcadas, % canceladas, % `layout_key` desconhecido, % `recusado` por raster. Sem isso no dia 1 de código.

---

## N. Critérios de produção

Antes de **implementar** a feature no app:

- [ ] Decisão escrita de licença (PyMuPDF comercial / AGPL inaceitável / pdfplumber).  
- [ ] Spike reexecutado em **pelo menos um** PDF bancário real anonimizado (tempo, RSS, tabelas vs words).  
- [ ] Concordância: isolamento Celery + tempfile 0700 + sem Redis para o arquivo.

Antes de **lançar**:

- [ ] Golden: investimento não vira `LinhaOfx` se a região escolhida é CC.  
- [ ] Golden: duas regiões movimento → UI pede escolha; não funde.  
- [ ] Golden: 07-like (sem Table) extrai N linhas gabarito ou cai em `baixa`/`recusado`, **nunca** em `alta` com lixo.  
- [ ] Célula ilegível ≠ valor inventado.  
- [ ] Raster recusado. Senha recusada.  
- [ ] PDF some do disco após o task (`finally` + janitor). Nada em `MEDIA_ROOT`.  
- [ ] Logs do fixture sem `R$` / nomes.  
- [ ] Preview + categorização + confirmar iguais ao OFX.  
- [ ] Flag fraca duplicata data+valor+tipo no preview.  
- [ ] `baixa` exige ciência para confirmar.  
- [ ] Política §3.3 atualizada com o que o código faz.  
- [ ] Fila `imports` não bloqueia export.

---

## O. Recomendação final

**Minha recomendação arquitetural é: tratar o PDF como job isolado (Celery + tempfile 0700 + `LinhaOfx`), com genérico por palavras+coordenadas e `find_tables` **desligado no default**. Porque o comprovante Santander real é digital, 11 páginas, 27 “tabelas” detectadas e **zero** linha de movimento nessas tabelas — as transações estão em colunas `dd/mm` + valor, e o `find_tables` ainda gasta 2,6 s. Misturar a região de investimento (várias colunas `valor`) com a de conta é o risco de produto. Isolar do Gunicorn permanece: pdfplumber neste arquivo foi a 130 MB RSS.**

**Não recomendo decidir PyMuPDF vs alternativa permissiva ainda — falta a licença AGPL.** Tecnicamente o PyMuPDF continua forte. Se não houver licença comercial: **pypdfium2** (Apache) ou **pdf-oxide** (MIT) acertam o sintético 05; o pdfplumber não. **pypdf** não serve no extrato real. Ver §E4–E5.

**Não recomendo parser `santander.py`, nem LLM/OCR no v1, nem FileField, nem PDF no Redis.**

**Recomendo no v1:** datas `dd/mm` com ano do período; escolha de região; flag fraca OFX×PDF; ciência em `baixa`; strip de CPF/CNPJ.

---

## P. Parecer de viabilidade (6 PDFs reais)

**A feature é viável para produção incremental. Não é viável como “um detector de tabela e pronto”.**

| PDF | Localiza transações sem OCR? | Como |
| --- | --- | --- |
| Santander | Sim | `dd/mm` + valor na mesma faixa Y |
| Bradesco | Sim | duas colunas de data; juntar linhas com Y mais folgado |
| Nubank (2 p.) | Sim | data = dia + mês por extenso como cabeçalho; valores herdam a data |
| Nubank (5 p.) | Sim | mesma família; interpretador atual: 61 candidatos (acordo entre 4 libs) |
| Caixa | Não no v1 | JPEG 1957×3230; recusar scan |
| Comprovante 2 p. | Não no v1 | mesmo padrão pdfmake+JPEG; recusar scan |

Nos seis, `find_tables`/`extract_tables` **não** devolveram o extrato. Nos quatro digitais, o texto está lá. Os dois rasters são o **mesmo** gerador (pdfmake + foto). Scan fica para OCR depois, com mensagem para usar OFX/Excel.

Go-live honesto: digital only + preview + recusa de raster + genérico por coordenadas + famílias de data (`dd/mm` e cabeçalho de mês). Não prometer todos os bancos. Licença PyMuPDF continua em aberto e não anula a viabilidade da extração.

---

## Apêndice: como reproduzir o spike

```bash
python3 -m venv /tmp/spike_pdf_venv
/tmp/spike_pdf_venv/bin/pip install pymupdf pdfplumber reportlab pillow pypdfium2 pdf-oxide pypdf
/tmp/spike_pdf_venv/bin/python docs/arquitetura/spike_importacao_pdf/generate_corpus.py --out /tmp/spike_pdf_corpus
/tmp/spike_pdf_venv/bin/python docs/arquitetura/spike_importacao_pdf/run_spike.py /tmp/spike_pdf_corpus
/tmp/spike_pdf_venv/bin/python docs/arquitetura/spike_importacao_pdf/compare_assertiveness.py /tmp/spike_pdf_corpus 4
/tmp/spike_pdf_venv/bin/python docs/arquitetura/spike_importacao_pdf/compare_more_libs.py /tmp/spike_pdf_corpus 4
```

Não instalar essas libs no `.venv` do GranaGo até a decisão de licença e o PR da feature.
