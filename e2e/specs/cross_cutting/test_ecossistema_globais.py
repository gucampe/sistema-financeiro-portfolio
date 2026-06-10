"""GLOB-E-01..04 — Jornada cross-app via UI vs backend snapshot."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import Page

from e2e.fixtures.pages.orcamentos_page import OrcamentosPage
from e2e.fixtures.pages.relatorios_page import (
    DespesasCategoriaPage,
    FluxoCaixaPage,
    RelatoriosHomePage,
)
from e2e.fixtures.pages.transacoes_page import HistoricoPage, TransacaoModalPage
from e2e.helpers.relatorio_contracts import snapshot_ecossistema_esperado
from transacoes.models import Transacao


def _hoje() -> date:
    return timezone.localdate()


def _assert_ui_ecossistema(page: Page, app_base_url: str, data: dict) -> None:
    user = data["user"]
    conta = data["conta"]
    cat = data["cat_despesa"]
    esperado = snapshot_ecossistema_esperado(user, conta=conta, categoria=cat)

    home = RelatoriosHomePage(page, app_base_url)
    home.open()
    kpis = home.kpis_hero()
    assert kpis["receitas"] == esperado["receitas"]
    assert kpis["despesas"] == esperado["despesas"]
    assert kpis["resultado"] == esperado["resultado"]

    fluxo = FluxoCaixaPage(page, app_base_url)
    fluxo.open()
    assert fluxo.totais_receitas() == esperado["fluxo_receitas"]
    assert fluxo.totais_despesas() == esperado["fluxo_despesas"]

    cat_page = DespesasCategoriaPage(page, app_base_url)
    cat_page.open()
    assert cat_page.total_despesas() == esperado["cat_total"]

    orc = OrcamentosPage(page, app_base_url)
    orc.open()
    assert orc.realizado_categoria_id(cat.id) == esperado["orc_realizado"]


@pytest.mark.ecossistema
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_glob_e_01_jornada_criar_despesa(logged_in_ecossistema_page, app_base_url):
    page, data = logged_in_ecossistema_page
    valor = Decimal("80.00")
    hoje = _hoje()

    home = RelatoriosHomePage(page, app_base_url)
    home.open()
    home.abrir_nova_despesa()
    TransacaoModalPage(page, app_base_url).criar_transacao(
        tipo="despesa",
        conta_id=data["conta"].id,
        cartao_id=None,
        categoria_id=data["cat_despesa"].id,
        valor=valor,
        descricao="GLOB-E-01 despesa",
        data=hoje,
    )

    _assert_ui_ecossistema(page, app_base_url, data)
    esperado = snapshot_ecossistema_esperado(
        data["user"], conta=data["conta"], categoria=data["cat_despesa"]
    )
    assert esperado["despesas"] == valor
    assert esperado["orc_realizado"] == valor


@pytest.mark.ecossistema
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_glob_e_02_editar_valor_reflexo(logged_in_ecossistema_page, app_base_url):
    page, data = logged_in_ecossistema_page
    hoje = _hoje()
    tx = Transacao.objects.create(
        usuario=data["user"],
        conta=data["conta"],
        categoria=data["cat_despesa"],
        tipo="despesa",
        valor=Decimal("30.00"),
        data=hoje,
        descricao="GLOB-E-02 alvo",
    )
    antes = snapshot_ecossistema_esperado(
        data["user"], conta=data["conta"], categoria=data["cat_despesa"]
    )

    hist = HistoricoPage(page, app_base_url)
    hist.open(hoje.year, hoje.month)
    hist.editar_por_id(tx.id)
    TransacaoModalPage(page, app_base_url).fill_valor(Decimal("55.00"))
    TransacaoModalPage(page, app_base_url).salvar()

    _assert_ui_ecossistema(page, app_base_url, data)
    depois = snapshot_ecossistema_esperado(
        data["user"], conta=data["conta"], categoria=data["cat_despesa"]
    )
    assert depois["despesas"] - antes["despesas"] == Decimal("25.00")
    assert depois["orc_realizado"] - antes["orc_realizado"] == Decimal("25.00")


@pytest.mark.ecossistema
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_glob_e_03_excluir_reflexo(logged_in_ecossistema_page, app_base_url):
    page, data = logged_in_ecossistema_page
    hoje = _hoje()
    tx = Transacao.objects.create(
        usuario=data["user"],
        conta=data["conta"],
        categoria=data["cat_despesa"],
        tipo="despesa",
        valor=Decimal("22.00"),
        data=hoje,
        descricao="GLOB-E-03 excluir",
    )
    antes = snapshot_ecossistema_esperado(
        data["user"], conta=data["conta"], categoria=data["cat_despesa"]
    )

    hist = HistoricoPage(page, app_base_url)
    hist.open(hoje.year, hoje.month)
    hist.excluir_por_id(tx.id)

    _assert_ui_ecossistema(page, app_base_url, data)
    depois = snapshot_ecossistema_esperado(
        data["user"], conta=data["conta"], categoria=data["cat_despesa"]
    )
    assert antes["despesas"] - depois["despesas"] == Decimal("22.00")
    assert antes["orc_realizado"] - depois["orc_realizado"] == Decimal("22.00")


@pytest.mark.ecossistema
@pytest.mark.relatorios_consistency
@pytest.mark.django_db(transaction=True)
def test_glob_e_04_consistencia_pos_reload(logged_in_ecossistema_page, app_base_url):
    page, data = logged_in_ecossistema_page
    hoje = _hoje()

    home = RelatoriosHomePage(page, app_base_url)
    home.open()
    home.abrir_nova_despesa()
    TransacaoModalPage(page, app_base_url).criar_transacao(
        tipo="despesa",
        conta_id=data["conta"].id,
        cartao_id=None,
        categoria_id=data["cat_despesa"].id,
        valor=Decimal("60.00"),
        descricao="GLOB-E-04 reload",
        data=hoje,
    )

    _assert_ui_ecossistema(page, app_base_url, data)
    page.reload(wait_until="load")
    _assert_ui_ecossistema(page, app_base_url, data)

    fluxo = FluxoCaixaPage(page, app_base_url)
    fluxo.open()
    fluxo_esperado = snapshot_ecossistema_esperado(
        data["user"], conta=data["conta"], categoria=data["cat_despesa"]
    )
    page.reload(wait_until="load")
    assert fluxo.totais_despesas() == fluxo_esperado["fluxo_despesas"]
