"""DEC-* — precisão decimal."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from cartoes.services.gestao_faturas import pagar_fatura
from financial_contracts.base import quantize_moeda
from financial_contracts.saldo_contracts import assert_saldo_conta, calcular_saldo_esperado
from transacoes.models import Transacao


@pytest.mark.decimal
def test_dec_02_aritmetica_decimal():
    assert quantize_moeda(Decimal("0.1") + Decimal("0.2")) == Decimal("0.30")


@pytest.mark.decimal
@pytest.mark.django_db(transaction=True)
def test_dec_03_pagamento_parcial_centavos(persona_card):
    user = persona_card["user"]
    conta = persona_card["conta"]
    cartao = persona_card["cartao"]
    cat = persona_card["cat_despesa"]
    hoje = timezone.localdate()
    saldo_antes = calcular_saldo_esperado(conta, incluir_compras_cartao=False)

    tx = Transacao.objects.create(
        usuario=user,
        conta=conta,
        cartao=cartao,
        categoria=cat,
        tipo="despesa",
        valor=Decimal("100.00"),
        data=hoje,
        descricao="DEC-03",
    )
    fatura = tx.fatura
    pagar_fatura(fatura=fatura, valor=Decimal("33.33"))
    pagar_fatura(fatura=fatura, valor=Decimal("33.33"))
    pagar_fatura(fatura=fatura, valor=Decimal("33.34"))

    conta.refresh_from_db()
    assert_saldo_conta(
        conta, saldo_antes - Decimal("100.00"), incluir_compras_cartao=False
    )
