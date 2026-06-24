from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings

from categorizacao.services.memory_lookup import (
    buscar_memoria_humana,
    memoria_humana_confirmada,
    tem_memoria_humana_bloqueante,
)
from categorizacao.services.observability import (
    log_gate_decision,
    log_llm_blocked_by_human_memory,
    log_llm_blocked_by_memory,
    log_merge_llm_lost,
    log_merge_llm_won,
    log_merge_prevented_by_human_priority,
)
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

logger = logging.getLogger("categorizacao.llm")

_BYPASS_FONTES = frozenset({"regra_usuario", "historico", "fuzzy"})
_HUMAN_PRIORITY_FONTES = frozenset({"historico", "regra_usuario"})
_AMBIGUITY_MARKERS = ("amazon", "magalu", "mercado livre", "shopee")


@dataclass
class GateDecision:
    invoke: bool
    reason: str


def llm_admin_enabled() -> bool:
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


def _predicao_hibrida_humana_confirmada(pred: PredicaoCategorizacao | None) -> bool:
    if pred is None:
        return False
    if pred.fonte not in _HUMAN_PRIORITY_FONTES:
        return False
    if pred.fonte == "historico" and pred.confianca >= 0.75:
        return True
    if pred.fonte == "regra_usuario" and pred.confianca >= 0.85:
        return True
    return pred.contexto.get("human_memory") and pred.confianca >= 0.75


def should_invoke_llm(
    ctx: ContextoCategorizacao,
    pred_hibrida: PredicaoCategorizacao | None,
) -> GateDecision:
    user_id = getattr(ctx.usuario, "pk", None)

    if not llm_admin_enabled():
        decision = GateDecision(False, "feature_disabled")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    from categorizacao.services.llm.circuit_breaker import is_circuit_open

    if is_circuit_open():
        decision = GateDecision(False, "circuit_open")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    from categorizacao.services.llm.cost_tracker import is_budget_exceeded

    if is_budget_exceeded():
        decision = GateDecision(False, "budget_exceeded")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    if not (ctx.descricao_normalizada or ctx.descricao or "").strip():
        decision = GateDecision(False, "empty_description")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    # Prioridade absoluta: memória humana confirmada (exata ou similar PIX PF)
    memoria, match_tipo = buscar_memoria_humana(ctx)
    if memoria is not None and memoria_humana_confirmada(memoria):
        log_llm_blocked_by_human_memory(user_id, memoria.merchant_key, match_tipo)
        decision = GateDecision(False, "human_memory_confirmed")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    if tem_memoria_humana_bloqueante(ctx):
        log_llm_blocked_by_memory(user_id, "similar_memory", ctx.merchant_key)
        decision = GateDecision(False, "human_memory_similar")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    trigger_max = float(getattr(settings, "CATEGORIZACAO_LLM_TRIGGER_MAX", 0.65))

    if pred_hibrida is None:
        decision = GateDecision(True, "no_hybrid_prediction")
        log_gate_decision(user_id, True, decision.reason)
        return decision

    fonte = pred_hibrida.fonte or ""
    conf = pred_hibrida.confianca

    if _predicao_hibrida_humana_confirmada(pred_hibrida):
        log_llm_blocked_by_human_memory(user_id, pred_hibrida.merchant_key or "", fonte)
        decision = GateDecision(False, "human_priority_hybrid")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    if fonte == "regra_usuario" and conf >= 0.90:
        decision = GateDecision(False, "regra_usuario_high_conf")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    if fonte == "historico" and conf >= 0.80:
        decision = GateDecision(False, "historico_high_conf")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    if fonte == "fuzzy" and conf >= 0.88:
        decision = GateDecision(False, "fuzzy_high_conf")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    if fonte in _BYPASS_FONTES and conf >= 0.75:
        decision = GateDecision(False, f"{fonte}_sufficient")
        log_gate_decision(user_id, False, decision.reason)
        return decision

    if _is_structurally_ambiguous(ctx) and conf < 0.75:
        decision = GateDecision(True, "structural_ambiguity")
        log_gate_decision(user_id, True, decision.reason)
        return decision

    if conf < trigger_max:
        decision = GateDecision(True, "low_confidence")
        log_gate_decision(user_id, True, decision.reason)
        return decision

    decision = GateDecision(False, "hybrid_sufficient")
    log_gate_decision(user_id, False, decision.reason)
    return decision


