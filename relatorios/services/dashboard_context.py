"""Orquestrador unificado do contexto do dashboard."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import Q

from categorias.models import Categoria
from contas.models import Conta
from transacoes.forms import TransacaoForm
from usuarios.models import Perfil
from usuarios.services.onboarding import progresso_primeiros_passos
from usuarios.utils import primeiro_nome

from relatorios.services.dashboard import (
    comparacao_mensal_e_top_despesas,
    contas_dashboard,
    query_transacoes_mes_atual,
    resumo_cartoes_dashboard,
    rotulo_periodo_atual,
    saudacao_periodo,
)
from relatorios.services.dashboard_cache import (
    get_cached_cartoes,
    get_cached_patrimonio,
)
from relatorios.services.orcamentos import (
    listar_orcamentos_dashboard,
    usuario_tem_orcamentos_cadastrados,
)
from relatorios.services.request_cache import RelatorioRequestCache


def _perfil_usuario(user) -> Perfil:
    if hasattr(user, "perfil") and user.perfil is not None:
        return user.perfil
    perfil, _ = Perfil.objects.get_or_create(usuario=user)
    return perfil


def montar_contexto_dashboard(
    user,
    cache: RelatorioRequestCache | None = None,
    *,
    categorias_preloaded=None,
) -> dict[str, Any]:
    """Monta contexto do dashboard com deduplicação intra-request."""
    cache = cache or RelatorioRequestCache(user)
    hoje = date.today()

    comparacao, top_despesas_mes = cache.get_or_set(
        "comparacao_top_despesas",
        lambda: comparacao_mensal_e_top_despesas(user, limit=5),
    )
    totais_mes = comparacao["atual"]
    resultado_mes = comparacao["resultado_atual"]

    patrimonio = get_cached_patrimonio(user.pk, lambda: contas_dashboard(user, limit=5))
    cartoes = get_cached_cartoes(user.pk, lambda: resumo_cartoes_dashboard(user))

    metas = cache.get_or_set(
        "metas_dashboard",
        lambda: [linha.as_dict() for linha in listar_orcamentos_dashboard(user, limite=3)],
    )
    tem_orcamentos_vigentes = any(m.get("planejado", 0) > 0 for m in metas)
    tem_orcamentos_cadastrados = cache.get_or_set(
        "tem_orcamentos_cadastrados",
        lambda: bool(metas) or usuario_tem_orcamentos_cadastrados(user),
    )
    top_despesas_chart = [
        {
            "nome": x["nome"],
            "total": float(x["total"]),
            "cor": x["cor"] or "#6B7280",
            "pct": float(x["percentual"]),
            "categoria_id": x["categoria_id"],
        }
        for x in top_despesas_mes
    ]

    if categorias_preloaded is not None:
        categorias_despesa = [c for c in categorias_preloaded if c.tipo == "despesa"]
        categorias_receita = [c for c in categorias_preloaded if c.tipo == "receita"]
    else:
        categorias_despesa = cache.categorias_despesa(
            lambda: Categoria.objects.filter(
                Q(usuario=user) | Q(padrao=True),
                tipo="despesa",
                ativa=True,
            ).order_by("nome")
        )
        categorias_receita = cache.categorias_receita(
            lambda: Categoria.objects.filter(
                Q(usuario=user) | Q(padrao=True),
                tipo="receita",
                ativa=True,
            ).order_by("nome")
        )

    perfil = _perfil_usuario(user)
    initial_tx, tipo_p = perfil.defaults_transacao_form()
    form = TransacaoForm(usuario=user, tipo_inicial=tipo_p, initial=initial_tx)

    return {
        "relatorio_nav": "home",
        "saudacao": saudacao_periodo(),
        "nome_usuario": primeiro_nome(user.nome),
        "rotulo_periodo": rotulo_periodo_atual(),
        "comparacao_mensal": comparacao,
        "totais_mes": totais_mes,
        "resultado_mes": resultado_mes,
        "patrimonio": patrimonio,
        "cartoes_dashboard": cartoes,
        "metas_financeiras": metas,
        "tem_orcamentos_cadastrados": tem_orcamentos_cadastrados,
        "tem_orcamentos_vigentes": tem_orcamentos_vigentes,
        "top_despesas_mes": top_despesas_mes,
        "top_despesas_chart": top_despesas_chart,
        "periodo_transacoes_qs": query_transacoes_mes_atual(),
        "icone_choices_instituicoes": [
            "nubank", "itau", "santander", "bradesco", "bb", "caixa",
            "inter", "sicredi", "sicoob", "picpay", "mercadopago",
        ],
        "categorias_despesa": categorias_despesa,
        "categorias_receita": categorias_receita,
        "form": form,
        "ocultar_valores_dashboard": perfil.ocultar_valores_dashboard,
        "primeiros_passos": progresso_primeiros_passos(user),
    }


def snapshot_dashboard_financeiro(user, cache: RelatorioRequestCache | None = None) -> dict[str, Any]:
    """Subset serializável para comparação antes/depois de otimizações."""
    ctx = montar_contexto_dashboard(user, cache)
    totais = ctx["totais_mes"]
    return {
        "totais_mes": {k: str(v) for k, v in totais.items()},
        "patrimonio_total": str(ctx["patrimonio"]["patrimonio_total"]),
        "metas_financeiras": [
            {
                "categoria_id": m["categoria_id"],
                "planejado": str(m["planejado"]),
                "realizado": str(m["realizado"]),
                "percentual": m["percentual"],
            }
            for m in ctx["metas_financeiras"]
        ],
        "resultado_mes": str(ctx["resultado_mes"]),
    }
