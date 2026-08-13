# Plano de verificação e malha de qualidade — GranaGo

**Data:** 12/08/2026

## Diagnóstico

O produto já tinha uma suíte grande (~500 testes pytest + ~132 E2E Playwright). O problema não era “não ter testes”; era **eles não formarem um gate confiável**.

Achados:

- `pytest.ini` não incluía `transacoes/tests`, `categorizacao/tests`, `config/tests` nem `core/tests`.
- O job CI `financial-contracts` cobria só um recorte. Ficavam de fora: transferências, parse OFX/XLSX, preview/confirm, onboarding, pipeline de categorização, CRUD de contas/categorias.
- E2E extended só rodava em push para `master`/`main`.
- O workflow E2E principal não subia Postgres, apesar das settings exigirem PostgreSQL.
- `contas/tests.py` e `categorias/tests.py` eram stubs vazios.
- Marker `performance_extended` era usado e não estava registrado (`--strict-markers`).
- Sem `make test`. Frontend é Django+HTMX: o caminho certo é E2E, não Jest.

## Fase 1 — Diagnóstico e correção

1. Rodar unitário completo (Postgres local; Neon remoto é inviável para a suíte inteira).
2. Rodar E2E MVP + smoke de cadastro.
3. Catalogar falhas em `docs/qualidade/RELATORIO_VERIFICACAO.md`.
4. Corrigir bugs de produto encontrados.

## Fase 2 — Malha permanente

1. `testpaths` completo; E2E fora do `pytest` default; marker `performance_extended` e `cadastro_smoke`.
2. Makefile: `test`, `test-unit`, `test-e2e-mvp`, `test-e2e-smoke`, `test-e2e`.
3. CI com Postgres 16; unitário completo em PR; smoke contas/categorias/config/onboarding/landing em PR.
4. Testes unitários e E2E de contas, categorias, configurações, onboarding e landing.
5. Barra de qualidade em `docs/qualidade/BARRA_QUALIDADE.md`.

Nada vai para produção direto: alteração local → commit → merge develop/master → pull na VPS.
