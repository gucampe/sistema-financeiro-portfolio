"""INV-* — contratos financeiros validados após fluxos UI."""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from cartoes.services.gestao_faturas import pagar_fatura
from e2e.fixtures.pages.dashboard_page import DashboardPage
from e2e.fixtures.pages.transacoes_page import TransacaoModalPage
from financial_contracts.competencia_contracts import assert_data_competencia_em_fatura
from financial_contracts.fatura_contracts import assert_fatura_saldo, assert_fatura_total
from financial_contracts.saldo_contracts import assert_patrimonio_contas, assert_saldo_conta
from transacoes.models import Transacao


def _hoje():
    return timezone.localdate()


@pytest.mark.integrity
@pytest.mark.django_db(transaction=True)
def test_inv_01_saldo_apos_receita(logged_in_page, app_base_url, persona_basic):
    conta = persona_basic["conta"]
    saldo = conta.saldo_atual_calc

    dash = DashboardPage(logged_in_page, app_base_url)
    dash.open()
    dash.open_nova_receita()

    modal = TransacaoModalPage(logged_in_page, app_base_url)
    modal.criar_transacao(
        tipo="receita",
        conta_id=conta.id,
        cartao_id=None,
        categoria_id=persona_basic["cat_receita"].id,
        valor=Decimal("50.00"),
        descricao="INV-01",
        data=_hoje(),
    )

    conta.refresh_from_db()
    assert_saldo_conta(conta, saldo + Decimal("50.00"))


@pytest.mark.integrity
@pytest.mark.django_db(transaction=True)
def test_inv_02_patrimonio_dashboard(persona_basic):
    user = persona_basic["user"]
    from contas.models import Conta

    total = sum(c.saldo_atual_calc for c in Conta.objects.filter(usuario=user, ativa=True))
    assert_patrimonio_contas(user, total)


@pytest.mark.integrity
@pytest.mark.django_db(transaction=True)
def test_inv_f01_fatura_total_apos_compra(persona_card):
    cartao = persona_card["cartao"]
    tx = Transacao.objects.filter(usuario=persona_card["user"], cartao=cartao).first()
    assert tx is not None
    fatura = tx.fatura
    assert_fatura_total(fatura)
    assert_data_competencia_em_fatura(tx)


@pytest.mark.integrity
@pytest.mark.django_db(transaction=True)
def test_inv_f02_saldo_fatura_apos_pagamento_parcial(persona_card):
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
        valor=Decimal("80.00"),
        data=hoje,
        descricao="INV-F02",
    )
    fatura = tx.fatura
    pagar_fatura(fatura=fatura, valor=Decimal("30.00"))
    fatura.refresh_from_db()
    assert_fatura_saldo(fatura)
