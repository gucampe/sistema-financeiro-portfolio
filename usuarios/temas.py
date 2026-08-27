"""Preferência de aparência do SaaS (claro/escuro). Sem seguir o sistema."""

from __future__ import annotations

from django.conf import settings

TEMA_CLARO = "claro"
TEMA_ESCURO = "escuro"
TEMA_CHOICES = (
    (TEMA_CLARO, "Claro"),
    (TEMA_ESCURO, "Escuro"),
)
COOKIE_TEMA = "granago_tema"
COOKIE_MAX_AGE = 60 * 60 * 24 * 400


def normalizar_tema(valor: str | None) -> str:
    return TEMA_ESCURO if valor == TEMA_ESCURO else TEMA_CLARO


def tema_do_request(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        perfil = getattr(user, "perfil", None)
        if perfil is not None:
            return normalizar_tema(getattr(perfil, "tema", None))
    cookie = ""
    if request is not None:
        cookie = request.COOKIES.get(COOKIE_TEMA, "")
    return normalizar_tema(cookie)


def aplicar_cookie_tema(response, tema: str) -> None:
    response.set_cookie(
        COOKIE_TEMA,
        normalizar_tema(tema),
        max_age=COOKIE_MAX_AGE,
        httponly=False,
        samesite="Lax",
        secure=bool(getattr(settings, "SESSION_COOKIE_SECURE", False)),
        path="/",
    )
