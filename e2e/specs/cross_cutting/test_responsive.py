"""RES-* — smoke responsivo."""

import pytest
from playwright.sync_api import expect

from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.login_page import LoginPage


@pytest.mark.cross_cutting
@pytest.mark.django_db(transaction=True)
def test_res_01_dashboard_mobile(browser, app_base_url, persona_basic):
    context = browser.new_context(
        viewport={"width": 390, "height": 844},
        timezone_id="America/Sao_Paulo",
    )
    page = context.new_page()
    LoginPage(page, app_base_url).login(persona_basic["user"].email, E2E_PASSWORD)
    page.goto(f"{app_base_url}/relatorios/")
    expect(page.locator(".dash-valor").first).to_be_visible()
    context.close()
