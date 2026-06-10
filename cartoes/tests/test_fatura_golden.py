"""
Golden — fluxo integrado curto de faturas (2 cartões, assert só no final).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase
from freezegun import freeze_time

from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.services.gestao_faturas import pagar_fatura
from cartoes.tests.helpers.asserts_fatura import (
    assert_compra_cartao_consistente,
    assert_conta_saldo,
    assert_fatura_consistente,
)
from cartoes.tests.helpers.fatura_fixtures import (
    build_cartao_par,
    datas_fronteira_fechamento,
    seed_compra,
    snapshot_faturas,
)
from categorias.models import Categoria
from contas.models import Conta
from financial_contracts.saldo_contracts import calcular_saldo_esperado
from transacoes.models import Transacao

User = get_user_model()


@pytest.mark.faturas_avancadas
class FaturaGoldenTest(TestCase):
    """Setup → fluxo → assert final (sem asserts intermediários)."""

    def test_fluxo_dois_cartoes_pagamentos_e_competencia(self):
        # --- 1. Setup ---
        user = User.objects.create_user(
            email="golden-fat@test.local", password="x", nome="Golden FAT"
        )
        conta = Conta.objects.create(
            usuario=user, nome="Conta Golden", tipo="corrente", ativa=True
        )
        cartao_a, cartao_b = build_cartao_par(user, conta)
        categoria = Categoria.objects.create(
            usuario=user, nome="Desp Golden", tipo="despesa", cor="#111", ativa=True
        )
        saldo_inicial = calcular_saldo_esperado(conta, incluir_compras_cartao=False)
        snap_vazio_a = snapshot_faturas([cartao_a])
        snap_vazio_b = snapshot_faturas([cartao_b])

        # --- 2. Fluxo ---
        antes_a, fech_a, depois_a = datas_fronteira_fechamento(cartao_a)
        seed_compra(
            user, conta, cartao_a, categoria,
            data=antes_a, valor=Decimal("60.00"), descricao="A antes fech",
        )
        seed_compra(
            user, conta, cartao_a, categoria,
            data=fech_a, valor=Decimal("40.00"), descricao="A no fech",
        )
        seed_compra(
            user, conta, cartao_a, categoria,
            data=depois_a, valor=Decimal("20.00"), descricao="A apos fech",
        )
        fatura_a_parcial = obter_ou_criar_fatura(cartao_a, antes_a)
        pagar_fatura(fatura=fatura_a_parcial, valor=Decimal("50.00"))

        seed_compra(
            user, conta, cartao_b, categoria,
            data=date(2026, 4, 8), valor=Decimal("100.00"), descricao="B compra",
        )
        fatura_b = obter_ou_criar_fatura(cartao_b, date(2026, 4, 8))
        with freeze_time("2026-04-15"):
            pagar_fatura(fatura=fatura_b)

        fatura_b.refresh_from_db()
        with self.assertRaises(ValidationError):
            pagar_fatura(fatura=fatura_b)

        # --- 3. Assert final ---
        fatura_a_parcial.refresh_from_db()
        fatura_b.refresh_from_db()
        assert_fatura_consistente(fatura_a_parcial)
        assert_fatura_consistente(fatura_b)

        for tx in Transacao.objects.filter(cartao__in=[cartao_a, cartao_b], pagamento_de_fatura__isnull=True):
            assert_compra_cartao_consistente(tx)

        total_pago = (
            Transacao.objects.filter(
                usuario=user, pagamento_de_fatura__isnull=False
            ).aggregate(s=models.Sum("valor"))["s"]
            or Decimal("0")
        )
        assert_conta_saldo(conta, saldo_inicial - total_pago)

        snap_final_a = snapshot_faturas([cartao_a])
        snap_final_b = snapshot_faturas([cartao_b])
        self.assertEqual(len(snap_vazio_a[cartao_a.pk]), 0)
        self.assertEqual(len(snap_vazio_b[cartao_b.pk]), 0)
        self.assertGreater(len(snap_final_a[cartao_a.pk]), 0)
        self.assertGreater(len(snap_final_b[cartao_b.pk]), 0)
