"""Configuração do Gunicorn para produção (Render)."""

import os

# Render injeta a porta via variável PORT.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Plano free: poucos workers para economizar memória.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))

timeout = 120
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
