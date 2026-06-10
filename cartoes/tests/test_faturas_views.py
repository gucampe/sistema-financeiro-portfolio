"""Smoke HTTP — views de faturas (mover lançamento, links)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from cartoes.models import Fatura
from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.tests.helpers.fatura_fixtures import build_cartao, seed_compra
from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao

User = get_user_model()


@pytest.mark.faturas_avancadas
@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class FaturasViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="faturas-view@test.local", password="x", nome="Usuario Views"
        )
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta", tipo="corrente", ativa=True
        )
        self.cartao = build_cartao(self.user, self.conta)
        self.categoria = Categoria.objects.create(
            usuario=self.user,
            nome="Alimentacao",
            tipo="despesa",
            ativa=True,
            cor="#4B5563",
        )
        self.client.force_login(self.user)

    def test_ver_lancamentos_aponta_para_fatura_detalhe(self):
        fatura = obter_ou_criar_fatura(self.cartao, timezone.localdate())
        url_faturas = reverse("cartoes:faturas", kwargs={"cartao_id": self.cartao.id})
        url_detalhe = reverse(
            "cartoes:fatura_detalhe",
            kwargs={"cartao_id": self.cartao.id, "fatura_id": fatura.id},
        )
        resp = self.client.get(url_faturas)
        self.assertEqual(resp.status_code, 200)
        links = re.findall(r'href="([^"]+)"[^>]*>\s*Ver lan', resp.content.decode())
        self.assertEqual(links, [url_detalhe])
        self.assertNotIn("/transacoes/", links[0])

    def test_movimentacao_por_direcao_respeita_ordem_cronologica(self):
        fatura_janeiro = Fatura.objects.create(
            usuario=self.user,
            cartao=self.cartao,
            competencia=date(2026, 1, 1),
            data_fechamento=date(2025, 12, 10),
            data_vencimento=date(2026, 1, 20),
            data_inicio_compras=date(2025, 11, 11),
            data_fim_compras=date(2025, 12, 10),
            status=Fatura.Status.FECHADA,
            status_ciclo=Fatura.Status.FECHADA,
            status_pagamento=Fatura.StatusPagamento.PENDENTE,
        )
        fatura_fevereiro = Fatura.objects.create(
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
        fatura_marco = Fatura.objects.create(
            usuario=self.user,
            cartao=self.cartao,
            competencia=date(2026, 3, 1),
            data_fechamento=date(2026, 2, 10),
            data_vencimento=date(2026, 3, 20),
            data_inicio_compras=date(2026, 1, 11),
            data_fim_compras=date(2026, 2, 10),
            status=Fatura.Status.ABERTA,
            status_ciclo=Fatura.Status.ABERTA,
            status_pagamento=Fatura.StatusPagamento.PENDENTE,
        )
        tx = seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 2, 5), valor=Decimal("90.00"), descricao="Compra marco",
        )
        Transacao.objects.filter(pk=tx.pk).update(fatura=fatura_marco)
        tx.refresh_from_db()
        url = reverse(
            "cartoes:mover_lancamento_fatura",
            kwargs={
                "cartao_id": self.cartao.id,
                "fatura_id": fatura_marco.id,
                "transacao_id": tx.id,
            },
        )
        resp = self.client.post(url, {"direcao": "anterior"})
        self.assertEqual(resp.status_code, 302)
        tx.refresh_from_db()
        fatura_fevereiro.refresh_from_db()
        self.assertEqual(tx.fatura_id, fatura_fevereiro.id)
        self.assertNotEqual(tx.fatura_id, fatura_janeiro.id)
        self.assertNotEqual(
            fatura_fevereiro.status_pagamento, Fatura.StatusPagamento.PAGO
        )

    def test_mover_proxima_cria_fatura_quando_so_existe_atual(self):
        fatura_unica = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        tx = seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("15.00"), descricao="Compra abril",
        )
        self.assertEqual(tx.fatura_id, fatura_unica.id)
        self.assertEqual(Fatura.objects.filter(cartao=self.cartao).count(), 1)
        url = reverse(
            "cartoes:mover_lancamento_fatura",
            kwargs={
                "cartao_id": self.cartao.id,
                "fatura_id": fatura_unica.id,
                "transacao_id": tx.id,
            },
        )
        resp = self.client.post(url, {"direcao": "proxima"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Fatura.objects.filter(cartao=self.cartao).count(), 2)
        tx.refresh_from_db()
        self.assertNotEqual(tx.fatura_id, fatura_unica.id)
        self.assertGreater(tx.fatura.competencia, fatura_unica.competencia)

    def test_mover_anterior_cria_fatura_quando_so_existe_atual(self):
        fatura_unica = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        tx = seed_compra(
            self.user, self.conta, self.cartao, self.categoria,
            data=date(2026, 4, 5), valor=Decimal("15.00"), descricao="Compra abril",
        )
        url = reverse(
            "cartoes:mover_lancamento_fatura",
            kwargs={
                "cartao_id": self.cartao.id,
                "fatura_id": fatura_unica.id,
                "transacao_id": tx.id,
            },
        )
        resp = self.client.post(url, {"direcao": "anterior"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Fatura.objects.filter(cartao=self.cartao).count(), 2)
        tx.refresh_from_db()
        self.assertNotEqual(tx.fatura_id, fatura_unica.id)
        self.assertLess(tx.fatura.competencia, fatura_unica.competencia)
