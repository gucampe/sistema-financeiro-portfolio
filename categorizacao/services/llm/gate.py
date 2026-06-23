from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings

from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

logger = logging.getLogger("categorizacao.llm")

_BYPASS_FONTES = frozenset({"regra_usuario", "historico", "fuzzy"})
_AMBIGUITY_MARKERS = ("amazon", "magalu", "mercado livre", "shopee")


@dataclass
class GateDecision:
    invoke: bool
    reason: str


def llm_admin_enabled() -> bool:
    """LLM só é acionada quando o admin habilita globalmente (env/settings)."""
    return bool(getattr(settings, "ENABLE_CATEGORIZACAO_LLM", False))


def _is_structurally_ambiguous(ctx: ContextoCategorizacao) -> bool:
    raw = (ctx.descricao or "").lower()
    desc = (ctx.descricao_normalizada or ctx.descricao or "").lower()
    mk = (ctx.merchant_key or "").lower()
    if any(m in raw for m in ("pix", "ted", "doc ", "transferencia")):
        return True
    if "pix" in desc or "pix" in mk or "ted" in desc or "doc " in desc:
        return True
    if not mk.strip() and len(desc) > 15:
        return True
    return any(marker in desc or marker in raw for marker in _AMBIGUITY_MARKERS)


def should_invoke_llm(
    ctx: ContextoCategorizacao,
    pred_hibrida: PredicaoCategorizacao | None,
) -> GateDecision:
    if not llm_admin_enabled():
        return GateDecision(False, "feature_disabled")

    from categorizacao.services.llm.circuit_breaker import is_circuit_open

    if is_circuit_open():
        return GateDecision(False, "circuit_open")

    from categorizacao.services.llm.cost_tracker import is_budget_exceeded

    if is_budget_exceeded():
        return GateDecision(False, "budget_exceeded")

    if not (ctx.descricao_normalizada or ctx.descricao or "").strip():
        return GateDecision(False, "empty_description")

    trigger_max = float(getattr(settings, "CATEGORIZACAO_LLM_TRIGGER_MAX", 0.65))

    if pred_hibrida is None:
        return GateDecision(True, "no_hybrid_prediction")

    fonte = pred_hibrida.fonte or ""
    conf = pred_hibrida.confianca

    if fonte == "regra_usuario" and conf >= 0.90:
        return GateDecision(False, "regra_usuario_high_conf")

    if fonte == "historico" and conf >= 0.80:
        return GateDecision(False, "historico_high_conf")

    if fonte == "fuzzy" and conf >= 0.88:
        return GateDecision(False, "fuzzy_high_conf")

    if fonte in _BYPASS_FONTES and conf >= 0.75:
        return GateDecision(False, f"{fonte}_sufficient")

    if _is_structurally_ambiguous(ctx) and conf < 0.75:
        return GateDecision(True, "structural_ambiguity")

    if conf < trigger_max:
        return GateDecision(True, "low_confidence")

    return GateDecision(False, "hybrid_sufficient")


def merge_predictions(
    pred_hibrida: PredicaoCategorizacao | None,
    pred_llm: PredicaoCategorizacao | None,
) -> PredicaoCategorizacao | None:
    min_llm = float(getattr(settings, "CATEGORIZACAO_LLM_MIN_CONFIDENCE", 0.55))

    if pred_llm is None:
        return pred_hibrida

    if pred_llm.confianca < min_llm:
        return pred_hibrida

    if pred_hibrida is None:
        return pred_llm

    if pred_llm.confianca > pred_hibrida.confianca:
        return pred_llm

    if pred_hibrida.confianca < float(getattr(settings, "CATEGORIZACAO_LLM_TRIGGER_MAX", 0.65)):
        return pred_llm

    return pred_hibrida
