from __future__ import annotations

import hashlib
import logging

from django.conf import settings

from categorizacao.schemas.llm_response import LLM_RESPONSE_JSON_SCHEMA
from categorizacao.services.llm.cache import get_cached, set_cached
from categorizacao.services.llm.category_resolver import (
    categorias_hash,
    listar_categorias_usuario,
    llm_response_to_predicao,
    resolve_categoria,
)
from categorizacao.services.llm.circuit_breaker import record_failure, record_success
from categorizacao.services.llm.cost_tracker import record_usage
from categorizacao.services.llm.gate import GateDecision, merge_predictions, should_invoke_llm
from categorizacao.services.llm.prompt_builder import PROMPT_VERSION, build_prompts
from categorizacao.services.llm.providers.registry import get_llm_provider, resolve_ab_model
from categorizacao.services.llm.response_parser import complete_with_retry
from categorizacao.services.pipeline import classificar
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

logger = logging.getLogger("categorizacao.llm")


def _log_request(
    usuario,
    *,
    model: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    success: bool,
    cache_hit: bool,
    gate_reason: str,
    descricao_hash: str,
    cost_usd: float,
) -> None:
    try:
        from categorizacao.models import LLMRequestLog

        LLMRequestLog.objects.create(
            usuario=usuario,
            model=model,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=success,
            cache_hit=cache_hit,
            gate_reason=gate_reason[:60],
            descricao_hash=descricao_hash[:64],
            cost_usd_estimated=cost_usd,
        )
    except Exception:
        logger.debug("LLMRequestLog persist failed", exc_info=True)


def _invoke_llm(ctx: ContextoCategorizacao, gate: GateDecision) -> PredicaoCategorizacao | None:
    model = resolve_ab_model(ctx.usuario.pk)
    provider = get_llm_provider(model)
    categorias = listar_categorias_usuario(ctx.usuario, ctx.tipo)
    if not categorias:
        return None

    cats_hash = categorias_hash(categorias)
    cached = get_cached(
        user_id=ctx.usuario.pk,
        model=model,
        prompt_version=PROMPT_VERSION,
        descricao_normalizada=ctx.descricao_normalizada,
        tipo=ctx.tipo,
        cats_hash=cats_hash,
    )
    desc_hash = hashlib.sha256(ctx.descricao_normalizada.encode()).hexdigest()[:16]

    if cached:
        cat = resolve_categoria(ctx.usuario, cached, ctx.tipo)
        if cat:
            _log_request(
                ctx.usuario,
                model=model,
                latency_ms=0,
                input_tokens=0,
                output_tokens=0,
                success=True,
                cache_hit=True,
                gate_reason=gate.reason,
                descricao_hash=desc_hash,
                cost_usd=0,
            )
            return llm_response_to_predicao(
                cached,
                cat,
                ctx.merchant_key,
                llm_contexto={
                    "llm_model": model,
                    "cache_hit": True,
                    "latency_ms": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "gate_reason": gate.reason,
                },
            )

    system, user = build_prompts(
        descricao_normalizada=ctx.descricao_normalizada,
        merchant_key=ctx.merchant_key,
        tipo=ctx.tipo,
        valor=ctx.valor,
        categorias=categorias,
    )
    timeout_s = float(getattr(settings, "CATEGORIZACAO_LLM_TIMEOUT_S", 8))
    max_retries = int(getattr(settings, "CATEGORIZACAO_LLM_MAX_RETRIES", 1))

    parsed, raw = complete_with_retry(
        provider,
        system=system,
        user=user,
        schema=LLM_RESPONSE_JSON_SCHEMA,
        timeout_s=timeout_s,
        max_retries=max_retries,
    )

    cost = record_usage(raw.model, raw.input_tokens, raw.output_tokens)

    if parsed is None:
        record_failure()
        _log_request(
            ctx.usuario,
            model=raw.model,
            latency_ms=raw.latency_ms,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            success=False,
            cache_hit=False,
            gate_reason=gate.reason,
            descricao_hash=desc_hash,
            cost_usd=cost,
        )
        return None

    record_success()
    set_cached(
        user_id=ctx.usuario.pk,
        model=model,
        prompt_version=PROMPT_VERSION,
        descricao_normalizada=ctx.descricao_normalizada,
        tipo=ctx.tipo,
        cats_hash=cats_hash,
        response=parsed,
    )
    cat = resolve_categoria(ctx.usuario, parsed, ctx.tipo)
    if not cat:
        _log_request(
            ctx.usuario,
            model=raw.model,
            latency_ms=raw.latency_ms,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            success=False,
            cache_hit=False,
            gate_reason="slug_invalid",
            descricao_hash=desc_hash,
            cost_usd=cost,
        )
        return None

    _log_request(
        ctx.usuario,
        model=raw.model,
        latency_ms=raw.latency_ms,
        input_tokens=raw.input_tokens,
        output_tokens=raw.output_tokens,
        success=True,
        cache_hit=False,
        gate_reason=gate.reason,
        descricao_hash=desc_hash,
        cost_usd=cost,
    )
    return llm_response_to_predicao(
        parsed,
        cat,
        ctx.merchant_key,
        llm_contexto={
            "llm_model": raw.model,
            "cache_hit": False,
            "latency_ms": raw.latency_ms,
            "tokens_in": raw.input_tokens,
            "tokens_out": raw.output_tokens,
            "gate_reason": gate.reason,
        },
    )


def classificar_com_llm(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    """Pipeline híbrido + fallback LLM condicional."""
    pred_hibrida = classificar(ctx)
    gate = should_invoke_llm(ctx, pred_hibrida)
    if not gate.invoke:
        return pred_hibrida
    pred_llm = _invoke_llm(ctx, gate)
    return merge_predictions(pred_hibrida, pred_llm)
