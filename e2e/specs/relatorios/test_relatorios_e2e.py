"""REL-* — relatórios e export."""

import pytest
from playwright.sync_api import expect


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_01_fluxo_caixa_carrega(logged_in_page, app_base_url):
    page = logged_in_page
    page.goto(f"{app_base_url}/relatorios/fluxo-caixa/")
    expect(page.locator("#chart-fluxo")).to_be_attached()


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_02_despesas_categoria(logged_in_page, app_base_url):
    page = logged_in_page
    page.goto(f"{app_base_url}/relatorios/despesas-por-categoria/")
    expect(page.locator("body")).to_contain_text("categoria")


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_15_export_csv_inicia_job(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    page.goto(f"{app_base_url}/relatorios/")
    csrf = page.locator("[name=csrfmiddlewaretoken]").first.input_value()
    response = page.request.post(
        f"{app_base_url}/relatorios/api/export/csv/",
        headers={"X-CSRFToken": csrf},
        data={},
    )
    assert response.status in (200, 202)
    if response.status == 202:
        body = response.json()
        assert "job_id" in body
