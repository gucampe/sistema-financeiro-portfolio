"""Middleware de manutenção planejada (HTTP 503)."""

from __future__ import annotations

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from config.error_handlers import render_error_page


def _is_allowlisted(path: str) -> bool:
    if path == "/health/" or path.startswith("/health/"):
        return True
    # WhiteNoise costuma atender static antes; allowlist defensiva.
    static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
    if not static_url.startswith("/"):
        static_url = "/" + static_url
    if path.startswith(static_url):
        return True
    return False


class MaintenanceModeMiddleware(MiddlewareMixin):
    """Se MAINTENANCE_MODE=True, responde 503 exceto allowlist (/health/, static)."""

    def process_request(self, request):
        if not getattr(settings, "MAINTENANCE_MODE", False):
            return None
        path = request.path or "/"
        if _is_allowlisted(path):
            return None
        return render_error_page(request, "errors/maintenance.html", 503)
