"""Envio de CompleteRegistration para a Conversions API da Meta.

O token nunca deve ir a templates, logs ou o Git. Falhas da Meta não
interrompem o cadastro.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings
from django.urls import reverse

from usuarios.audit import _client_ip
from usuarios.utils import normalizar_email, normalizar_whatsapp, primeiro_nome

logger = logging.getLogger(__name__)

EVENTO_CADASTRO = "CompleteRegistration"
SESSION_FBCLID = "meta_fbclid"
SESSION_FBCLID_TS = "meta_fbclid_ts"
SESSION_ADVANCED_MATCHING = "meta_advanced_matching"


def _sha256(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def _letras_minusculas(valor: str) -> str:
    return "".join(ch for ch in (valor or "").strip().lower() if ch.isalpha())


def hash_email(email: str) -> str:
    normalizado = normalizar_email(email)
    return _sha256(normalizado) if normalizado else ""


def telefone_para_capi(whatsapp: str) -> str:
    digitos = normalizar_whatsapp(whatsapp)
    if not digitos:
        return ""
    if digitos.startswith("55") and len(digitos) >= 12:
        return digitos
    return f"55{digitos}"


def hash_telefone(whatsapp: str) -> str:
    tel = telefone_para_capi(whatsapp)
    return _sha256(tel) if tel else ""


def hash_primeiro_nome(nome: str) -> str:
    texto = _letras_minusculas(primeiro_nome(nome))
    return _sha256(texto) if texto else ""


def hash_sobrenome(nome: str) -> str:
    partes = (nome or "").strip().split()
    if len(partes) < 2:
        return ""
    texto = _letras_minusculas("".join(partes[1:]))
    return _sha256(texto) if texto else ""


def hash_external_id(usuario_id: int | str | None) -> str:
    if usuario_id is None or usuario_id == "":
        return ""
    return _sha256(str(usuario_id))


def hash_country() -> str:
    return _sha256("br")


def fbc_de_fbclid(fbclid: str, criado_em_ms: int) -> str:
    fbclid = (fbclid or "").strip()
    if not fbclid:
        return ""
    return f"fb.1.{int(criado_em_ms)}.{fbclid}"


def capturar_fbclid(request) -> None:
    """Guarda o primeiro fbclid da sessão (doc Meta: fbc a partir do clique)."""
    if request is None or not hasattr(request, "session") or request.method != "GET":
        return
    fbclid = (request.GET.get("fbclid") or "").strip()
    if not fbclid or len(fbclid) > 512 or " " in fbclid:
        return
    if request.session.get(SESSION_FBCLID):
        return
    request.session[SESSION_FBCLID] = fbclid
    request.session[SESSION_FBCLID_TS] = int(time.time() * 1000)


def dados_advanced_matching(
    *,
    email: str,
    nome: str,
    whatsapp: str,
    usuario_id: int | str | None = None,
) -> dict[str, str]:
    """Parâmetros do Pixel (hashes + country ISO). Sem PII em claro."""
    dados: dict[str, str] = {}
    em = hash_email(email)
    if em:
        dados["em"] = em
    ph = hash_telefone(whatsapp)
    if ph:
        dados["ph"] = ph
    fn = hash_primeiro_nome(nome)
    if fn:
        dados["fn"] = fn
    ln = hash_sobrenome(nome)
    if ln:
        dados["ln"] = ln
    ext = hash_external_id(usuario_id)
    if ext:
        dados["external_id"] = ext
    dados["country"] = "br"
    return dados


def _event_source_url(request) -> str:
    caminho = reverse("usuarios:landing")
    site = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    if site:
        return f"{site}{caminho}"
    if request is not None:
        return request.build_absolute_uri(caminho)
    return ""


def _user_agent(request) -> str:
    if request is None:
        return ""
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]


def _fbc_do_request(request) -> str:
    if request is None:
        return ""
    cookie = (request.COOKIES.get("_fbc") or "").strip()
    if cookie:
        return cookie
    session = getattr(request, "session", None)
    if not session:
        return ""
    fbclid = (session.get(SESSION_FBCLID) or "").strip()
    ts = session.get(SESSION_FBCLID_TS)
    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return ""
    return fbc_de_fbclid(fbclid, ts_int)


def montar_user_data(
    *,
    email: str,
    nome: str,
    whatsapp: str,
    request=None,
    usuario_id: int | str | None = None,
) -> dict[str, Any]:
    user_data: dict[str, Any] = {}
    em = hash_email(email)
    if em:
        user_data["em"] = [em]
    ph = hash_telefone(whatsapp)
    if ph:
        user_data["ph"] = [ph]
    fn = hash_primeiro_nome(nome)
    if fn:
        user_data["fn"] = [fn]
    ln = hash_sobrenome(nome)
    if ln:
        user_data["ln"] = [ln]
    ext = hash_external_id(usuario_id)
    if ext:
        user_data["external_id"] = [ext]
    user_data["country"] = [hash_country()]

    if request is not None:
        ip = _client_ip(request)
        if ip:
            user_data["client_ip_address"] = ip
        ua = _user_agent(request)
        if ua:
            user_data["client_user_agent"] = ua
        fbp = (request.COOKIES.get("_fbp") or "").strip()
        if fbp:
            user_data["fbp"] = fbp
        fbc = _fbc_do_request(request)
        if fbc:
            user_data["fbc"] = fbc
    return user_data


def _capi_configurada() -> bool:
    pixel = (getattr(settings, "META_PIXEL_ID", "") or "").strip()
    token = (getattr(settings, "META_CAPI_ACCESS_TOKEN", "") or "").strip()
    return bool(pixel and token)


def enviar_complete_registration(
    *,
    event_id: str,
    email: str,
    nome: str,
    whatsapp: str,
    request=None,
    usuario_id: int | str | None = None,
) -> bool:
    """POST CompleteRegistration. Retorna True se a Meta aceitou o evento."""
    if not event_id or not _capi_configurada():
        return False

    pixel = (getattr(settings, "META_PIXEL_ID", "") or "").strip()
    token = (getattr(settings, "META_CAPI_ACCESS_TOKEN", "") or "").strip()
    versao = (getattr(settings, "META_CAPI_API_VERSION", "") or "v22.0").strip()
    teste = (getattr(settings, "META_CAPI_TEST_EVENT_CODE", "") or "").strip()

    evento = {
        "event_name": EVENTO_CADASTRO,
        "event_time": int(time.time()),
        "event_id": event_id,
        "event_source_url": _event_source_url(request),
        "action_source": "website",
        "user_data": montar_user_data(
            email=email,
            nome=nome,
            whatsapp=whatsapp,
            request=request,
            usuario_id=usuario_id,
        ),
    }
    payload: dict[str, Any] = {
        "data": [evento],
        "access_token": token,
    }
    if teste:
        payload["test_event_code"] = teste

    url = f"https://graph.facebook.com/{versao}/{pixel}/events"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            ok = 200 <= getattr(resp, "status", 200) < 300
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        logger.warning("Falha ao enviar evento CAPI (%s).", EVENTO_CADASTRO)
        return False
    if not ok:
        logger.warning("CAPI recusou evento %s.", EVENTO_CADASTRO)
    return bool(ok)
