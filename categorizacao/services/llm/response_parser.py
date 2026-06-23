from __future__ import annotations

import json
import logging

from categorizacao.schemas.llm_response import LLMClassificationResponse, LLMRawResult
from categorizacao.services.llm.providers.base import LLMProvider

logger = logging.getLogger("categorizacao.llm")


def parse_llm_response(raw: LLMRawResult) -> LLMClassificationResponse | None:
    if not raw.ok:
        return None
    try:
        data = json.loads(raw.text)
        resp = LLMClassificationResponse.from_dict(data)
        if resp.ambigua and resp.confianca > 0.75:
            resp = LLMClassificationResponse(
                categoria_slug=resp.categoria_slug,
                confianca=min(resp.confianca, 0.75),
                motivo=resp.motivo,
                merchant_detectado=resp.merchant_detectado,
                tipo_merchant=resp.tipo_merchant,
                ambigua=True,
                categorias_alternativas=resp.categorias_alternativas,
            )
        return resp
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("LLM JSON inválido: %s", exc)
        return None


def complete_with_retry(
    provider: LLMProvider,
    *,
    system: str,
    user: str,
    schema: dict,
    timeout_s: float,
    max_retries: int = 1,
) -> tuple[LLMClassificationResponse | None, LLMRawResult]:
    last_raw: LLMRawResult | None = None
    user_prompt = user
    for attempt in range(max_retries + 1):
        last_raw = provider.complete_json(
            system=system,
            user=user_prompt,
            schema=schema,
            timeout_s=timeout_s,
        )
        parsed = parse_llm_response(last_raw)
        if parsed is not None:
            return parsed, last_raw
        if attempt < max_retries:
            user_prompt = (
                user
                + "\n\nERRO: resposta anterior inválida. Corrija para o schema JSON exato."
            )
    return None, last_raw  # type: ignore[return-value]
