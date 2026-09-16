"""Eventos de produto — funil de ativação e Ajuda. Sem PII nem valores financeiros."""

from __future__ import annotations

import logging
from typing import Any

from django.db import IntegrityError

from usuarios.models import ProdutoEvento, Usuario

logger = logging.getLogger(__name__)

EVENTOS_FIRST = frozenset(
    {
        "onboarding_started",
        "first_account_created",
        "first_transaction_created",
        "first_import_started",
        "first_import_failed",
        "first_import_completed",
        "first_dashboard_view_with_data",
        "first_card_created",
    }
)

EVENTOS_RECORRENTES = frozenset(
    {
        "help_opened",
        "help_search_used",
        "help_article_opened",
        "context_tip_shown",
        "context_tip_opened",
        "context_tip_dismissed",
        "pwa_install_prompt_shown",
        "pwa_install_clicked",
        "pwa_install_dismissed",
        "pwa_installed",
        "pwa_opened_standalone",
    }
)

EVENTOS_PERMITIDOS = EVENTOS_FIRST | EVENTOS_RECORRENTES

_PAYLOAD_KEYS = frozenset({"q", "article_id", "dica_id", "versao", "origem"})
_PAYLOAD_MAX = 80


def sanitizar_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    limpo: dict[str, Any] = {}
    for chave, valor in payload.items():
        if chave not in _PAYLOAD_KEYS:
            continue
        if chave == "versao":
            try:
                limpo["versao"] = int(valor)
            except (TypeError, ValueError):
                continue
            continue
        texto = str(valor).strip()[:_PAYLOAD_MAX]
        if texto:
            limpo[chave] = texto
    return limpo


def registrar_evento(
    usuario: Usuario,
    evento: str,
    payload: dict[str, Any] | None = None,
) -> ProdutoEvento | None:
    if evento not in EVENTOS_PERMITIDOS:
        return None
    meta = sanitizar_payload(payload)
    if evento in EVENTOS_FIRST:
        obj, _created = ProdutoEvento.objects.get_or_create(
            usuario=usuario,
            evento=evento,
            defaults={"payload": meta},
        )
        return obj
    return ProdutoEvento.objects.create(usuario=usuario, evento=evento, payload=meta)


def registrar_evento_seguro(
    usuario: Usuario,
    evento: str,
    payload: dict[str, Any] | None = None,
) -> None:
    try:
        registrar_evento(usuario, evento, payload)
    except IntegrityError:
        pass
    except Exception:
        logger.exception("produto_evento falhou evento=%s user_id=%s", evento, getattr(usuario, "pk", None))
