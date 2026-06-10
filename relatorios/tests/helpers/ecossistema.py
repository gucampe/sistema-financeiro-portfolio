"""Snapshot e asserts GLOB-CON — consistência cross-app do ecossistema financeiro."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.http import QueryDict

from financial_contracts.base import quantize_moeda
from financial_contracts.saldo_contracts import calcular_saldo_esperado
from relatorios.services.despesas_categoria import montar_analise_despesas_categoria
from relatorios.services.filtros import parse_relatorio_filtros
from relatorios.services.orcamentos import listar_orcamentos_mes
from relatorios.services.por_conta import montar_analise_por_conta
from relatorios.tests.helpers.consistency import assert_totais_filtrados
from relatorios.tests.helpers.kpi_home import kpi_home


class EcossistemaConsistencyError(AssertionError):
    pass


@dataclass(frozen=True)
class SnapshotEcossistema:
    saldo_conta: Decimal
    receitas: Decimal
    despesas: Decimal
    resultado: Decimal
    patrimonio: Decimal
    fluxo_receitas: Decimal
    fluxo_despesas: Decimal
    cat_total: Decimal
    cat_linha: Decimal
    conta_movimento: Decimal
    orc_realizado: Decimal
    cat_linha_b: Decimal | None = None
    orc_realizado_b: Decimal | None = None


def _eq(atual: Decimal, esperado: Decimal, contrato: str, ctx: str = "") -> None:
    a = quantize_moeda(atual)
    e = quantize_moeda(esperado)
    if a != e:
        msg = f"{contrato} violado: {a} != {e}"
        if ctx:
            msg = f"{msg} ({ctx})"
        raise EcossistemaConsistencyError(msg)


def _total_categoria(analise: dict, categoria_id: int) -> Decimal:
    for row in analise.get("categorias") or []:
        if row.get("categoria_id") == categoria_id:
            return row.get("total") or Decimal("0")
    return Decimal("0")


def _orc_realizado(linhas, categoria_id: int) -> Decimal:
    for linha in linhas:
        if linha.categoria_id == categoria_id:
            return linha.realizado or Decimal("0")
    return Decimal("0")


def _filtros_este_mes(user):
    return parse_relatorio_filtros(QueryDict("preset=este_mes"), usuario=user)


def snapshot_ecossistema(
    user,
    *,
    conta,
    categoria,
    categoria_b=None,
    ano: int | None = None,
    mes: int | None = None,
) -> SnapshotEcossistema:
    from django.utils import timezone

    hoje = timezone.localdate()
    ano = ano or hoje.year
    mes = mes or hoje.month
    filtros = _filtros_este_mes(user)
    kpi = kpi_home(user)
    fluxo = assert_totais_filtrados(user, filtros)
    analise_cat = montar_analise_despesas_categoria(user, filtros)
    analise_conta = montar_analise_por_conta(user, filtros)
    linhas_orc = listar_orcamentos_mes(user, ano, mes)
    cid_b = categoria_b.id if categoria_b else None

    return SnapshotEcossistema(
        saldo_conta=calcular_saldo_esperado(conta),
        receitas=kpi["receitas"],
        despesas=kpi["despesas"],
        resultado=kpi["resultado"],
        patrimonio=kpi["patrimonio"],
        fluxo_receitas=fluxo["receitas"],
        fluxo_despesas=fluxo["despesas"],
        cat_total=analise_cat["total_despesas"],
        cat_linha=_total_categoria(analise_cat, categoria.id),
        conta_movimento=analise_conta["hero"].movimento_total,
        orc_realizado=_orc_realizado(linhas_orc, categoria.id),
        cat_linha_b=_total_categoria(analise_cat, cid_b) if cid_b else None,
        orc_realizado_b=_orc_realizado(linhas_orc, cid_b) if cid_b else None,
    )


def assert_ecossistema_coerente(snap: SnapshotEcossistema, *, contrato: str = "GLOB-CON") -> None:
    """GLOB-CON-01..06 — cruzamentos internos do ecossistema."""
    _eq(snap.resultado, snap.receitas - snap.despesas, f"{contrato}-01", "kpi.resultado")
    _eq(snap.fluxo_receitas, snap.receitas, f"{contrato}-02", "fluxo.receitas vs kpi")
    _eq(snap.fluxo_despesas, snap.despesas, f"{contrato}-02", "fluxo.despesas vs kpi")
    _eq(snap.cat_total, snap.fluxo_despesas, f"{contrato}-03", "cat_total vs fluxo.despesas")
    if snap.cat_linha > snap.cat_total:
        raise EcossistemaConsistencyError(
            f"{contrato}-04: cat_linha {snap.cat_linha} > cat_total {snap.cat_total}"
        )
    _eq(snap.orc_realizado, snap.cat_linha, f"{contrato}-05", "orc vs cat_linha (categoria alvo)")


def assert_delta_ecossistema(
    antes: SnapshotEcossistema,
    depois: SnapshotEcossistema,
    *,
    delta_receitas: Decimal = Decimal("0"),
    delta_despesas: Decimal = Decimal("0"),
    delta_orc: Decimal = Decimal("0"),
    delta_saldo: Decimal = Decimal("0"),
    delta_cat_linha: Decimal | None = None,
    delta_orc_b: Decimal = Decimal("0"),
    delta_cat_linha_b: Decimal | None = None,
    contrato: str = "GLOB-DELTA",
) -> None:
    """Compara snapshots antes/depois com deltas esperados."""
    _eq(depois.receitas - antes.receitas, delta_receitas, contrato, "delta receitas")
    _eq(depois.despesas - antes.despesas, delta_despesas, contrato, "delta despesas")
    _eq(depois.saldo_conta - antes.saldo_conta, delta_saldo, contrato, "delta saldo")
    _eq(depois.orc_realizado - antes.orc_realizado, delta_orc, contrato, "delta orc_realizado")
    if delta_cat_linha is not None:
        _eq(depois.cat_linha - antes.cat_linha, delta_cat_linha, contrato, "delta cat_linha")

    _eq(
        depois.fluxo_receitas - antes.fluxo_receitas,
        delta_receitas,
        contrato,
        "delta fluxo receitas",
    )
    _eq(
        depois.fluxo_despesas - antes.fluxo_despesas,
        delta_despesas,
        contrato,
        "delta fluxo despesas",
    )
    _eq(depois.cat_total - antes.cat_total, delta_despesas, contrato, "delta cat_total")
    _eq(
        depois.conta_movimento - antes.conta_movimento,
        delta_receitas - delta_despesas,
        contrato,
        "delta conta_movimento",
    )

    if delta_cat_linha_b is not None and antes.cat_linha_b is not None and depois.cat_linha_b is not None:
        _eq(depois.cat_linha_b - antes.cat_linha_b, delta_cat_linha_b, contrato, "delta cat_linha_b")
    if delta_orc_b != 0 and antes.orc_realizado_b is not None and depois.orc_realizado_b is not None:
        _eq(depois.orc_realizado_b - antes.orc_realizado_b, delta_orc_b, contrato, "delta orc_b")

    assert_ecossistema_coerente(depois)
