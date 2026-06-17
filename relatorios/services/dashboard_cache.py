"""Cache cross-request de agregações do dashboard (Redis/LocMem, TTL curto)."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

DASHBOARD_CACHE_TTL = 30


def _cache_enabled() -> bool:
    return getattr(settings, "ENABLE_DASHBOARD_AGG_CACHE", False)


def _user_key(prefix: str, user_id: int) -> str:
    return f"dash:{prefix}:{user_id}"


def _mes_key(prefix: str, user_id: int, ano: int, mes: int) -> str:
    return f"dash:{prefix}:{user_id}:{ano:04d}-{mes:02d}"


def invalidate_dashboard_user(user_id: int) -> None:
    if not _cache_enabled():
        return
    hoje = timezone.localdate()
    keys = [
        _user_key("patrimonio", user_id),
        _user_key("cartoes", user_id),
        _mes_key("comp_mes", user_id, hoje.year, hoje.month),
    ]
    cache.delete_many(keys)


def get_cached_patrimonio(user_id: int, factory) -> dict[str, Any]:
    if not _cache_enabled():
        return factory()
    key = _user_key("patrimonio", user_id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = factory()
    cache.set(key, value, DASHBOARD_CACHE_TTL)
    return value


def get_cached_cartoes(user_id: int, factory) -> dict[str, Any]:
    if not _cache_enabled():
        return factory()
    key = _user_key("cartoes", user_id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = factory()
    cache.set(key, value, DASHBOARD_CACHE_TTL)
    return value


def get_cached_comparacao_mes(user_id: int, ano: int, mes: int, factory) -> dict[str, Any]:
    if not _cache_enabled():
        return factory()
    key = _mes_key("comp_mes", user_id, ano, mes)
    cached = cache.get(key)
    if cached is not None:
        return cached
    value = factory()
    cache.set(key, value, DASHBOARD_CACHE_TTL)
    return value


def filtros_cache_key(filtros) -> str:
    raw = f"{filtros.data_inicio}|{filtros.data_fim}|{filtros.modo_data}|{filtros.conta_ids}|{filtros.categoria_ids}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]
