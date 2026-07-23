"""Handlers e helpers para páginas de erro brandadas do GranaGo.

handler500 não chama sentry_sdk.capture_* — o DjangoIntegration já captura.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse


CACHE_NO_STORE = "no-store"


def _safe_reverse(name: str, fallback: str) -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def _host(request: HttpRequest) -> str:
    try:
        return request.get_host().split(":")[0].lower()
    except Exception:
        return ""


def _landing_hosts() -> set[str]:
    raw = getattr(settings, "LANDING_HOSTS", "") or ""
    return {h.strip().lower() for h in raw.split(",") if h.strip()}


def _app_host() -> str:
    return (getattr(settings, "APP_HOST", "") or "").strip().lower()


def _is_landing_host(request: HttpRequest) -> bool:
    host = _host(request)
    landing = _landing_hosts()
    return bool(host and landing and host in landing)


def _is_authenticated(request: HttpRequest) -> bool:
    try:
        user = getattr(request, "user", None)
        return bool(user is not None and user.is_authenticated)
    except Exception:
        return False


def _absolute_app_login() -> str:
    app_login = (getattr(settings, "APP_LOGIN_URL", "") or "").strip()
    if app_login:
        return app_login
    return _safe_reverse("usuarios:login", "/login/")


def error_page_context(request: HttpRequest, *, status: int) -> dict[str, Any]:
    """Contexto mínimo de CTAs conforme host e autenticação."""
    on_landing = _is_landing_host(request)
    authenticated = _is_authenticated(request)

    landing_url = _safe_reverse("usuarios:landing", "/")
    login_url = _safe_reverse("usuarios:login", "/login/")
    dashboard_url = _safe_reverse("relatorios:home", "/dashboard/")
    app_login = _absolute_app_login()

    if on_landing:
        primary_url, primary_label = landing_url, "Ir para o início"
        secondary_url, secondary_label = app_login, "Entrar"
        brand_url = landing_url
    elif authenticated:
        primary_url, primary_label = dashboard_url, "Ir para o Dashboard"
        secondary_url, secondary_label = _safe_reverse("transacoes:historico", "/transacoes/"), "Transações"
        brand_url = dashboard_url
    else:
        primary_url, primary_label = login_url, "Entrar"
        secondary_url, secondary_label = landing_url, "Ir para o site"
        brand_url = login_url

    if status == 429:
        if authenticated and not on_landing:
            primary_url, primary_label = dashboard_url, "Ir para o Dashboard"
            secondary_url, secondary_label = login_url, "Tentar novamente mais tarde"
        else:
            primary_url, primary_label = login_url, "Voltar ao login"
            secondary_url, secondary_label = landing_url, "Ir para o site"
        brand_url = login_url if not on_landing else landing_url

    if status == 503:
        primary_url, primary_label = brand_url, "Tentar novamente"
        secondary_url, secondary_label = "", ""

    return {
        "status_code": status,
        "brand_url": brand_url,
        "primary_url": primary_url,
        "primary_label": primary_label,
        "secondary_url": secondary_url,
        "secondary_label": secondary_label,
        "is_authenticated": authenticated,
        "on_landing": on_landing,
    }


def _apply_error_headers(response: HttpResponse, status: int) -> HttpResponse:
    response["Cache-Control"] = CACHE_NO_STORE
    response["X-Robots-Tag"] = "noindex, nofollow"
    if status in (429, 503) and "Retry-After" not in response:
        # Valor genérico quando a janela exata não é conhecida.
        response["Retry-After"] = "120"
    return response


def render_error_page(request: HttpRequest, template_name: str, status: int) -> HttpResponse:
    context = error_page_context(request, status=status)
    response = render(request, template_name, context, status=status)
    return _apply_error_headers(response, status)


def render_error_page_resilient(request: HttpRequest, template_name: str, status: int) -> HttpResponse:
    """Render sem RequestContext (sem context processors) — uso no handler500."""
    context = error_page_context(request, status=status)
    try:
        html = render_to_string(template_name, context)
    except Exception:
        html = (
            "<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
            "<meta name=\"robots\" content=\"noindex\"><title>Erro | GranaGo</title></head>"
            "<body><h1>Algo deu errado</h1>"
            "<p>Tente novamente em alguns instantes.</p>"
            f"<p><a href=\"{context['primary_url']}\">{context['primary_label']}</a></p>"
            "</body></html>"
        )
    response = HttpResponse(html, status=status, content_type="text/html; charset=utf-8")
    return _apply_error_headers(response, status)


def handler404(request, exception=None):
    return render_error_page(request, "errors/404.html", 404)


def handler403(request, exception=None):
    return render_error_page(request, "errors/403.html", 403)


def csrf_failure(request, reason=""):
    """Usado via CSRF_FAILURE_VIEW — mesma UX do 403, sem detalhar o motivo."""
    return render_error_page(request, "errors/403.html", 403)


def handler500(request):
    # Sem capture_exception: Sentry DjangoIntegration já registrou o erro.
    return render_error_page_resilient(request, "errors/500.html", 500)
