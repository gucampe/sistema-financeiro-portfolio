from decimal import Decimal
from pathlib import Path

import pytest
from playwright.sync_api import expect

from financial_contracts.saldo_contracts import assert_saldo_conta
from transacoes.models import Transacao

SAMPLE_OFX = Path(__file__).resolve().parents[2] / "fixtures" / "files" / "sample.ofx"


@pytest.mark.mvp
@pytest.mark.import_ofx
@pytest.mark.django_db(transaction=True)
def test_trx_20_import_ofx_basico(logged_in_page, app_base_url, persona_basic):
    page = logged_in_page
    conta = persona_basic["conta"]
    saldo_antes = conta.saldo_atual_calc
    count_antes = Transacao.objects.filter(usuario=persona_basic["user"]).count()

    page.goto(f"{app_base_url}/transacoes/")
    page.click("#btn-importar-ofx")
    expect(page.locator("#overlay-importar-ofx")).to_be_visible()

    page.select_option("#import-ofx-conta", value=str(conta.id))
    page.locator("#import-ofx-conta").dispatch_event("change")
    page.set_input_files("#import-ofx-arquivo", str(SAMPLE_OFX))

    with page.expect_response(lambda r: "importar/ofx/preview" in r.url):
        page.click("#btn-import-ofx-preview")

    page.wait_for_selector("#import-ofx-step-preview:not(.hidden)", timeout=15000)
    expect(page.locator("#import-ofx-tbody tr")).not_to_have_count(0)

    with page.expect_response(lambda r: "importar/ofx/confirmar" in r.url):
        page.click("#btn-import-ofx-confirmar")

    page.wait_for_load_state("load")

    conta.refresh_from_db()
    count_depois = Transacao.objects.filter(usuario=persona_basic["user"]).count()
    assert count_depois > count_antes
    assert conta.saldo_atual_calc != saldo_antes or count_depois > count_antes
    assert_saldo_conta(conta, conta.saldo_atual_calc)
