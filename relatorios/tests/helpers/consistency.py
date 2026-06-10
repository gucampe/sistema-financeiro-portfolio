"""Asserts reutilizáveis REL-CON-* para consistência de relatórios."""

from __future__ import annotations

from decimal import Decimal

from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import (
    aplicar_filtros_relatorio,
    resultado_fluxo,
    saldos_por_conta_totais,
    totais_por_tipo,
)
from relatorios.services.dashboard import comparacao_mensal, contas_dashboard
from relatorios.services.filtros import RelatorioFiltros


class RelatorioConsistencyError(AssertionError):
    pass


def _eq(atual: Decimal, esperado: Decimal, contrato: str, ctx: str = "") -> None:
    a = Decimal(atual).quantize(Decimal("0.01"))
    e = Decimal(esperado).quantize(Decimal("0.01"))
    if a != e:
        msg = f"{contrato} violado: {a} != {e}"
        if ctx:
            msg = f"{msg} ({ctx})"
        raise RelatorioConsistencyError(msg)


def assert_kpis_mes_coerentes(user, contrato: str = "REL-CON-01") -> None:
    comp = comparacao_mensal(user)
    tot = comp["atual"]
    res = comp["resultado_atual"]
    esperado = resultado_fluxo(tot)
    _eq(res, esperado, contrato, "resultado_mes")


def assert_patrimonio_coerente(user, contrato: str = "REL-CON-02") -> None:
    dash = contas_dashboard(user)
    _, total_servico = saldos_por_conta_totais(user)
    _eq(dash["patrimonio_total"], total_servico, contrato, "patrimonio_total")


def assert_totais_filtrados(
    user,
    filtros: RelatorioFiltros,
    *,
    contrato: str = "REL-CON-03",
) -> dict[str, Decimal]:
    qs = aplicar_filtros_relatorio(transacoes_base_qs(user), filtros)
    return totais_por_tipo(qs)


def assert_resultado_receitas_menos_despesas(
    totais: dict[str, Decimal],
    contrato: str = "REL-CON-04",
) -> None:
    esperado = totais["receitas"] - totais["despesas"]
    _eq(resultado_fluxo(totais), esperado, contrato)
