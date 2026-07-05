"""Configuração do Gunicorn para produção (VPS / Render)."""

import os

# VPS: GUNICORN_BIND=127.0.0.1:8000 (atrás do nginx).
# Render: PORT injetado automaticamente.
_bind = os.environ.get("GUNICORN_BIND", "").strip()
if _bind:
    bind = _bind
else:
    bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
