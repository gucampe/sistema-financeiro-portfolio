import pytest
from playwright.sync_api import expect

from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.login_page import LoginPage


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_auth_01_login_valido_redirect_dashboard(page, app_base_url, persona_basic):
    login = LoginPage(page, app_base_url)
    login.login(persona_basic["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    expect(page.locator("text=Receitas do mês").first).to_be_visible()


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_auth_03_rota_protegida_sem_login(page, app_base_url):
    page.goto(f"{app_base_url}/relatorios/")
    page.wait_for_load_state("domcontentloaded")
    expect(page).to_have_url(f"{app_base_url}/login/?next=/relatorios/")
