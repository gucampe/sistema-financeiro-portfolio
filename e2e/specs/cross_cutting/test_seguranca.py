"""E2E-SEC-01..06 — Segurança (status, redirect, seletor estável)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from e2e.factories.personas import E2E_PASSWORD, seed_persona_basic
from e2e.fixtures.pages.login_page import LoginPage
from relatorios.models import ExportRelatorioJob
from transacoes.models import Transacao


@pytest.mark.seguranca
@pytest.mark.django_db(transaction=True)
def test_e2e_sec_01_anonimo_api_serie_tendencia(browser, app_base_url):
    context = browser.new_context()
    page = context.new_page()
    resp = page.request.get(
        f"{app_base_url}/relatorios/api/serie-tendencia/?preset=este_mes",
        max_redirects=0,
    )
    assert resp.status == 302
    context.close()


@pytest.mark.seguranca
@pytest.mark.django_db(transaction=True)
def test_e2e_sec_02_idor_editar_transacao_b(browser, app_base_url, persona_basic):
    outro = seed_persona_basic(f"sec-b-{id(persona_basic)}@e2e.granago.test")
    tx = Transacao.objects.create(
        usuario=outro["user"],
        conta=outro["conta"],
        categoria=outro["cat_despesa"],
        tipo="despesa",
        valor=Decimal("10.00"),
        data=date.today(),
        descricao="SEC-B",
    )
    context = browser.new_context()
    page = context.new_page()
    LoginPage(page, app_base_url).login(persona_basic["user"].email, E2E_PASSWORD)
    resp = page.request.get(f"{app_base_url}/transacoes/{tx.id}/editar/?ajax=1")
    assert resp.status == 404
    context.close()


@pytest.mark.seguranca
@pytest.mark.django_db(transaction=True)
def test_e2e_sec_03_idor_export_job_b(browser, app_base_url, persona_basic):
    outro = seed_persona_basic(f"sec-job-{id(persona_basic)}@e2e.granago.test")
    job = ExportRelatorioJob.objects.create(
        usuario=outro["user"],
        status=ExportRelatorioJob.STATUS_PENDING,
        filtros_json="{}",
    )
    context = browser.new_context()
    page = context.new_page()
    LoginPage(page, app_base_url).login(persona_basic["user"].email, E2E_PASSWORD)
    resp = page.request.get(f"{app_base_url}/relatorios/api/export/jobs/{job.id}/")
    assert resp.status == 404
    context.close()


@pytest.mark.seguranca
@pytest.mark.django_db(transaction=True)
def test_e2e_sec_04_csrf_orcamentos_salvar_sem_token(logged_in_page, app_base_url):
    resp = logged_in_page.request.post(
        f"{app_base_url}/relatorios/orcamentos/salvar/",
        headers={"X-Requested-With": "XMLHttpRequest"},
        data={"categoria_id": "1", "valor": "100"},
    )
    assert resp.status == 403


@pytest.mark.seguranca
@pytest.mark.django_db(transaction=True)
def test_e2e_sec_05_historico_sem_transacao_b(logged_in_page, app_base_url, persona_basic):
    outro = seed_persona_basic(f"sec-list-{id(persona_basic)}@e2e.granago.test")
    tx = Transacao.objects.create(
        usuario=outro["user"],
        conta=outro["conta"],
        categoria=outro["cat_despesa"],
        tipo="despesa",
        valor=Decimal("10.00"),
        data=date.today(),
        descricao="SEC-B",
    )
    logged_in_page.goto(f"{app_base_url}/transacoes/")
    locator = logged_in_page.locator(f'[data-transacao-id="{tx.id}"]')
    assert locator.count() == 0


@pytest.mark.seguranca
@pytest.mark.django_db(transaction=True)
def test_e2e_sec_06_anonimo_historico_redireciona_login(browser, app_base_url):
    context = browser.new_context()
    page = context.new_page()
    page.goto(f"{app_base_url}/transacoes/")
    assert "/login/" in page.url
    context.close()
