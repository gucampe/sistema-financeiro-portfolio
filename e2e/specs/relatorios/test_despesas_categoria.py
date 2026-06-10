"""REL-CAT-UI-* — despesas por categoria."""

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.relatorios_page import DespesasCategoriaPage
from e2e.helpers.relatorio_contracts import verify_categoria_total


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_cat_ui_01_hero_total(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    pag = DespesasCategoriaPage(logged_in_relatorios_page, app_base_url)
    pag.open()
    esperado = verify_categoria_total(user, {"preset": "este_mes"})
    assert pag.total_despesas() == esperado


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_cat_ui_02_delta_periodo_anterior(logged_in_relatorios_page, app_base_url):
    pag = DespesasCategoriaPage(logged_in_relatorios_page, app_base_url)
    pag.open()
    hero = logged_in_relatorios_page.locator('[aria-label="Resumo de despesas por categoria"]')
    expect(hero).to_contain_text("Vs período anterior")
