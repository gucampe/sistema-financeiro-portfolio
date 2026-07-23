"""Resposta de lockout do django-axes (HTTP 429) com página brandada."""

from __future__ import annotations

from config.error_handlers import render_error_page


def lockout_response(request, credentials, *args, **kwargs):
    return render_error_page(request, "errors/429.html", 429)
