from __future__ import annotations

from django.core.cache import cache

from categorizacao.models import RegraCategorizacao

CACHE_TTL = 60
PREFIX = "categorizacao"


def _cache_key(prefix: str, usuario_id: int) -> str:
    return f"{PREFIX}:{prefix}:{usuario_id}"


def get_regras_usuario(usuario_id: int) -> list[RegraCategorizacao]:
    key = _cache_key("regras", usuario_id)
    cached = cache.get(key)
    if cached is not None:
        return cached
    regras = list(
        RegraCategorizacao.objects.filter(
            usuario_id=usuario_id,
            ativa=True,
        )
        .select_related("categoria")
        .order_by("-prioridade", "-confianca_base")
    )
    cache.set(key, regras, CACHE_TTL)
    return regras


def get_regras_globais() -> list[RegraCategorizacao]:
    key = f"{PREFIX}:regras:global"
    cached = cache.get(key)
    if cached is not None:
        return cached
    regras = list(
        RegraCategorizacao.objects.filter(
            usuario__isnull=True,
            ativa=True,
        )
        .select_related("categoria")
        .order_by("-prioridade", "-confianca_base")
    )
    cache.set(key, regras, CACHE_TTL)
    return regras


def invalidar_cache_usuario(usuario_id: int) -> None:
    cache.delete(_cache_key("regras", usuario_id))
    cache.delete(_cache_key("categorias", usuario_id))


def invalidar_cache_global() -> None:
    cache.delete(f"{PREFIX}:regras:global")
    from categorizacao.services.merchant import invalidar_cache_merchants

    invalidar_cache_merchants()
