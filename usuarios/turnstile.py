from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_obrigatorio() -> bool:
    if getattr(settings, "IS_PRODUCTION", False):
        return True
    site = (getattr(settings, "TURNSTILE_SITE_KEY", "") or "").strip()
    secret = (getattr(settings, "TURNSTILE_SECRET_KEY", "") or "").strip()
    return bool(site and secret)


def verificar_turnstile(token: str, remote_ip: str | None = None) -> bool:
    """Valida o token do widget. Bypass só com chaves vazias fora de produção."""
    site = (getattr(settings, "TURNSTILE_SITE_KEY", "") or "").strip()
    secret = (getattr(settings, "TURNSTILE_SECRET_KEY", "") or "").strip()

    if getattr(settings, "IS_PRODUCTION", False) and (not site or not secret):
        raise ImproperlyConfigured("Turnstile não configurado em produção.")

    if not site or not secret:
        return True

    token = (token or "").strip()
    if not token:
        return False

    payload = urllib.parse.urlencode(
        {
            "secret": secret,
            "response": token,
            **({"remoteip": remote_ip} if remote_ip else {}),
        }
    ).encode()
    req = urllib.request.Request(
        SITEVERIFY_URL,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        logger.exception("Falha ao verificar Turnstile.")
        return False
    return bool(data.get("success"))
