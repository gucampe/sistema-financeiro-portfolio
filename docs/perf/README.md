# Baseline de performance

Artefatos gerados por `python manage.py audit_performance --json --output docs/perf/baseline.json`.

Variáveis úteis:

- `ENABLE_PERF_MIDDLEWARE=1` — decompõe TTFB em db/context/render/minify
- `ENABLE_MINIFY_HTML=0|1` — A/B minify-html
- `ENABLE_DASHBOARD_AGG_CACHE=1` + `REDIS_URL` — cache cross-request (após gates)

Comandos:

```bash
source .venv/bin/activate
python manage.py audit_performance --rounds 5 --json --output docs/perf/baseline-local.json
python manage.py perf_snapshot --email user@example.com --output docs/perf/snapshot.json
python manage.py profile_template_render --rounds 10
pytest tests/performance/ -m performance_budget
```
