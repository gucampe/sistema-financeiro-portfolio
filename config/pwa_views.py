"""PWA do SaaS: manifest e service worker em URLs estáveis (sem hash)."""

from __future__ import annotations

from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.templatetags.static import static
from django.views.decorators.http import require_GET

_CACHE = "no-cache"
_PROD_APP_ID = "https://app.granago.com.br/"

SW_JS = """\
/* GranaGo PWA v1 — pass-through de rede.
 * Sem cache de HTML, HTMX, relatórios ou dados financeiros.
 */
self.addEventListener("fetch", function (event) {
  event.respondWith(fetch(event.request));
});
"""


def _host(request) -> str:
    return request.get_host().split(":")[0].lower()


def _app_host() -> str:
    return (getattr(settings, "APP_HOST", "") or "").strip().lower()


def _pwa_no_saas(request) -> bool:
    app = _app_host()
    if not app:
        return False
    return _host(request) != app


def _pwa_id(request) -> str:
    app = _app_host()
    if app == "app.granago.com.br":
        return _PROD_APP_ID
    if app:
        return f"{request.scheme}://{app}/"
    return request.build_absolute_uri("/")


def _icon(src: str, sizes: str, purpose: str) -> dict:
    return {
        "src": static(src),
        "sizes": sizes,
        "type": "image/png",
        "purpose": purpose,
    }


@require_GET
def web_manifest(request):
    if _pwa_no_saas(request):
        raise Http404()
    payload = {
        "id": _pwa_id(request),
        "name": "GranaGo",
        "short_name": "GranaGo",
        "lang": "pt-BR",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f4f5f7",
        "theme_color": "#f4f5f7",
        "icons": [
            _icon("img/icons/pwa/icon-192.png", "192x192", "any"),
            _icon("img/icons/pwa/icon-512.png", "512x512", "any"),
            _icon("img/icons/pwa/icon-192-maskable.png", "192x192", "maskable"),
            _icon("img/icons/pwa/icon-512-maskable.png", "512x512", "maskable"),
        ],
    }
    resp = JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
    resp["Content-Type"] = "application/manifest+json"
    resp["Cache-Control"] = _CACHE
    return resp


@require_GET
def service_worker(request):
    if _pwa_no_saas(request):
        raise Http404()
    resp = HttpResponse(SW_JS, content_type="application/javascript; charset=utf-8")
    resp["Cache-Control"] = _CACHE
    return resp
