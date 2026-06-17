"""Configuração do Gunicorn para produção (Render)."""

import os

# Render injeta a porta via variável PORT.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Plano free: 1 worker + threads para estabilidade de memória no Render.
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "60"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
