from decimal import Decimal

import pytest
from playwright.sync_api import expect

from e2e.fixtures.pages.dashboard_page import DashboardPage
from relatorios.tests.helpers.kpi_home import kpi_home


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_dash_01_kpis_refletem_mes(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    user = persona_basic["user"]
    totais = kpi_home(user)

    dash = DashboardPage(page, app_base_url)
    dash.open()

    receitas_ui = dash.kpi_receitas()
    despesas_ui = dash.kpi_despesas()

    assert receitas_ui == totais["receitas"]
    assert despesas_ui == totais["despesas"]
    expect(page.locator(".dash-valor").first).to_be_visible()
