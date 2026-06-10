"""E2E-IMP-01..05 — importação OFX/XLSX avançada."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.utils import timezone

from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.import_pages import ImportOfxPage, ImportPlanilhaPage
from e2e.fixtures.pages.login_page import LoginPage
from e2e.helpers.planilha_fixture import build_sample_xlsx_bytes
from financial_contracts.saldo_contracts import assert_saldo_conta
from transacoes.models import Transacao
from transacoes.tests.helpers.import_fixtures import (
    build_ofx_bytes,
    build_ofx_concorrente,
    build_ofx_corrupto,
    build_ofx_dup,
)


def _hoje() -> date:
    return timezone.localdate()


@pytest.mark.importacao_avancada
@pytest.mark.django_db(transaction=True)
def test_e2e_imp_01_xlsx_medio_preview(logged_in_page, app_base_url, persona_basic, tmp_path):
    raw = build_sample_xlsx_bytes(n_linhas=200, data=_hoje())
    path = tmp_path / "medio.xlsx"
    path.write_bytes(raw)

    planilha = ImportPlanilhaPage(logged_in_page, app_base_url)
    planilha.abrir()
    planilha.selecionar_conta(persona_basic["conta"].id)
    planilha.upload(path)
    planilha.aguardar_preview()
    assert planilha.linhas_preview_count() == 200


@pytest.mark.importacao_avancada
@pytest.mark.django_db(transaction=True)
def test_e2e_imp_02_dup_ofx_preview(logged_in_page, app_base_url, persona_basic, tmp_path):
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    Transacao.objects.create(
        usuario=user,
        conta=conta,
        categoria=persona_basic["cat_despesa"],
        tipo="despesa",
        valor=Decimal("42.50"),
        data=date(2024, 1, 15),
        descricao="PADARIA CENTRAL",
        ofx_fitid="dup-seed-fitid",
    )
    path = tmp_path / "dup.ofx"
    path.write_bytes(build_ofx_dup("fitid_igual"))

    ofx = ImportOfxPage(logged_in_page, app_base_url)
    ofx.abrir()
    ofx.selecionar_conta(conta.id)
    ofx.upload(path)
    ofx.aguardar_preview()
    assert ofx.linhas_preview_count() >= 1
    assert not ofx.linha_marcada(0)


@pytest.mark.importacao_avancada
@pytest.mark.django_db(transaction=True)
def test_e2e_imp_03_import_incremental(logged_in_page, app_base_url, persona_basic, tmp_path):
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    txs = [
        {"fitid": "inc-e2e-1", "trnamt": "-11.00", "name": "Inc 1", "dtposted": "20240901120000"},
        {"fitid": "inc-e2e-2", "trnamt": "-22.00", "name": "Inc 2", "dtposted": "20240902120000"},
        {"fitid": "inc-e2e-3", "trnamt": "-33.00", "name": "Inc 3", "dtposted": "20240903120000"},
    ]
    path = tmp_path / "inc.ofx"
    path.write_bytes(build_ofx_bytes(txs))

    ofx = ImportOfxPage(logged_in_page, app_base_url)
    ofx.abrir()
    ofx.selecionar_conta(conta.id)
    ofx.upload(path)
    ofx.aguardar_preview()
    ofx.confirmar()

    conta.refresh_from_db()
    saldo_meio = conta.saldo_atual_calc
    count_meio = Transacao.objects.filter(usuario=persona_basic["user"], conta=conta).count()
    assert saldo_meio != saldo_antes

    ofx.abrir()
    ofx.selecionar_conta(conta.id)
    ofx.upload(path)
    ofx.aguardar_preview()
    assert ofx.linhas_preview_count() == 3
    for i in range(3):
        assert not ofx.linha_marcada(i)

    ofx.tentar_confirmar_sem_linhas()
    conta.refresh_from_db()
    assert conta.saldo_atual_calc == saldo_meio
    assert (
        Transacao.objects.filter(usuario=persona_basic["user"], conta=conta).count()
        == count_meio
    )


@pytest.mark.importacao_avancada
@pytest.mark.django_db(transaction=True)
def test_e2e_imp_04_ofx_quebrado(logged_in_page, app_base_url, persona_basic, tmp_path):
    path = tmp_path / "bad.ofx"
    path.write_bytes(build_ofx_corrupto("lixo"))

    ofx = ImportOfxPage(logged_in_page, app_base_url)
    ofx.abrir()
    ofx.selecionar_conta(persona_basic["conta"].id)
    ofx.upload(path)
    with logged_in_page.expect_response(lambda r: "importar/ofx/preview" in r.url):
        logged_in_page.click("#btn-import-ofx-preview")
    texto = ofx.erro_visivel()
    assert texto
    assert ofx.linhas_preview_count() == 0


@pytest.mark.importacao_avancada
@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_e2e_imp_05_import_concorrente(browser, app_base_url, persona_basic, django_db_blocker, tmp_path):
    django_db_blocker.unblock()
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    path = tmp_path / "conc.ofx"
    path.write_bytes(build_ofx_concorrente(5))

    count_antes = Transacao.objects.filter(usuario=user, conta=conta).count()
    saldo_antes = conta.saldo_atual_calc

    ctx1 = browser.new_context(timezone_id="America/Sao_Paulo")
    ctx2 = browser.new_context(timezone_id="America/Sao_Paulo")
    p1 = ctx1.new_page()
    p2 = ctx2.new_page()
    LoginPage(p1, app_base_url).login(user.email, E2E_PASSWORD)
    LoginPage(p2, app_base_url).login(user.email, E2E_PASSWORD)

    ofx1 = ImportOfxPage(p1, app_base_url)
    ofx2 = ImportOfxPage(p2, app_base_url)

    for ofx in (ofx1, ofx2):
        ofx.abrir()
        ofx.selecionar_conta(conta.id)
        ofx.upload(path)
        ofx.aguardar_preview()

    p1.click("#btn-import-ofx-confirmar")
    p2.click("#btn-import-ofx-confirmar")
    p1.wait_for_load_state("load")
    p2.wait_for_load_state("load")

    count_depois = Transacao.objects.filter(usuario=user, conta=conta).count()
    assert count_depois == count_antes + 5

    conta.refresh_from_db()
    assert_saldo_conta(conta, conta.saldo_atual_calc)
    assert conta.saldo_atual_calc == saldo_antes - Decimal("60.00")

    ctx1.close()
    ctx2.close()
