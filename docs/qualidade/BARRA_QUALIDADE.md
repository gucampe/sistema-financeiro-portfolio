# Barra de qualidade — GranaGo

**Data:** 12/08/2026

Este documento define o que “está ok” significa daqui para frente. A UI é Django templates + HTMX: Playwright é o teste de frontend; não há suíte Jest.

## Comandos locais

Ative a `.venv` antes. O `pytest` default **não** sobe o browser.

| Comando | O que cobre |
|---------|-------------|
| `make test-unit` | Unitário/integration completo, sem `performance_extended` e sem E2E |
| `make test-e2e-mvp` | E2E bloqueante (auth, dashboard, transações, transferências, faturas, import OFX, invariantes) |
| `make test-e2e-smoke` | Contas, categorias, configurações, onboarding e landing |
| `make test-e2e` | E2E amplo (exceto synthetic) |
| `make test` | Alias de `test-unit` |

Use Postgres local (`DB_*` no `.env`). Se `DATABASE_URL` apontar para um banco remoto (ex.: Neon), a suíte fica impraticável. Para forçar o banco local: `DATABASE_URL= make test-unit`.

## Gates

| Gate | Critério |
|------|----------|
| Local, antes de commit | `make test-unit` |
| Local, feature de UI | `make test-e2e-mvp` e, se mexer em contas/categorias/config, `make test-e2e-smoke` |
| PR | Unitário completo + E2E MVP + smoke cadastro + `performance_pr` + pip-audit (workflow `e2e.yml`) |
| Merge `master`/`main` | E2E extended (já existia; agora com Postgres) |
| Deploy VPS | Workflow `deploy-vps` só após E2E verde |
| Produção | Synthetic `/health/` + smoke (`synthetic-monitoring.yml`) |

## O que o CI cobre agora

- Job `financial-contracts`: `pytest -m "not performance_extended" --ignore=e2e` em Postgres 16.
- Job `e2e-mvp` (PR): MVP + integrity + segurança/concurrency + `cadastro_smoke`.
- Job `e2e-extended` (push master/main): suíte E2E ampla + stress de import OFX.
- `migrations.yml`: migrate + testes de migration **sem** `continue-on-error`.

## Fora desta barra (backlog)

- Coverage percentual com pytest-cov e gate rígido.
- axe/a11y sistemático (dependência instalada, não usada).
- Postgres no job synthetic-local.
- E2E das regras de categorização IA na UI.
- Download de export por share token sem autenticação.
