"""Testes unitários — cartões e faturas avançadas (sem HTTP)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from freezegun import freeze_time

from cartoes.models import Fatura
from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.services.gestao_faturas import (
    calcular_resumo_pagamento,
    mover_lancamento,
    pagar_fatura,
    recalcular_fatura,
)
from cartoes.tests.helpers.asserts_fatura import (
    assert_compra_cartao_consistente,
    assert_compra_nao_move_saldo,
    assert_conta_saldo,
    assert_fatura_consistente,
)
from cartoes.tests.helpers.fatura_fixtures import (
    build_cartao,
    build_cartao_par,
    datas_fronteira_fechamento,
    mesma_fatura,
    seed_compra,
    snapshot_faturas,
)
from categorias.models import Categoria
from contas.models import Conta
from financial_contracts.saldo_contracts import calcular_saldo_esperado
from transacoes.models import Transacao

User = get_user_model()


class FaturasAvancadasBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="fat-adv@test.local", password="x", nome="Fat Adv"
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user, nome="Conta FAT", tipo="corrente", ativa=True
        )
        cls.cartao = build_cartao(cls.user, cls.conta)
        cls.categoria = Categoria.objects.create(
            usuario=cls.user,
            nome="Desp FAT",
            tipo="despesa",
            cor="#EF4444",
            ativa=True,
        )


@pytest.mark.faturas_avancadas
class TestInvCiclo(FaturasAvancadasBase):
    def test_mesma_fatura_antes_e_no_fechamento(self):
        antes, fech, _ = datas_fronteira_fechamento(self.cartao)
        self.assertTrue(mesma_fatura(self.cartao, antes, fech))

    def test_fatura_diferente_apos_fechamento(self):
        _, fech, depois = datas_fronteira_fechamento(self.cartao)
        self.assertFalse(mesma_fatura(self.cartao, fech, depois))

    def test_vencimento_posterior_ao_fechamento(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        self.assertGreater(fatura.data_vencimento, fatura.data_fechamento)

    def test_status_temporal_derivado(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        self.assertEqual(
            fatura.get_status_temporal(hoje=fatura.data_inicio_compras - timedelta(days=1)),
            Fatura.StatusTemporal.FUTURA,
        )
        self.assertEqual(
            fatura.get_status_temporal(hoje=fatura.data_fim_compras),
            Fatura.StatusTemporal.ABERTA,
        )
        self.assertEqual(
            fatura.get_status_temporal(hoje=fatura.data_fim_compras + timedelta(days=1)),
            Fatura.StatusTemporal.FECHADA,
        )

    def test_faturas_distintas_por_competencia(self):
        f1 = obter_ou_criar_fatura(self.cartao, date(2026, 3, 5))
        f2 = obter_ou_criar_fatura(self.cartao, date(2026, 5, 5))
        self.assertNotEqual(f1.pk, f2.pk)


@pytest.mark.faturas_avancadas
class TestInvFatura(FaturasAvancadasBase):
    def test_pagamento_parcial_e_total(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("200.00"),
        )
        pagar_fatura(fatura=fatura, valor=Decimal("50.00"))
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PARCIAL)
        pagar_fatura(fatura=fatura)
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PAGO)
        assert_fatura_consistente(fatura)

    def test_status_atrasado(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2025, 1, 5))
        seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2025, 1, 5), valor=Decimal("30.00"),
        )
        resumo = calcular_resumo_pagamento(
            fatura, hoje=fatura.data_vencimento + timedelta(days=5)
        )
        self.assertEqual(resumo.status_pagamento, Fatura.StatusPagamento.ATRASADO)

    def test_rejeita_pagamento_maior_que_saldo(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("40.00"),
        )
        antes = Transacao.objects.filter(pagamento_de_fatura=fatura).count()
        with self.assertRaises(ValidationError):
            pagar_fatura(fatura=fatura, valor=Decimal("99.00"))
        self.assertEqual(
            Transacao.objects.filter(pagamento_de_fatura=fatura).count(), antes
        )

    def test_fatura_vazia_apos_excluir_compra(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        tx = seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("25.00"),
        )
        recalcular_fatura(fatura)
        tx.delete()
        fatura.refresh_from_db()
        resumo = recalcular_fatura(fatura)
        self.assertEqual(resumo.total, Decimal("0"))
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PENDENTE)

    def test_nova_compra_em_fatura_paga_rebaixa_status(self):
        fatura = Fatura.objects.create(
            usuario=self.user,
            cartao=self.cartao,
            competencia=date(2026, 2, 1),
            data_fechamento=date(2026, 1, 10),
            data_vencimento=date(2026, 2, 20),
            data_inicio_compras=date(2025, 12, 11),
            data_fim_compras=date(2026, 1, 10),
            status=Fatura.Status.FECHADA,
            status_ciclo=Fatura.Status.FECHADA,
            status_pagamento=Fatura.StatusPagamento.PAGO,
        )
        seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 2, 3), valor=Decimal("30.00"), descricao="Base",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("30.00"),
            descricao="Pag base",
            data=date(2026, 2, 20),
            pagamento_de_fatura=fatura,
        )
        recalcular_fatura(fatura)
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PAGO)
        seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 2, 5), valor=Decimal("10.00"), descricao="Nova",
        )
        Transacao.objects.filter(
            cartao=self.cartao, descricao="Nova"
        ).update(fatura=fatura)
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PARCIAL)

    def test_mover_para_fatura_paga_recalcula_parcial(self):
        fatura_origem = obter_ou_criar_fatura(self.cartao, date(2026, 3, 5))
        fatura_destino = Fatura.objects.create(
            usuario=self.user,
            cartao=self.cartao,
            competencia=date(2026, 2, 1),
            data_fechamento=date(2026, 1, 10),
            data_vencimento=date(2026, 2, 20),
            data_inicio_compras=date(2025, 12, 11),
            data_fim_compras=date(2026, 1, 10),
            status=Fatura.Status.FECHADA,
            status_ciclo=Fatura.Status.FECHADA,
            status_pagamento=Fatura.StatusPagamento.PAGO,
        )
        seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 2, 5), valor=Decimal("20.00"), descricao="Dest",
        )
        Transacao.objects.filter(descricao="Dest").update(fatura=fatura_destino)
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("20.00"),
            descricao="Pag dest",
            data=date(2026, 2, 20),
            pagamento_de_fatura=fatura_destino,
        )
        tx = seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 3, 5), valor=Decimal("40.00"), descricao="Mover",
        )
        Transacao.objects.filter(pk=tx.pk).update(fatura=fatura_origem)
        mover_lancamento(transacao=tx, fatura_destino=fatura_destino)
        fatura_destino.refresh_from_db()
        self.assertEqual(fatura_destino.status_pagamento, Fatura.StatusPagamento.PARCIAL)


@pytest.mark.faturas_avancadas
class TestInvCompetencia(FaturasAvancadasBase):
    def test_competencia_fatura_con_comp_01(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        assert_fatura_consistente(fatura)

    def test_data_competencia_compra_con_comp_02(self):
        tx = seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("15.00"),
        )
        assert_compra_cartao_consistente(tx)
        self.assertNotEqual(tx.data, tx.data_competencia)

    def test_mover_lancamento_preserva_competencia(self):
        fatura_origem = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        fatura_destino = Fatura.objects.create(
            usuario=self.user,
            cartao=self.cartao,
            competencia=date(2026, 6, 1),
            data_fechamento=date(2026, 5, 10),
            data_vencimento=date(2026, 6, 20),
            data_inicio_compras=date(2026, 4, 11),
            data_fim_compras=date(2026, 5, 10),
            status=Fatura.Status.FECHADA,
            status_ciclo=Fatura.Status.FECHADA,
            status_pagamento=Fatura.StatusPagamento.PENDENTE,
        )
        tx = seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("80.00"), descricao="Movel",
        )
        comp_antes = tx.data_competencia
        mover_lancamento(transacao=tx, fatura_destino=fatura_destino)
        tx.refresh_from_db()
        self.assertEqual(tx.data_competencia, comp_antes)


@pytest.mark.faturas_avancadas
class TestInvIsolamento(FaturasAvancadasBase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cartao_a, cls.cartao_b = build_cartao_par(cls.user, cls.conta)

    def test_compras_geram_faturas_distintas(self):
        d = date(2026, 4, 8)
        fa = obter_ou_criar_fatura(self.cartao_a, d)
        fb = obter_ou_criar_fatura(self.cartao_b, d)
        self.assertNotEqual(fa.cartao_id, fb.cartao_id)

    def test_pagar_a_nao_altera_b(self):
        d = date(2026, 4, 8)
        seed_compra(
            self.user, self.conta, self.cartao_a, self.categoria,
            data=d, valor=Decimal("50.00"), descricao="A",
        )
        seed_compra(
            self.user, self.conta, self.cartao_b, self.categoria,
            data=d, valor=Decimal("30.00"), descricao="B",
        )
        snap_antes = snapshot_faturas([self.cartao_b])
        fa = obter_ou_criar_fatura(self.cartao_a, d)
        pagar_fatura(fatura=fa)
        snap_depois = snapshot_faturas([self.cartao_b])
        self.assertEqual(snap_antes[self.cartao_b.pk], snap_depois[self.cartao_b.pk])


@pytest.mark.faturas_avancadas
class TestAntecipacao(FaturasAvancadasBase):
    @freeze_time("2026-04-15")
    def test_pagar_antes_vencimento(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        self.assertGreater(fatura.data_vencimento, date(2026, 4, 15))
        saldo_antes = calcular_saldo_esperado(self.conta, incluir_compras_cartao=False)
        seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("80.00"),
        )
        assert_compra_nao_move_saldo(self.conta, saldo_antes)
        pagar_fatura(fatura=fatura)
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PAGO)
        assert_conta_saldo(self.conta, saldo_antes - Decimal("80.00"))
        resumo = calcular_resumo_pagamento(fatura, hoje=date(2026, 4, 15))
        self.assertNotEqual(resumo.status_pagamento, Fatura.StatusPagamento.ATRASADO)
