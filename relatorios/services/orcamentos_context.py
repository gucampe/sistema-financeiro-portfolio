"""Orquestrador de contexto da tela de orçamentos."""

from __future__ import annotations

from typing import Any

from relatorios.forms import OrcamentoCategoriaForm
from relatorios.models import OrcamentoCategoria
from relatorios.services.filtros import RelatorioFiltros
from relatorios.services.orcamentos import (
    MESES_PT,
    _filtros_orcamento_despesas,
    listar_orcamentos,
    painel_mes_orcamento,
    periodo_orcamento_multi_mes,
    referencia_mes_orcamento,
    resumo_linhas_orcamento,
    rotulo_periodo_orcamento,
    usuario_tem_orcamentos_cadastrados,
)
from relatorios.services.request_cache import RelatorioRequestCache


def montar_contexto_orcamentos(
    user,
    base_filtros: RelatorioFiltros,
    *,
    cache: RelatorioRequestCache | None = None,
) -> dict[str, Any]:
    """Monta contexto de orçamentos com memoização intra-request."""
    cache = cache or RelatorioRequestCache(user)
    filtros_periodo = _filtros_orcamento_despesas(base_filtros)
    ano_ref, mes_ref = referencia_mes_orcamento(base_filtros)
    cache_key = (
        f"{filtros_periodo.data_inicio}:{filtros_periodo.data_fim}:"
        f"{ano_ref}:{mes_ref}"
    )

    linhas = cache.get_or_set(
        f"listar_orcamentos:{cache_key}",
        lambda: listar_orcamentos(
            user,
            filtros_periodo,
            ano_ref=ano_ref,
            mes_ref=mes_ref,
            incluir_inativos=False,
            exibir_inativos=True,
            cache=cache,
        ),
    )
    resumo = resumo_linhas_orcamento(linhas)
    painel_mes = painel_mes_orcamento(linhas, resumo)

    orcamento_ids = [l.orcamento_id for l in linhas if l.orcamento_id]
    orcamentos_map = cache.get_or_set(
        f"orcamentos_map:{','.join(str(i) for i in sorted(orcamento_ids))}",
        lambda: {
            o.pk: o
            for o in OrcamentoCategoria.objects.filter(usuario=user, pk__in=orcamento_ids)
        },
    )
    for linha in linhas:
        linha.historico = []
        linha.orcamento_obj = orcamentos_map.get(linha.orcamento_id)

    tem_orcamentos = cache.get_or_set(
        "tem_orcamentos_cadastrados",
        lambda: usuario_tem_orcamentos_cadastrados(user),
    )

    return {
        "relatorio_nav": "orcamentos",
        "ano": ano_ref,
        "mes": mes_ref,
        "mes_rotulo": MESES_PT[mes_ref - 1],
        "periodo_orcamento_rotulo": rotulo_periodo_orcamento(base_filtros),
        "periodo_orcamento_multi_mes": periodo_orcamento_multi_mes(base_filtros),
        "linhas_orcamento": linhas,
        "resumo_orcamento": resumo,
        "painel_mes": painel_mes,
        "tem_orcamentos": tem_orcamentos,
        "drill_mes_qs": f"{filtros_periodo.to_drill_transacoes_query_string()}&tipo=despesa",
        "form_orcamento": OrcamentoCategoriaForm(
            usuario=user,
            initial={"ativo": True},
        ),
    }
