"""RC-* — concorrência e race conditions."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone
from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.services.gestao_faturas import calcular_resumo_pagamento, valor_pago_fatura
from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.faturas_page import FaturaDetalhePage
from e2e.fixtures.pages.login_page import LoginPage
from financial_contracts.fatura_contracts import assert_fatura_saldo
from transacoes.models import Transacao


def _hoje():
    return timezone.localdate()


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_rc_04_refresh_apos_pagamento_parcial(
    browser, app_base_url, persona_card, django_db_blocker
):
    django_db_blocker.unblock()
    user = persona_card["user"]
    conta = persona_card["conta"]
    cartao = persona_card["cartao"]
    cat = persona_card["cat_despesa"]
    hoje = _hoje()
    fatura = obter_ou_criar_fatura(cartao, hoje)
    Transacao.objects.create(
        usuario=user,
        conta=conta,
        cartao=cartao,
        categoria=cat,
        tipo="despesa",
        valor=Decimal("90.00"),
        data=hoje,
        descricao="RC-04",
    )
    fatura.refresh_from_db()
    fatura_id = fatura.id

    context = browser.new_context(timezone_id="America/Sao_Paulo")
    page = context.new_page()
    LoginPage(page, app_base_url).login(user.email, E2E_PASSWORD)

    fatura_page = FaturaDetalhePage(page, app_base_url)
    fatura_page.open(cartao.id, fatura_id)
    fatura_page.pagar(Decimal("40.00"))
    page.reload()
    page.wait_for_load_state("load")

    from cartoes.models import Fatura

    fatura = Fatura.objects.get(pk=fatura_id)
    assert_fatura_saldo(fatura)
    assert valor_pago_fatura(fatura) == Decimal("40.00")
    context.close()


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_rc_01_pagamento_simultaneo_duas_abas(browser, app_base_url, persona_card, django_db_blocker):
    django_db_blocker.unblock()
    user = persona_card["user"]
    conta = persona_card["conta"]
    cartao = persona_card["cartao"]
    cat = persona_card["cat_despesa"]
    hoje = _hoje()
    fatura = obter_ou_criar_fatura(cartao, hoje)
    Transacao.objects.create(
        usuario=user,
        conta=conta,
        cartao=cartao,
        categoria=cat,
        tipo="despesa",
        valor=Decimal("60.00"),
        data=hoje,
        descricao="RC-01",
    )
    fatura.refresh_from_db()
    resumo = calcular_resumo_pagamento(fatura)
    fatura_id = fatura.id
    cartao_id = cartao.id

    ctx1 = browser.new_context()
    ctx2 = browser.new_context()
    p1 = ctx1.new_page()
    p2 = ctx2.new_page()
    LoginPage(p1, app_base_url).login(user.email, E2E_PASSWORD)
    LoginPage(p2, app_base_url).login(user.email, E2E_PASSWORD)

    url = f"{app_base_url}/cartoes/{cartao_id}/faturas/{fatura_id}/"
    p1.goto(url)
    p2.goto(url)

    p1.locator('form[action*="pagar"] button[type="submit"]').click()
    p2.locator('form[action*="pagar"] button[type="submit"]').click()
    p1.wait_for_load_state("load")
    p2.wait_for_load_state("load")

    from cartoes.models import Fatura

    fatura = Fatura.objects.get(pk=fatura_id)
    pago = valor_pago_fatura(fatura)
    assert pago <= resumo.total
    assert_fatura_saldo(fatura)
    ctx1.close()
    ctx2.close()
