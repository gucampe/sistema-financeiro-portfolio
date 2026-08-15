"""Roteamento por host: site institucional + landing na raiz, SaaS em APP_HOST."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin


def _host(request) -> str:
    return request.get_host().split(":")[0].lower()


def _landing_hosts() -> set[str]:
    raw = getattr(settings, "LANDING_HOSTS", "") or ""
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _app_host() -> str:
    return (getattr(settings, "APP_HOST", "") or "").strip().lower()


# Paths que pertencem ao SaaS — na landing redirecionam para app.
_APP_PATH_PREFIXES = (
    "/login/",
    "/logout/",
    "/admin/",
    "/dashboard/",
    "/transacoes/",
    "/contas/",
    "/cartoes/",
    "/categorias/",
    "/categorizacao/",
    "/relatorios/",
    "/api/",
    "/senha/",
    "/configuracoes/",
    "/media/",
)


class HostRoutingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        app = _app_host()
        landing = _landing_hosts()
        if not app or not landing:
            return None

        host = _host(request)
        path = request.path

        # www → apex (fallback se nginx não redirecionou)
        if host.startswith("www.") and host[4:] in landing:
            apex = host[4:]
            return HttpResponsePermanentRedirect(f"https://{apex}{request.get_full_path()}")

        # Landing: paths do app → app subdomain
        if host in landing:
            if any(path == p.rstrip("/") or path.startswith(p) for p in _APP_PATH_PREFIXES):
                return HttpResponseRedirect(f"https://{app}{request.get_full_path()}")
            return None

        # App: raiz anônima → login
        if host == app and path in ("/", ""):
            if not getattr(request, "user", None) or not request.user.is_authenticated:
                return HttpResponseRedirect(f"https://{app}/login/")
            return HttpResponseRedirect(f"https://{app}/dashboard/")

        return None
