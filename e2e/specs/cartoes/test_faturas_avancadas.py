"""E2E-FAT-05..10 — faturas avançadas (asserts UI estáveis, sem recálculo de saldo)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from cartoes.services.faturas import obter_ou_criar_fatura
from e2e.fixtures.pages.faturas_page import FaturaDetalhePage
from e2e.fixtures.pages.orcamentos_page import OrcamentosPage
from transacoes.models import Transacao


def _hoje() -> date:
    return timezone.localdate()


@pytest.mark.faturas_avancadas
@pytest.mark.django_db(transaction=True)
def test_e2e_fat_05_pagar_somente_cartao_a(logged_in_cartao_b_page, app_base_url, persona_cartao_b):
    user = persona_cartao_b["user"]
    conta = persona_cartao_b["conta"]
    cartao_a = persona_cartao_b["cartao_a"]
    cartao_b = persona_cartao_b["cartao_b"]
    cat = persona_cartao_b["cat_despesa"]
    d = date(2026, 4, 8)

    tx_a = Transacao.objects.create(
        usuario=user, conta=conta, cartao=cartao_a, categoria=cat,
        tipo="despesa", valor=Decimal("75.00"), data=d, descricao="E2E FAT-05 A",
    )
    tx_b = Transacao.objects.create(
        usuario=user, conta=conta, cartao=cartao_b, categoria=cat,
        tipo="despesa", valor=Decimal("45.00"), data=d, descricao="E2E FAT-05 B",
    )
    fatura_a = tx_a.fatura
    fatura_b = tx_b.fatura

    page = logged_in_cartao_b_page
    det_a = FaturaDetalhePage(page, app_base_url)
    det_a.open(cartao_a.id, fatura_a.id)
    det_a.pagar()
    assert det_a.falta_pagar_ausente()

    det_b = FaturaDetalhePage(page, app_base_url)
    det_b.open(cartao_b.id, fatura_b.id)
    assert det_b.acao_pagar_visivel()
    assert not det_b.falta_pagar_ausente()


@pytest.mark.faturas_avancadas
@pytest.mark.django_db(transaction=True)
def test_e2e_fat_06_compra_no_dia_fechamento(logged_in_cartao_b_page, app_base_url, persona_cartao_b):
    user = persona_cartao_b["user"]
    conta = persona_cartao_b["conta"]
    cartao_a = persona_cartao_b["cartao_a"]
    cat = persona_cartao_b["cat_despesa"]
    dia_fech = date(2026, 4, cartao_a.dia_fechamento)

    tx = Transacao.objects.create(
        usuario=user, conta=conta, cartao=cartao_a, categoria=cat,
        tipo="despesa", valor=Decimal("33.00"), data=dia_fech, descricao="E2E FAT-06 fech",
    )
    esperada = obter_ou_criar_fatura(cartao_a, dia_fech)
    assert tx.fatura_id == esperada.id

    page = logged_in_cartao_b_page
    det = FaturaDetalhePage(page, app_base_url)
    det.open(cartao_a.id, esperada.id)
    assert f"/faturas/{esperada.id}/" in page.url


@pytest.mark.faturas_avancadas
@pytest.mark.django_db(transaction=True)
def test_e2e_fat_07_pagar_antes_vencimento(logged_in_cartao_b_page, app_base_url, persona_cartao_b):
    user = persona_cartao_b["user"]
    conta = persona_cartao_b["conta"]
    cartao_a = persona_cartao_b["cartao_a"]
    cat = persona_cartao_b["cat_despesa"]
    hoje = _hoje()
    data_compra = hoje.replace(day=min(5, hoje.day) or 1)

    tx = Transacao.objects.create(
        usuario=user, conta=conta, cartao=cartao_a, categoria=cat,
        tipo="despesa", valor=Decimal("90.00"), data=data_compra, descricao="E2E FAT-07",
    )
    fatura = tx.fatura
    assert fatura.data_vencimento > hoje

    page = logged_in_cartao_b_page
    det = FaturaDetalhePage(page, app_base_url)
    det.open(cartao_a.id, fatura.id)
    det.pagar()
    assert det.falta_pagar_ausente()


@pytest.mark.faturas_avancadas
@pytest.mark.django_db(transaction=True)
def test_e2e_fat_08_tres_pagamentos_parciais(logged_in_cartao_b_page, app_base_url, persona_cartao_b):
    user = persona_cartao_b["user"]
    conta = persona_cartao_b["conta"]
    cartao_a = persona_cartao_b["cartao_a"]
    cat = persona_cartao_b["cat_despesa"]

    tx = Transacao.objects.create(
        usuario=user, conta=conta, cartao=cartao_a, categoria=cat,
        tipo="despesa", valor=Decimal("90.00"), data=date(2026, 4, 6), descricao="E2E FAT-08",
    )
    fatura = tx.fatura

    page = logged_in_cartao_b_page
    det = FaturaDetalhePage(page, app_base_url)
    det.open(cartao_a.id, fatura.id)
    det.pagar(Decimal("30.00"))
    det.open(cartao_a.id, fatura.id)
    det.pagar(Decimal("30.00"))
    det.open(cartao_a.id, fatura.id)
    det.pagar(Decimal("30.00"))
    assert det.falta_pagar_ausente()


@pytest.mark.faturas_avancadas
@pytest.mark.django_db(transaction=True)
def test_e2e_fat_09_compra_reflete_orcamento(logged_in_cartao_b_page, app_base_url, persona_cartao_b):
    user = persona_cartao_b["user"]
    conta = persona_cartao_b["conta"]
    cartao_a = persona_cartao_b["cartao_a"]
    cat_orc = persona_cartao_b["cat_orcamento"]
    hoje = _hoje()

    Transacao.objects.create(
        usuario=user, conta=conta, cartao=cartao_a, categoria=cat_orc,
        tipo="despesa", valor=Decimal("80.00"),
        data=hoje.replace(day=min(7, hoje.day) or 1),
        descricao="E2E FAT-09 compra orc",
    )

    orc = OrcamentosPage(logged_in_cartao_b_page, app_base_url)
    orc.open()
    card = orc.card_categoria("E2E Orc Cartão")
    texto = card.inner_text()
    assert "80" in texto.replace(".", "") or "R$ 80" in texto


@pytest.mark.faturas_avancadas
@pytest.mark.django_db(transaction=True)
def test_e2e_fat_10_atraso_apos_vencimento(logged_in_cartao_b_page, app_base_url, persona_cartao_b):
    user = persona_cartao_b["user"]
    conta = persona_cartao_b["conta"]
    cartao_a = persona_cartao_b["cartao_a"]
    cat = persona_cartao_b["cat_despesa"]
    data_antiga = _hoje() - timedelta(days=120)

    tx = Transacao.objects.create(
        usuario=user, conta=conta, cartao=cartao_a, categoria=cat,
        tipo="despesa", valor=Decimal("55.00"), data=data_antiga, descricao="E2E FAT-10",
    )
    fatura = tx.fatura
    assert fatura.data_vencimento < _hoje()

    page = logged_in_cartao_b_page
    det = FaturaDetalhePage(page, app_base_url)
    det.open(cartao_a.id, fatura.id)
    assert det.indicador_atraso_presente()
