from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from cartoes.models import Fatura
from cartoes.services.gestao_faturas import calcular_resumo_pagamento
from e2e.fixtures.pages.faturas_page import FaturaDetalhePage
from e2e.helpers.financial_contracts import verify_fatura, verify_saldo_conta
from financial_contracts.fatura_contracts import assert_fatura_saldo, assert_status_fatura_coerente
from financial_contracts.saldo_contracts import assert_saldo_conta, calcular_saldo_esperado
from transacoes.models import Transacao


def _hoje() -> date:
    return timezone.localdate()


@pytest.mark.mvp
@pytest.mark.django_db(transaction=True)
def test_fat_03_pagar_fatura_total(logged_in_card_page, app_base_url, persona_card):
    page = logged_in_card_page
    user = persona_card["user"]
    conta = persona_card["conta"]
    cartao = persona_card["cartao"]
    cat = persona_card["cat_despesa"]

    hoje = _hoje()
    tx = Transacao.objects.create(
        usuario=user,
        conta=conta,
        cartao=cartao,
        categoria=cat,
        tipo="despesa",
        valor=Decimal("120.00"),
        data=hoje,
        descricao="E2E compra pagar total",
    )
    fatura = tx.fatura
    saldo_antes = calcular_saldo_esperado(conta, incluir_compras_cartao=False)
    resumo = calcular_resumo_pagamento(fatura)

    fatura_page = FaturaDetalhePage(page, app_base_url)
    fatura_page.open(cartao.id, fatura.id)
    fatura_page.pagar()

    conta.refresh_from_db()
    fatura.refresh_from_db()
    assert_saldo_conta(
        conta, saldo_antes - resumo.total, incluir_compras_cartao=False
    )
    assert fatura.status_pagamento == Fatura.StatusPagamento.PAGO
    verify_fatura(fatura.id)


@pytest.mark.mvp
@pytest.mark.decimal
@pytest.mark.django_db(transaction=True)
def test_fat_04_pagamento_parcial_dec_03(logged_in_card_page, app_base_url, persona_card):
    page = logged_in_card_page
    user = persona_card["user"]
    conta = persona_card["conta"]
    cartao = persona_card["cartao"]
    cat = persona_card["cat_despesa"]

    hoje = _hoje()
    tx = Transacao.objects.create(
        usuario=user,
        conta=conta,
        cartao=cartao,
        categoria=cat,
        tipo="despesa",
        valor=Decimal("100.00"),
        data=hoje,
        descricao="E2E compra parcial",
    )
    fatura = tx.fatura
    saldo_antes = calcular_saldo_esperado(conta, incluir_compras_cartao=False)

    fatura_page = FaturaDetalhePage(page, app_base_url)
    fatura_page.open(cartao.id, fatura.id)
    fatura_page.pagar(Decimal("33.33"))

    conta.refresh_from_db()
    fatura.refresh_from_db()
    assert_saldo_conta(
        conta, saldo_antes - Decimal("33.33"), incluir_compras_cartao=False
    )
    assert_fatura_saldo(fatura)
    assert_status_fatura_coerente(fatura)
    assert fatura.status_pagamento == Fatura.StatusPagamento.PARCIAL
    verify_saldo_conta(
        conta.id, saldo_antes - Decimal("33.33"), incluir_compras_cartao=False
    )
