from __future__ import annotations

import hashlib
import json
import logging
from datetime import date

from django.conf import settings
from django.core.cache import cache

from categorizacao.schemas.llm_response import LLMClassificationResponse

logger = logging.getLogger("categorizacao.llm")

_L1: dict[str, LLMClassificationResponse] = {}
_L1_MAX = 256


def _cache_key(
    *,
    user_id: int,
    model: str,
    prompt_version: str,
    descricao_normalizada: str,
    tipo: str,
    cats_hash: str,
) -> str:
    raw = f"{user_id}|{model}|{prompt_version}|{descricao_normalizada}|{tipo}|{cats_hash}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"categorizacao:llm:{digest}"


def get_cached(
    *,
    user_id: int,
    model: str,
    prompt_version: str,
    descricao_normalizada: str,
    tipo: str,
    cats_hash: str,
) -> LLMClassificationResponse | None:
    key = _cache_key(
        user_id=user_id,
        model=model,
        prompt_version=prompt_version,
        descricao_normalizada=descricao_normalizada,
        tipo=tipo,
        cats_hash=cats_hash,
    )
    if key in _L1:
        return _L1[key]
    try:
        data = cache.get(key)
        if data:
            if isinstance(data, str):
                data = json.loads(data)
            return LLMClassificationResponse.from_dict(data)
    except Exception:
        logger.debug("LLM cache read failed", exc_info=True)
    return None


def set_cached(
    *,
    user_id: int,
    model: str,
    prompt_version: str,
    descricao_normalizada: str,
    tipo: str,
    cats_hash: str,
    response: LLMClassificationResponse,
) -> None:
    key = _cache_key(
        user_id=user_id,
        model=model,
        prompt_version=prompt_version,
        descricao_normalizada=descricao_normalizada,
        tipo=tipo,
        cats_hash=cats_hash,
    )
    if len(_L1) >= _L1_MAX:
        _L1.clear()
    _L1[key] = response
    ttl_h = int(getattr(settings, "CATEGORIZACAO_LLM_CACHE_TTL_H", 168))
    try:
        cache.set(key, json.dumps(response.__dict__), timeout=ttl_h * 3600)
    except Exception:
        logger.debug("LLM cache write failed", exc_info=True)
