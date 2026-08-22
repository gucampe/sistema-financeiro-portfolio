# Spike isolado — não é código de produção

Geradores, benchmark de desempenho e comparação de assertividade (21/08/2026). Corpus e venv ficam em `/tmp` (ver `ANALISE_SPIKE_IMPORTACAO_PDF.md` §E e §E4).
Não adicionar estas bibliotecas ao `requirements.txt` do GranaGo sem decisão de licença.

- `generate_corpus.py` — PDFs sintéticos
- `run_spike.py` — tempo, RSS, tabelas, classe
- `compare_more_libs.py` — pypdfium2, pdf-oxide, pypdf no mesmo interpretador

