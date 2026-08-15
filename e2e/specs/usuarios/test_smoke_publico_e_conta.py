"""E2E smoke — landing, login público, configurações e onboarding."""

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.login_page import LoginPage


@pytest.mark.cadastro_smoke
@pytest.mark.django_db(transaction=True)
def test_landing_publica_exibe_marca(page, app_base_url):
    page.goto(f"{app_base_url}/")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("text=GranaGo").first).to_be_visible()
    expect(
        page.get_by_role(
            "heading",
            name="Você sabe quanto ganhou. Mas sabe pra onde foi cada real?",
        )
    ).to_be_visible()

    page.goto(f"{app_base_url}/primeiros-donos/")
    page.wait_for_load_state("domcontentloaded")
    expect(page.get_by_text("Veja 3 meses de gastos").first).to_be_visible()


@pytest.mark.cadastro_smoke
@pytest.mark.django_db(transaction=True)
def test_login_publico_formulario_visivel(page, app_base_url):
    login = LoginPage(page, app_base_url)
    login.open()
    expect(page.locator("#email")).to_be_visible()
    expect(page.locator("#senha")).to_be_visible()
    expect(page.locator('button[type="submit"]')).to_be_visible()


@pytest.mark.cadastro_smoke
@pytest.mark.django_db(transaction=True)
def test_configuracoes_abre_perfil(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    page.goto(f"{app_base_url}/configuracoes/")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("h1", has_text="Configurações")).to_be_visible()
    expect(page.locator("#perfil")).to_be_visible()
    expect(page.locator("#form-dados-pessoais")).to_be_visible()
    expect(page.get_by_text(persona_basic["user"].email)).to_be_visible()


@pytest.mark.cadastro_smoke
@pytest.mark.django_db(transaction=True)
def test_onboarding_pagina_e_status_json(logged_in_page, app_base_url):
    page = logged_in_page
    page.goto(f"{app_base_url}/primeiros-passos/")
    page.wait_for_load_state("domcontentloaded")
    expect(page.locator("#pp-page")).to_be_visible()
    expect(page.locator("#pp-progress-label")).to_be_visible()

    status = page.request.get(f"{app_base_url}/primeiros-passos/status/")
    assert status.ok
    data = status.json()
    assert "concluidas" in data
    assert "total" in data
    assert "etapas" in data
