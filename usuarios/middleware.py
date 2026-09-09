from __future__ import annotations

from usuarios.services.meta_conversions import capturar_fbclid


class MetaFbclidMiddleware:
    """Persiste o primeiro fbclid da sessão para montar o fbc na CAPI."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        capturar_fbclid(request)
        return self.get_response(request)
