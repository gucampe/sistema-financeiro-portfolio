"""TRX-22+ — importação de planilha .xlsx."""

from decimal import Decimal

import pytest
from playwright.sync_api import expect

from e2e.helpers.planilha_fixture import ensure_sample_xlsx
from financial_contracts.saldo_contracts import assert_saldo_conta
from transacoes.models import Transacao

SAMPLE_XLSX = ensure_sample_xlsx()
DESCRICAO_E2E = "E2E planilha import"


@pytest.mark.import_planilha
@pytest.mark.django_db(transaction=True)
def test_trx_22_import_planilha_basico(logged_in_page, app_base_url, persona_basic):
    """TRX-22: upload → preview → confirmar → lançamentos persistidos."""
    page = logged_in_page
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    count_antes = Transacao.objects.filter(usuario=user).count()

    page.goto(f"{app_base_url}/transacoes/")
    page.click("#btn-importar-planilha")
    expect(page.locator("#overlay-importar-planilha")).to_be_visible()

    page.wait_for_selector(
        f"#import-planilha-conta option[value='{conta.id}']",
        state="attached",
        timeout=10000,
    )
    page.select_option("#import-planilha-conta", value=str(conta.id))
    page.locator("#import-planilha-conta").dispatch_event("change")
    page.set_input_files("#import-planilha-arquivo", str(SAMPLE_XLSX))

    with page.expect_response(lambda r: "importar/planilha/preview" in r.url):
        page.click("#btn-import-planilha-preview")

    page.wait_for_selector("#import-planilha-feed .import-feed-item", timeout=15000)
    expect(page.locator("#import-planilha-feed .import-feed-item")).not_to_have_count(0)
    desc_input = page.locator(".import-planilha-descricao").first
    expect(desc_input).to_have_value(DESCRICAO_E2E)
    page.select_option(
        ".import-planilha-categoria",
        value=str(persona_basic["cat_despesa"].id),
    )

    with page.expect_response(lambda r: "importar/planilha/confirmar" in r.url):
        page.click("#btn-import-planilha-confirmar")

    page.wait_for_load_state("load")

    conta.refresh_from_db()
    count_depois = Transacao.objects.filter(usuario=user).count()
    assert count_depois == count_antes + 1
    assert Transacao.objects.filter(
        usuario=user, descricao=DESCRICAO_E2E, conta=conta
    ).exists()
    assert conta.saldo_atual_calc == saldo_antes - Decimal("45.75")
    assert_saldo_conta(conta, conta.saldo_atual_calc)


@pytest.mark.import_planilha
@pytest.mark.django_db(transaction=True)
def test_trx_23_planilha_preview_sem_confirmar(logged_in_page, app_base_url, persona_basic):
    """TRX-23: preview lista linhas sem persistir no banco."""
    page = logged_in_page
    user = persona_basic["user"]
    conta = persona_basic["conta"]
    count_antes = Transacao.objects.filter(usuario=user).count()

    page.goto(f"{app_base_url}/transacoes/")
    page.click("#btn-importar-planilha")
    page.select_option("#import-planilha-conta", value=str(conta.id))
    page.set_input_files("#import-planilha-arquivo", str(SAMPLE_XLSX))

    with page.expect_response(lambda r: "importar/planilha/preview" in r.url):
        page.click("#btn-import-planilha-preview")

    page.wait_for_selector("#import-planilha-feed .import-feed-item", timeout=15000)
    expect(page.locator("#import-planilha-step-preview")).to_be_visible()
    expect(page.locator(".import-planilha-descricao").first).to_have_value(DESCRICAO_E2E)

    count_depois = Transacao.objects.filter(usuario=user).count()
    assert count_depois == count_antes
