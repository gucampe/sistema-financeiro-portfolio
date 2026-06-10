"""ORC-MUL-E*, ORC-GRP-E* — múltiplos meses e painel agregado."""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.orcamentos_page import OrcamentosPage
from e2e.fixtures.pages.relatorios_page import FiltrosPortalPage
from e2e.helpers.orcamento_contracts import verify_painel_mes


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_mul_e01_filtro_90d(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    user = persona_orcamentos["user"]
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    filtros = FiltrosPortalPage(logged_in_orcamentos_page, app_base_url)
    filtros.abrir()
    filtros.selecionar_preset("ultimos_90d")
    filtros.aplicar()
    painel = verify_painel_mes(user, {"preset": "ultimos_90d"})
    ui = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    assert ui.painel_gasto() == painel["realizado"]


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_grp_e01_contagem_saude(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    user = persona_orcamentos["user"]
    painel = verify_painel_mes(user)
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    assert pag.contagem_saude("ok") == painel["contagem_saude"]["ok"]
    assert pag.contagem_saude("risco") == painel["contagem_saude"]["risco"]
    assert pag.contagem_saude("excedido") == painel["contagem_saude"]["excedido"]


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_grp_e02_hero_percentual(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    user = persona_orcamentos["user"]
    painel = verify_painel_mes(user)
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    ui_pct = pag.painel_percentual()
    assert ui_pct is not None
    assert abs(ui_pct - round(painel["percentual"], 0)) < 2
    expect(logged_in_orcamentos_page.locator("#orcamento-hero-resumo")).to_contain_text("%")
