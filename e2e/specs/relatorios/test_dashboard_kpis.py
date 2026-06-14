"""E2E-DASH-01..08 — Visão Geral / KPIs."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from playwright.sync_api import expect

from e2e.fixtures.pages.relatorios_page import (
    FiltrosPortalPage,
    FluxoCaixaPage,
    RelatoriosHomePage,
)
from e2e.fixtures.pages.transacoes_page import TransacaoModalPage
from e2e.helpers.relatorio_contracts import kpi_home_esperado, verify_fluxo_periodo
from relatorios.tests.helpers.kpi_home import kpi_home


def _hoje() -> date:
    return timezone.localdate()


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_01_consistencia_home_fluxo(
    logged_in_relatorios_page, app_base_url, persona_relatorios
):
    user = persona_relatorios["user"]
    esperado = kpi_home_esperado(user)
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    ui = home.kpis_hero()
    assert ui["receitas"] == esperado["receitas"]
    assert ui["despesas"] == esperado["despesas"]
    assert ui["resultado"] == esperado["resultado"]

    home.ir_para_aba("Entradas x Saídas")
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo_esperado = verify_fluxo_periodo(user, {"preset": "este_mes"})
    assert fluxo.totais_receitas() == fluxo_esperado["receitas"]
    assert fluxo.totais_despesas() == fluxo_esperado["despesas"]
    assert fluxo.totais_resultado() == fluxo_esperado["resultado"]


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_02_filtros_nao_afetam_hero(
    logged_in_relatorios_page, app_base_url, persona_relatorios
):
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    antes = home.snapshot_kpis_hero()

    filtros = FiltrosPortalPage(logged_in_relatorios_page, app_base_url)
    filtros.abrir()
    filtros.selecionar_preset("ultimos_90d")
    filtros.desmarcar_todas_contas()
    filtros.marcar_conta(persona_relatorios["conta_b"].id)
    filtros.aplicar()

    depois = home.kpis_hero()
    assert depois == antes


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_03_comparativo_mes_anterior_visivel(
    logged_in_relatorios_page, app_base_url, persona_relatorios
):
    comp = kpi_home(persona_relatorios["user"])["comparacao"]
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    hero = logged_in_relatorios_page.locator(RelatoriosHomePage.HERO)
    if comp["delta_pct_receitas"] is not None:
        expect(hero).to_contain_text("vs mês anterior")


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_04_patrimonio_home(logged_in_relatorios_page, app_base_url, persona_relatorios):
    esperado = kpi_home(persona_relatorios["user"])["patrimonio"]
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    assert home.patrimonio() == esperado


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_05_ocultar_valores_ciclo_completo(
    logged_in_relatorios_page, app_base_url, persona_relatorios
):
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    antes = home.kpis_hero()

    home.toggle_ocultar()
    logged_in_relatorios_page.wait_for_timeout(300)
    for loc in logged_in_relatorios_page.locator(f"{RelatoriosHomePage.ROOT} .dash-valor").all():
        expect(loc).to_contain_text("•••")
    assert home.valores_ocultos()

    home.toggle_ocultar()
    logged_in_relatorios_page.wait_for_timeout(300)
    assert home.kpis_hero() == antes

    home.toggle_ocultar()
    logged_in_relatorios_page.wait_for_timeout(300)
    logged_in_relatorios_page.reload(wait_until="load")
    expect(logged_in_relatorios_page.locator(f"{RelatoriosHomePage.ROOT}")).to_have_attribute(
        "data-ocultar", "1"
    )
    expect(
        home.first_visible(f"{RelatoriosHomePage.HERO} .dash-valor")
    ).to_contain_text("•••")


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_06_reload_apos_receita(
    logged_in_relatorios_page, app_base_url, persona_relatorios
):
    user = persona_relatorios["user"]
    conta = persona_relatorios["conta_a"]
    antes = kpi_home(user)
    valor = Decimal("120.00")

    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    home.abrir_nova_receita()
    modal = TransacaoModalPage(logged_in_relatorios_page, app_base_url)
    modal.wait_modal_open()
    modal.criar_transacao(
        tipo="receita",
        conta_id=conta.id,
        cartao_id=None,
        categoria_id=persona_relatorios["cat_receita"].id,
        valor=valor,
        descricao="E2E-DASH-06 receita",
        data=_hoje(),
    )

    assert home.kpi_receitas() == antes["receitas"] + valor
    assert home.patrimonio() == antes["patrimonio"] + valor


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_07_reload_apos_despesa(
    logged_in_relatorios_page, app_base_url, persona_relatorios
):
    user = persona_relatorios["user"]
    antes = kpi_home(user)
    valor = Decimal("45.00")

    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    home.abrir_nova_despesa()
    modal = TransacaoModalPage(logged_in_relatorios_page, app_base_url)
    modal.wait_modal_open()
    modal.criar_transacao(
        tipo="despesa",
        conta_id=persona_relatorios["conta_a"].id,
        cartao_id=None,
        categoria_id=persona_relatorios["cat_despesa"].id,
        valor=valor,
        descricao="E2E-DASH-07 despesa",
        data=_hoje(),
    )

    assert home.kpi_despesas() == antes["despesas"] + valor


@pytest.mark.dashboard_kpis
@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_e2e_dash_08_widgets_smoke(logged_in_relatorios_page, app_base_url, persona_relatorios):
    home = RelatoriosHomePage(logged_in_relatorios_page, app_base_url)
    home.open()
    page = logged_in_relatorios_page

    expect(page.locator("section").filter(has_text="Cartões")).to_contain_text("Cartão Rel E2E")

    sec_orc = page.locator("section").filter(has_text="Orçamento do mês")
    expect(sec_orc).to_contain_text("E2E Despesas")
    expect(sec_orc).to_contain_text("%")

    sec_top = page.locator("section").filter(has_text="Para onde seu dinheiro está indo")
    if sec_top.locator("canvas#grafico-categorias").count() > 0:
        expect(sec_top.locator("canvas#grafico-categorias")).to_be_attached()
