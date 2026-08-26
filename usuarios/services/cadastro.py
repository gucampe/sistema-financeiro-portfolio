from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction

from usuarios.audit import registrar_audit, _client_ip
from usuarios.models import AuditLog, Consentimento, LeadPrimeirosDonos, Usuario
from usuarios.services.email_acesso import (
    enviar_email_ja_tem_acesso,
    enviar_email_setup,
    url_setup_conta,
)
from usuarios.utils import normalizar_email, normalizar_whatsapp

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoCaptura:
    setup_url: str = ""


def _reportar_falha_email(exc: Exception) -> None:
    logger.exception("Falha ao enviar e-mail de acesso Primeiros Donos.")
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def _pode_enviar_email(email: str) -> bool:
    if cache.get(f"setup_email:{email}"):
        return False
    limite = int(getattr(settings, "SETUP_EMAIL_RATE_LIMIT_PER_HOUR", 5))
    count = cache.get(f"setup_email_hour:{email}") or 0
    return int(count) < limite


def _marcar_email_enviado(email: str) -> None:
    cooldown = int(getattr(settings, "SETUP_EMAIL_COOLDOWN_SECONDS", 60))
    cache.set(f"setup_email:{email}", 1, timeout=max(cooldown, 1))
    hour_key = f"setup_email_hour:{email}"
    if cache.add(hour_key, 1, timeout=3600):
        return
    try:
        cache.incr(hour_key)
    except ValueError:
        cache.set(hour_key, 1, timeout=3600)


def _user_agent(request) -> str:
    if request is None:
        return ""
    return (request.META.get("HTTP_USER_AGENT") or "")[:256]


def _buscar_usuario(email: str) -> Usuario | None:
    user = Usuario.objects.filter(email=email).first()
    if user is not None:
        return user
    return Usuario.objects.filter(email__iexact=email).first()


def _criar_ou_obter_usuario(*, email: str, nome: str, whatsapp: str) -> tuple[Usuario, bool]:
    existente = _buscar_usuario(email)
    if existente is not None:
        return existente, False
    try:
        with transaction.atomic():
            user = Usuario.objects.create_user(
                email=email,
                password=None,
                nome=nome,
                whatsapp=whatsapp,
                origem=Usuario.ORIGEM_PRIMEIROS_DONOS,
            )
        return user, True
    except IntegrityError:
        user = _buscar_usuario(email)
        if user is None:
            raise
        return user, False


def _upsert_lead(*, email: str, nome: str, whatsapp: str, usuario: Usuario) -> LeadPrimeirosDonos:
    try:
        lead, _created = LeadPrimeirosDonos.objects.update_or_create(
            email=email,
            defaults={"nome": nome, "whatsapp": whatsapp},
        )
    except IntegrityError:
        lead = LeadPrimeirosDonos.objects.get(email=email)
        lead.nome = nome
        lead.whatsapp = whatsapp
        lead.save(update_fields=["nome", "whatsapp", "atualizado_em"])

    update_fields = ["nome", "whatsapp", "atualizado_em"]
    if lead.usuario_id is None:
        lead.usuario = usuario
        update_fields.append("usuario")
        lead.save(update_fields=update_fields)
    elif lead.nome != nome or lead.whatsapp != whatsapp:
        lead.save(update_fields=["nome", "whatsapp", "atualizado_em"])
    return lead


@transaction.atomic
def registrar_primeiro_dono(*, nome: str, email: str, whatsapp: str, request=None) -> ResultadoCaptura:
    email = normalizar_email(email)
    whatsapp = normalizar_whatsapp(whatsapp)
    nome = (nome or "").strip()

    usuario, created = _criar_ou_obter_usuario(email=email, nome=nome, whatsapp=whatsapp)

    if created or not usuario.has_usable_password():
        campos = []
        if usuario.nome != nome:
            usuario.nome = nome
            campos.append("nome")
        if usuario.whatsapp != whatsapp:
            usuario.whatsapp = whatsapp
            campos.append("whatsapp")
        if campos:
            campos.append("atualizado_em")
            usuario.save(update_fields=campos)

    _upsert_lead(email=email, nome=nome, whatsapp=whatsapp, usuario=usuario)

    Consentimento.objects.create(
        usuario=usuario,
        email=email,
        canal=Consentimento.CANAL_CAPTURA,
        versao_termos=getattr(settings, "LEGAL_TERMS_VERSION", "2026-08-25"),
        versao_privacidade=getattr(settings, "LEGAL_PRIVACY_VERSION", "2026-08-25"),
        ip=_client_ip(request),
        user_agent=_user_agent(request),
    )

    if created:
        registrar_audit(
            acao=AuditLog.ACAO_SIGNUP,
            usuario=usuario,
            request=request,
            metadata={"origem": "primeiros_donos"},
        )

    pendente = not usuario.has_usable_password()
    setup_url = url_setup_conta(usuario, request=request) if pendente else ""

    def _enviar():
        if not _pode_enviar_email(email):
            return
        try:
            if pendente:
                enviar_email_setup(usuario, setup_url)
            else:
                enviar_email_ja_tem_acesso(usuario, request=request)
            _marcar_email_enviado(email)
        except Exception as exc:
            _reportar_falha_email(exc)

    transaction.on_commit(_enviar)
    return ResultadoCaptura(setup_url=setup_url)
