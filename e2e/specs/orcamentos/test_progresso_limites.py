"""ORC-PCT-E*, ORC-LIM-E* — progresso e limites excedidos."""

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.orcamentos_page import OrcamentosPage
from e2e.helpers.orcamento_contracts import verify_linha_categoria


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_pct_e01_barra_progresso(logged_in_orcamentos_page, app_base_url):
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    expect(logged_in_orcamentos_page.locator('[role="progressbar"]').first).to_be_visible()


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_pct_e02_status_por_categoria(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    user = persona_orcamentos["user"]
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    verify_linha_categoria(user, "Orc Moradia", status="ok")
    verify_linha_categoria(user, "Orc Transporte", status="risco")
    verify_linha_categoria(user, "Orc Lazer", status="excedido")
    assert "Atenção" in pag.status_categoria("Orc Transporte")
    assert "Estourado" in pag.status_categoria("Orc Lazer")


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_lim_e01_disponivel_negativo(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    card = pag.card_categoria("Orc Lazer")
    expect(card).to_contain_text("Acima do limite")


@pytest.mark.orcamentos
@pytest.mark.orcamentos_avancados
@pytest.mark.django_db(transaction=True)
def test_orc_lim_e02_hero_global_excedido_ou_risco(logged_in_orcamentos_page, app_base_url, persona_orcamentos):
    pag = OrcamentosPage(logged_in_orcamentos_page, app_base_url)
    pag.open()
    hero = logged_in_orcamentos_page.locator("#orcamento-hero-resumo")
    texto = hero.inner_text()
    assert "%" in texto
    upper = texto.upper()
    assert "ORÇADO" in upper and "GASTO" in upper
