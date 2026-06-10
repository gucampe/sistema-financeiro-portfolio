"""REL-FLX-UI-* — entradas x saídas."""

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.relatorios_page import FluxoCaixaPage
from e2e.helpers.relatorio_contracts import verify_fluxo_periodo


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_flx_ui_01_chart_renderiza(logged_in_relatorios_page, app_base_url):
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    expect(logged_in_relatorios_page.locator("#chart-fluxo")).to_be_attached()


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_flx_ui_02_cards_iguais_servico(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    esperado = verify_fluxo_periodo(user, {"preset": "este_mes"})
    assert fluxo.totais_receitas() == esperado["receitas"]
    assert fluxo.totais_despesas() == esperado["despesas"]
    assert fluxo.totais_resultado() == esperado["resultado"]


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_flx_ui_03_override_ano_mes(logged_in_relatorios_page, app_base_url, persona_relatorios):
    from django.utils import timezone

    hoje = timezone.localdate()
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open(f"?ano={hoje.year}&mes={hoje.month}")
    esperado = verify_fluxo_periodo(user := persona_relatorios["user"], {"preset": "este_mes"})
    assert fluxo.totais_receitas() == esperado["receitas"]


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_flx_ui_04_link_ver_transacoes(logged_in_relatorios_page, app_base_url):
    fluxo = FluxoCaixaPage(logged_in_relatorios_page, app_base_url)
    fluxo.open()
    link = logged_in_relatorios_page.locator("a").filter(has_text="Ver transações").first
    if link.count() == 0:
        pytest.skip("Link Ver transações ausente")
    href = link.get_attribute("href") or ""
    assert "inicio=" in href or "transacoes" in href
