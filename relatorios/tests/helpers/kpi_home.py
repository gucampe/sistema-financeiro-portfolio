"""Fonte de verdade KPI_HOME — comparacao_mensal sem filtros de URL."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from relatorios.services.dashboard import comparacao_mensal, contas_dashboard


def kpi_home(user) -> dict[str, Any]:
    """
    KPI_HOME = comparacao_mensal(user) no mês calendário atual,
    sem filtros de URL. Patrimônio vem de contas_dashboard().
    """
    comp = comparacao_mensal(user)
    pat = contas_dashboard(user)
    return {
        "receitas": comp["atual"]["receitas"],
        "despesas": comp["atual"]["despesas"],
        "resultado": comp["resultado_atual"],
        "comparacao": comp,
        "patrimonio": pat["patrimonio_total"],
        "contas": pat["contas"],
    }


def kpi_home_receitas(user) -> Decimal:
    return kpi_home(user)["receitas"]


def kpi_home_despesas(user) -> Decimal:
    return kpi_home(user)["despesas"]


def kpi_home_resultado(user) -> Decimal:
    return kpi_home(user)["resultado"]


def kpi_home_patrimonio(user) -> Decimal:
    return kpi_home(user)["patrimonio"]
