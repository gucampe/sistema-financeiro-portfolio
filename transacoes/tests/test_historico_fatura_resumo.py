"""Histórico agrega compras de fatura em uma linha na data de vencimento."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao

from cartoes.models import Cartao
from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.services.gestao_faturas import pagar_fatura


class HistoricoResumoFaturaTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="hist@example.com",
            password="x",
            nome="User Hist",
        )
        self.conta = Conta.objects.create(usuario=self.user, nome="Conta", tipo="corrente", ativa=True)
        self.cartao = Cartao.objects.create(
            usuario=self.user,
            nome="Cartao Hist",
            dia_fechamento=10,
            dia_vencimento=20,
            conta_padrao=self.conta,
            ativa=True,
        )
        self.categoria = Categoria.objects.create(
            usuario=self.user,
            nome="Alimentacao",
            tipo="despesa",
            ativa=True,
            padrao=False,
            cor="#4B5563",
            icone="fa-utensils",
        )

    def test_compras_nao_aparecem_e_resumo_no_mes_do_vencimento(self):
        self.client.force_login(self.user)
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        desc_compra = "Descricao unica compra XYZ"
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("42.50"),
            descricao=desc_compra,
            data=date(2026, 4, 5),
        )

        y, m = fatura.data_vencimento.year, fatura.data_vencimento.month
        url = f"{reverse('transacoes:historico')}?ano={y}&mes={m}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Fatura ")
        self.assertNotContains(resp, "Pagamento da fatura")
        self.assertNotContains(resp, desc_compra)

    def test_rodape_soma_valor_da_fatura_apenas_quando_paga(self):
        self.client.force_login(self.user)
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("100.00"),
            descricao="Compra A",
            data=date(2026, 4, 5),
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("30.00"),
            descricao="Compra B",
            data=date(2026, 4, 6),
        )

        y, m = fatura.data_vencimento.year, fatura.data_vencimento.month
        url = f"{reverse('transacoes:historico')}?ano={y}&mes={m}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_despesas"], Decimal("0"))

        pagar_fatura(fatura=fatura)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["total_despesas"], Decimal("130"))
        self.assertContains(resp, "Pagamento da fatura")
        self.assertContains(resp, "R$ 130,00")
