from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate

from categorizacao.models import (
    CategorizacaoUXEvent,
    EventoCategorizacao,
    LLMRequestLog,
    MemoriaMerchantUsuario,
)


def _periodo_qs(dias: int = 30):
    desde = date.today() - timedelta(days=dias)
    return desde


def coletar_metricas_dashboard(dias: int = 30) -> dict:
    desde = _periodo_qs(dias)
    eventos = EventoCategorizacao.objects.filter(criado_em__date__gte=desde)
    llm_logs = LLMRequestLog.objects.filter(criado_em__date__gte=desde)
    ux_events = CategorizacaoUXEvent.objects.filter(criado_em__date__gte=desde)

    por_fonte = list(
        eventos.filter(acao__in=("aceita", "corrigida", "auto_aplicada"))
        .exclude(fonte="")
        .values("fonte")
        .annotate(total=Count("id"), confianca_media=Avg("confianca"))
        .order_by("-total")
    )

    correcoes = eventos.filter(acao="corrigida").count()
    aceites = eventos.filter(acao="aceita").count()
    passive = eventos.filter(contexto__learning_source="imported_passive").count()

    llm_total = llm_logs.count()
    llm_sucesso = llm_logs.filter(success=True).count()
    cache_hits = llm_logs.filter(cache_hit=True).count()
    latencias = list(llm_logs.filter(success=True).values_list("latency_ms", flat=True))

    def _percentil(vals: list[float], p: float) -> float:
        if not vals:
            return 0.0
        s = sorted(vals)
        idx = int(len(s) * p)
        idx = min(idx, len(s) - 1)
        return round(s[idx], 1)

    gate_reasons = list(
        llm_logs.values("gate_reason")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    bloqueios_llm = sum(
        1 for g in gate_reasons if g["gate_reason"] in (
            "human_memory_confirmed",
            "human_memory_similar",
            "human_priority_hybrid",
            "historico_high_conf",
        )
    )

    ia_clicks = ux_events.filter(evento="ia_click").count()
    ia_complete = ux_events.filter(evento="ia_complete").count()
    ia_cancel = ux_events.filter(evento="ia_cancel").count()

    duracoes = [
        e.payload.get("duracao_ms", 0)
        for e in ux_events.filter(evento="ia_complete")
        if isinstance(e.payload, dict)
    ]
    duracao_media_ia = round(sum(duracoes) / len(duracoes), 0) if duracoes else 0

    categorias_revertidas = list(
        eventos.filter(acao="corrigida")
        .values("categoria_final__nome")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    memorias = MemoriaMerchantUsuario.objects.filter(confirmacoes__gte=1)
    merchants_fragmentados = (
        memorias.values("merchant_key")
        .annotate(cnt=Count("id"))
        .filter(cnt__gte=1)
        .order_by("-cnt")[:15]
    )

    evolucao = list(
        eventos.annotate(dia=TruncDate("criado_em"))
        .values("dia")
        .annotate(total=Count("id"))
        .order_by("dia")
    )

    por_fonte_ia = {}
    for ev in ux_events.filter(evento="ia_complete"):
        pf = (ev.payload or {}).get("por_fonte") or {}
        for k, v in pf.items():
            por_fonte_ia[k] = por_fonte_ia.get(k, 0) + int(v)

    return {
        "periodo_dias": dias,
        "por_fonte": por_fonte,
        "por_acao": list(
            eventos.values("acao").annotate(total=Count("id")).order_by("-total")
        ),
        "taxa_correcao": round(correcoes / max(aceites + correcoes, 1) * 100, 1),
        "aceite_passivo_llm": passive,
        "llm": {
            "total": llm_total,
            "sucesso": llm_sucesso,
            "cache_hit_rate": round(cache_hits / max(llm_total, 1) * 100, 1),
            "bloqueios_memoria": bloqueios_llm,
            "latencia_p50": _percentil(latencias, 0.5),
            "latencia_p95": _percentil(latencias, 0.95),
            "latencia_p99": _percentil(latencias, 0.99),
            "gate_reasons": gate_reasons,
            "custo_usd": float(
                sum(llm_logs.values_list("cost_usd_estimated", flat=True)) or 0
            ),
        },
        "ux_ia": {
            "cliques": ia_clicks,
            "conclusoes": ia_complete,
            "cancelamentos": ia_cancel,
            "duracao_media_ms": duracao_media_ia,
            "por_fonte_batch": por_fonte_ia,
        },
        "categorias_revertidas": categorias_revertidas,
        "top_merchants_memoria": list(merchants_fragmentados),
        "evolucao_diaria": evolucao,
    }
