"""Wrappers E2E para contratos REL-CON-* e verificação UI vs backend."""

from __future__ import annotations

from decimal import Decimal

from django.http import QueryDict

from relatorios.services.agregacoes import resultado_fluxo, totais_por_tipo
from relatorios.services.agregacoes import saldos_por_conta_totais
from relatorios.tests.helpers.kpi_home import (
    kpi_home,
    kpi_home_despesas,
    kpi_home_patrimonio,
    kpi_home_receitas,
    kpi_home_resultado,
)
from relatorios.services.despesas_categoria import montar_analise_despesas_categoria
from relatorios.services.filtros import RelatorioFiltros, parse_relatorio_filtros
from relatorios.services.fluxo_caixa import resumo_minimo_periodo
from relatorios.services.por_conta import montar_analise_por_conta
from relatorios.tests.helpers.consistency import (
    assert_kpis_mes_coerentes,
    assert_totais_filtrados,
)


def filtros_from_params(user, params: dict) -> RelatorioFiltros:
    q = QueryDict(mutable=True)
    for key, val in params.items():
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            q.setlist(key, [str(v) for v in val])
        else:
            q[key] = str(val)
    return parse_relatorio_filtros(q, usuario=user)


def totais_esperados(user, params: dict | None = None) -> dict[str, Decimal]:
    params = params or {"preset": "este_mes"}
    filtros = filtros_from_params(user, params)
    return assert_totais_filtrados(user, filtros)


def verify_kpis_mes(user) -> None:
    assert_kpis_mes_coerentes(user)


def verify_patrimonio_dashboard(user) -> Decimal:
    _, total = saldos_por_conta_totais(user)
    assert kpi_home_patrimonio(user) == total
    return kpi_home_patrimonio(user)


def verify_fluxo_periodo(user, params: dict) -> dict[str, Decimal]:
    filtros = filtros_from_params(user, params)
    tot = assert_totais_filtrados(user, filtros)
    return {
        "receitas": tot["receitas"],
        "despesas": tot["despesas"],
        "resultado": resultado_fluxo(tot),
    }


def verify_categoria_total(user, params: dict) -> Decimal:
    filtros = filtros_from_params(user, params)
    analise = montar_analise_despesas_categoria(user, filtros)
    return analise["hero"].total_despesas


def verify_conta_patrimonio(user, params: dict) -> Decimal:
    filtros = filtros_from_params(user, params)
    analise = montar_analise_por_conta(user, filtros)
    return analise["hero"].patrimonio_total


def verify_conta_movimento(user, params: dict) -> Decimal:
    filtros = filtros_from_params(user, params)
    analise = montar_analise_por_conta(user, filtros)
    return analise["hero"].movimento_total


def kpi_receitas_esperado(user) -> Decimal:
    return kpi_home_receitas(user)


def kpi_despesas_esperado(user) -> Decimal:
    return kpi_home_despesas(user)


def kpi_resultado_esperado(user) -> Decimal:
    return kpi_home_resultado(user)


def kpi_home_esperado(user) -> dict:
    return kpi_home(user)


def snapshot_ecossistema_esperado(user, *, conta, categoria) -> dict:
    """Backend snapshot para comparação UI vs serviços (GLOB-E)."""
    from relatorios.tests.helpers.ecossistema import snapshot_ecossistema

    snap = snapshot_ecossistema(user, conta=conta, categoria=categoria)
    return {
        "receitas": snap.receitas,
        "despesas": snap.despesas,
        "resultado": snap.resultado,
        "fluxo_receitas": snap.fluxo_receitas,
        "fluxo_despesas": snap.fluxo_despesas,
        "cat_total": snap.cat_total,
        "conta_movimento": snap.conta_movimento,
        "orc_realizado": snap.orc_realizado,
    }
