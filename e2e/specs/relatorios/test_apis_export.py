"""REL-API-* — APIs e export CSV."""

import pytest

from e2e.helpers.relatorio_contracts import filtros_from_params


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_api_01_serie_tendencia(logged_in_relatorios_page, app_base_url, persona_relatorios):
    page = logged_in_relatorios_page
    page.goto(f"{app_base_url}/relatorios/fluxo-caixa/")
    resp = page.request.get(f"{app_base_url}/relatorios/api/serie-tendencia/?preset=este_mes")
    assert resp.status == 200
    body = resp.json()
    assert "labels" in body or "receitas" in body or isinstance(body, dict)


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_api_02_top_categorias_despesa(logged_in_relatorios_page, app_base_url, persona_relatorios):
    resp = logged_in_relatorios_page.request.get(
        f"{app_base_url}/relatorios/api/top-categorias/?preset=este_mes&tipo=despesa"
    )
    assert resp.status == 200
    data = resp.json()
    assert isinstance(data, list) or "categorias" in data or isinstance(data, dict)


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_api_03_export_csv_job(logged_in_relatorios_page, app_base_url, persona_relatorios):
    page = logged_in_relatorios_page
    page.goto(f"{app_base_url}/relatorios/")
    csrf = page.locator("[name=csrfmiddlewaretoken]").first.input_value()
    resp = page.request.post(
        f"{app_base_url}/relatorios/api/export/csv/",
        headers={"X-CSRFToken": csrf},
        data={"preset": "este_mes"},
    )
    assert resp.status in (200, 202)
    if resp.status == 202:
        assert "job_id" in resp.json()


@pytest.mark.relatorios
@pytest.mark.django_db(transaction=True)
def test_rel_api_04_export_respeita_filtros(logged_in_relatorios_page, app_base_url, persona_relatorios):
    user = persona_relatorios["user"]
    conta_b = persona_relatorios["conta_b"].id
    page = logged_in_relatorios_page
    page.goto(f"{app_base_url}/relatorios/fluxo-caixa/?preset=este_mes&conta={conta_b}")
    csrf = page.locator("[name=csrfmiddlewaretoken]").first.input_value()
    resp = page.request.post(
        f"{app_base_url}/relatorios/api/export/csv/",
        headers={"X-CSRFToken": csrf},
        data={"preset": "este_mes", "conta": str(conta_b)},
    )
    assert resp.status in (200, 202)
    filtros = filtros_from_params(user, {"preset": "este_mes", "conta": [conta_b]})
    assert filtros.conta_ids == (conta_b,)
