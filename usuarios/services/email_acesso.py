from __future__ import annotations

from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from usuarios.tokens import conta_setup_token_generator
from usuarios.utils import primeiro_nome

WHATSAPP_SUPORTE = "11931496081"
WHATSAPP_SUPORTE_DISPLAY = "(11) 93149-6081"


def url_absoluta_app(path: str, request=None) -> str:
    path = path if path.startswith("/") else f"/{path}"
    host = (getattr(settings, "APP_HOST", "") or "").strip()
    usar_app_host = bool(host) and (
        getattr(settings, "IS_PRODUCTION", False) or not settings.DEBUG
    )
    if usar_app_host:
        return f"https://{host}{path}"
    if request is not None:
        return request.build_absolute_uri(path)
    if host:
        return f"http://{host}{path}"
    site = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    if site:
        return urljoin(site + "/", path.lstrip("/"))
    return path


def url_setup_conta(usuario, *, request=None) -> str:
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = conta_setup_token_generator.make_token(usuario)
    path = reverse("usuarios:conta_configurar", args=[uid, token])
    return url_absoluta_app(path, request)


def url_redefinir_senha(*, request=None) -> str:
    return url_absoluta_app(reverse("usuarios:password_reset"), request)


def _contexto_email(usuario, extra: dict | None = None) -> dict:
    ctx = {
        "nome": usuario.nome,
        "primeiro_nome": primeiro_nome(usuario.nome) or usuario.nome,
        "email": usuario.email,
        "whatsapp_suporte_display": WHATSAPP_SUPORTE_DISPLAY,
        "whatsapp_suporte_url": f"https://wa.me/55{WHATSAPP_SUPORTE}",
    }
    if extra:
        ctx.update(extra)
    return ctx


def _enviar(assunto: str, texto: str, html: str, destinatario: str) -> None:
    msg = EmailMultiAlternatives(
        subject=assunto,
        body=texto,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[destinatario],
    )
    if html:
        msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=False)


def enviar_email_setup(usuario, setup_url: str) -> None:
    ctx = _contexto_email(usuario, {"setup_url": setup_url})
    assunto = render_to_string("usuarios/emails/acesso_setup_subject.txt", ctx).strip()
    texto = render_to_string("usuarios/emails/acesso_setup.txt", ctx)
    html = render_to_string("usuarios/emails/acesso_setup.html", ctx)
    _enviar(assunto, texto, html, usuario.email)


def enviar_email_ja_tem_acesso(usuario, *, request=None) -> None:
    login_url = url_absoluta_app(reverse("usuarios:login"), request)
    reset_url = url_redefinir_senha(request=request)
    ctx = _contexto_email(usuario, {"login_url": login_url, "reset_url": reset_url})
    assunto = render_to_string("usuarios/emails/ja_tem_acesso_subject.txt", ctx).strip()
    texto = render_to_string("usuarios/emails/ja_tem_acesso.txt", ctx)
    html = render_to_string("usuarios/emails/ja_tem_acesso.html", ctx)
    _enviar(assunto, texto, html, usuario.email)
