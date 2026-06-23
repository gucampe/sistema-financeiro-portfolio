from __future__ import annotations

import json
import time
from functools import lru_cache
from pathlib import Path

from django.db.models import Q

from categorias.models import Categoria
from categorizacao.models import MerchantGlobal
from categorizacao.services.normalizer import normalizar_texto

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MERCHANTS_CACHE: list[dict] | None = None
_MERCHANTS_CACHE_AT: float = 0.0
_CACHE_TTL = 300.0


def _load_merchants_json() -> list[dict]:
    path = _DATA_DIR / "merchants_br.json"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_merchants_ativos() -> list[MerchantGlobal]:
    global _MERCHANTS_CACHE, _MERCHANTS_CACHE_AT
    now = time.monotonic()
    if _MERCHANTS_CACHE is not None and (now - _MERCHANTS_CACHE_AT) < _CACHE_TTL:
        return _build_merchant_objects_from_db_or_cache()

    qs = list(MerchantGlobal.objects.filter(ativo=True).order_by("-prioridade"))
    if qs:
        _MERCHANTS_CACHE = None
        _MERCHANTS_CACHE_AT = now
        return qs

    # Fallback para JSON se DB vazio
    _MERCHANTS_CACHE = _load_merchants_json()
    _MERCHANTS_CACHE_AT = now
    return _build_merchant_objects_from_db_or_cache()


def _build_merchant_objects_from_db_or_cache() -> list:
    qs = MerchantGlobal.objects.filter(ativo=True).order_by("-prioridade")
    if qs.exists():
        return list(qs)
    if not _MERCHANTS_CACHE:
        return []
    result = []
    for item in _MERCHANTS_CACHE:
        m = MerchantGlobal(
            canonical_name=item["canonical_name"],
            aliases=item.get("aliases", []),
            categoria_padrao_nome=item["categoria_padrao_nome"],
            tipo=item.get("tipo", "despesa"),
            prioridade=item.get("prioridade", 0),
            ativo=True,
        )
        m.pk = hash(item["canonical_name"]) & 0x7FFFFFFF
        result.append(m)
    return result


def resolver_categoria_padrao(
    usuario,
    categoria_padrao_nome: str,
    tipo: str,
) -> Categoria | None:
    cat = Categoria.objects.filter(
        Q(usuario=usuario) | Q(padrao=True),
        nome__iexact=categoria_padrao_nome,
        tipo=tipo,
        ativa=True,
    ).first()
    if cat:
        return cat
    return Categoria.objects.filter(
        Q(usuario=usuario) | Q(padrao=True),
        nome__iexact=categoria_padrao_nome,
        ativa=True,
    ).first()


def merchant_aliases_flat(merchant: MerchantGlobal) -> list[str]:
    aliases = [merchant.canonical_name]
    for a in merchant.aliases or []:
        norm = normalizar_texto(str(a)).lower()
        if norm and norm not in aliases:
            aliases.append(norm)
    return aliases


def invalidar_cache_merchants() -> None:
    global _MERCHANTS_CACHE, _MERCHANTS_CACHE_AT
    _MERCHANTS_CACHE = None
    _MERCHANTS_CACHE_AT = 0.0