def merge_predictions(
    pred_hibrida: PredicaoCategorizacao | None,
    pred_llm: PredicaoCategorizacao | None,
    *,
    ctx: ContextoCategorizacao | None = None,
) -> PredicaoCategorizacao | None:
    min_llm = float(getattr(settings, "CATEGORIZACAO_LLM_MIN_CONFIDENCE", 0.55))
    user_id = getattr(ctx.usuario, "pk", None) if ctx else None

    if pred_llm is None:
        return pred_hibrida

    if pred_llm.confianca < min_llm:
        log_merge_llm_lost(pred_hibrida.fonte if pred_hibrida else "none", pred_hibrida.confianca if pred_hibrida else 0, pred_llm.confianca)
        return pred_hibrida

    # Prioridade humana: histórico/regra nunca perde para LLM
    if _predicao_hibrida_humana_confirmada(pred_hibrida):
        log_merge_prevented_by_human_priority(
            user_id,
            pred_hibrida.fonte,
            pred_hibrida.confianca,
        )
        return pred_hibrida

    if ctx and tem_memoria_humana_bloqueante(ctx):
        log_merge_prevented_by_human_priority(
            user_id,
            pred_hibrida.fonte if pred_hibrida else "memory",
            pred_hibrida.confianca if pred_hibrida else 0,
        )
        return pred_hibrida

    if pred_hibrida is None:
        ctx_extra = {"requires_user_confirmation": True, "is_pix_pf": bool(ctx and ctx.is_pix_pf)}
        return PredicaoCategorizacao(
            categoria_id=pred_llm.categoria_id,
            categoria_nome=pred_llm.categoria_nome,
            confianca=pred_llm.confianca,
            fonte=pred_llm.fonte,
            merchant_key=pred_llm.merchant_key,
            explicacao=pred_llm.explicacao,
            contexto={**pred_llm.contexto, **ctx_extra},
        )

    if pred_llm.confianca > pred_hibrida.confianca:
        log_merge_llm_won(pred_hibrida.fonte, pred_hibrida.confianca, pred_llm.confianca)
        ctx_extra = {"requires_user_confirmation": True, "is_pix_pf": bool(ctx and ctx.is_pix_pf)}
        return PredicaoCategorizacao(
            categoria_id=pred_llm.categoria_id,
            categoria_nome=pred_llm.categoria_nome,
            confianca=pred_llm.confianca,
            fonte=pred_llm.fonte,
            merchant_key=pred_llm.merchant_key,
            explicacao=pred_llm.explicacao,
            contexto={**pred_llm.contexto, **ctx_extra},
        )

    if pred_hibrida.confianca < float(getattr(settings, "CATEGORIZACAO_LLM_TRIGGER_MAX", 0.65)):
        log_merge_llm_won(pred_hibrida.fonte, pred_hibrida.confianca, pred_llm.confianca)
        ctx_extra = {"requires_user_confirmation": True, "is_pix_pf": bool(ctx and ctx.is_pix_pf)}
        return PredicaoCategorizacao(
            categoria_id=pred_llm.categoria_id,
            categoria_nome=pred_llm.categoria_nome,
            confianca=pred_llm.confianca,
            fonte=pred_llm.fonte,
            merchant_key=pred_llm.merchant_key,
            explicacao=pred_llm.explicacao,
            contexto={**pred_llm.contexto, **ctx_extra},
        )

    log_merge_llm_lost(pred_hibrida.fonte, pred_hibrida.confianca, pred_llm.confianca)
    return pred_hibrida
