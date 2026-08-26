"""Audit log mínimo (LGPD / segurança)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

from usuarios.models import AuditLog


def _client_ip(request) -> str | None:
    if request is None:
        return None
    cf = (request.META.get("HTTP_CF_CONNECTING_IP") or "").strip()
    if cf:
        return cf[:45]
    real = (request.META.get("HTTP_X_REAL_IP") or "").strip()
    if real:
        return real[:45]
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return (request.META.get("REMOTE_ADDR") or "")[:45] or None


def axes_client_ip(request) -> str:
    """IP real só para registro no Axes — o lockout é por e-mail, não por IP."""
    return _client_ip(request) or ""


def registrar_audit(
    *,
    acao: str,
    usuario=None,
    request=None,
    ip: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog | None:
    try:
        return AuditLog.objects.create(
            usuario=usuario,
            acao=acao[:40],
            ip=ip or (_client_ip(request) if request else None),
            metadata=metadata or {},
        )
    except Exception:
        return None


@receiver(user_login_failed)
def audit_login_failed(sender, credentials, request, **kwargs):
    email = (credentials or {}).get("username") or (credentials or {}).get("email") or ""
    registrar_audit(
        acao=AuditLog.ACAO_LOGIN_FAILED,
        request=request,
        metadata={"email_prefix": str(email)[:3] + "***" if email else ""},
    )
