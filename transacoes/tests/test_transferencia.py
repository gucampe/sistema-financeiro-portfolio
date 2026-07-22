"""Testes de domínio: transferência entre contas (dupla partida + transfer_id)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from contas.models import Conta
from financial_contracts.saldo_contracts import assert_patrimonio_contas, assert_saldo_conta
from transacoes.models import Transacao
from transacoes.services import (
    atualizar_transferencia,
    criar_transferencia,
    excluir_transferencia,
    obter_par_transferencia,
)

User = get_user_model()


class TransferenciaServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="transf@test.local", password="x", nome="Transf"
        )
        self.conta_a = Conta.objects.create(
            usuario=self.user, nome="Conta A", tipo="corrente", ativa=True
        )
        self.conta_b = Conta.objects.create(
            usuario=self.user, nome="Conta B", tipo="poupanca", ativa=True
        )
        # Saldo inicial via receita
        from categorias.models import Categoria

        self.cat, _ = Categoria.objects.get_or_create(
            usuario=self.user,
            nome="Salário",
            tipo="receita",
            defaults={"ativa": True},
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            tipo="receita",
            valor=Decimal("1000.00"),
            descricao="Saldo base",
            data=date(2026, 1, 1),
            categoria=self.cat,
        )

    def test_cria_duas_pernas_mesmo_transfer_id(self):
        tx_o, tx_d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("250.00"),
            data=date(2026, 1, 10),
            descricao="Para poupança",
        )
        self.assertEqual(tx_o.tipo, "transferencia")
        self.assertEqual(tx_d.tipo, "transferencia")
        self.assertEqual(tx_o.transfer_id, tx_d.transfer_id)
        self.assertIsNotNone(tx_o.transfer_id)
        self.assertEqual(tx_o.papel_transferencia, "origem")
        self.assertEqual(tx_d.papel_transferencia, "destino")
        self.assertEqual(tx_o.conta_id, self.conta_a.id)
        self.assertEqual(tx_d.conta_id, self.conta_b.id)

        assert_saldo_conta(self.conta_a, Decimal("750.00"))
        assert_saldo_conta(self.conta_b, Decimal("250.00"))
        assert_patrimonio_contas(self.user, Decimal("1000.00"))

    def test_rejeita_mesma_conta(self):
        with self.assertRaises(ValidationError):
            criar_transferencia(
                self.user,
                conta_origem=self.conta_a,
                conta_destino=self.conta_a,
                valor=Decimal("10.00"),
                data=date(2026, 1, 10),
            )

    def test_excluir_remove_ambas_pelo_transfer_id(self):
        tx_o, _tx_d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("100.00"),
            data=date(2026, 1, 10),
        )
        tid = tx_o.transfer_id
        excluir_transferencia(self.user, tid)
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, transfer_id=tid).count(), 0
        )
        assert_saldo_conta(self.conta_a, Decimal("1000.00"))
        assert_saldo_conta(self.conta_b, Decimal("0.00"))
        assert_patrimonio_contas(self.user, Decimal("1000.00"))

    def test_atualizar_propaga_valor_e_contas(self):
        tx_o, tx_d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("100.00"),
            data=date(2026, 1, 10),
        )
        conta_c = Conta.objects.create(
            usuario=self.user, nome="Conta C", tipo="carteira", ativa=True
        )
        atualizar_transferencia(
            self.user,
            tx_o.transfer_id,
            conta_origem=self.conta_a,
            conta_destino=conta_c,
            valor=Decimal("300.00"),
            descricao="Atualizada",
        )
        o2, d2 = obter_par_transferencia(self.user, tx_o.transfer_id)
        self.assertEqual(o2.valor, Decimal("300.00"))
        self.assertEqual(d2.valor, Decimal("300.00"))
        self.assertEqual(d2.conta_id, conta_c.id)
        self.assertEqual(o2.descricao, "Atualizada")
        self.assertEqual(d2.descricao, "Atualizada")
        assert_saldo_conta(self.conta_a, Decimal("700.00"))
        assert_saldo_conta(self.conta_b, Decimal("0.00"))
        assert_saldo_conta(conta_c, Decimal("300.00"))
        assert_patrimonio_contas(self.user, Decimal("1000.00"))

    def test_contraparte_via_transfer_id(self):
        tx_o, tx_d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("50.00"),
            data=date(2026, 1, 10),
        )
        self.assertEqual(tx_o.contraparte().pk, tx_d.pk)
        self.assertEqual(tx_d.contraparte().pk, tx_o.pk)


class TransferenciaViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="transf-view@test.local", password="x", nome="View"
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.conta_a = Conta.objects.create(
            usuario=self.user, nome="Origem", tipo="corrente", ativa=True
        )
        self.conta_b = Conta.objects.create(
            usuario=self.user, nome="Destino", tipo="poupanca", ativa=True
        )

    def test_post_transferir_cria_par(self):
        url = reverse("transacoes:transferir")
        resp = self.client.post(
            url,
            {
                "conta_origem": self.conta_a.id,
                "conta_destino": self.conta_b.id,
                "valor": "150,00",
                "data": "2026-01-15",
                "descricao": "Pix interno",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertTrue(data["transfer_id"])
        self.assertEqual(
            Transacao.objects.filter(
                usuario=self.user, transfer_id=data["transfer_id"]
            ).count(),
            2,
        )
        assert_saldo_conta(self.conta_a, Decimal("-150.00"))
        assert_saldo_conta(self.conta_b, Decimal("150.00"))
        assert_patrimonio_contas(self.user, Decimal("0.00"))

    def test_excluir_uma_perna_remove_par(self):
        tx_o, _tx_d = criar_transferencia(
            self.user,
            conta_origem=self.conta_a,
            conta_destino=self.conta_b,
            valor=Decimal("40.00"),
            data=date(2026, 1, 10),
        )
        tid = tx_o.transfer_id
        resp = self.client.post(
            reverse("transacoes:excluir", args=[tx_o.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Transacao.objects.filter(usuario=self.user, transfer_id=tid).count(), 0
        )
