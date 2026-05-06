from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao

from cartoes.models import Cartao, Fatura
from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.services.gestao_faturas import (
    atualizar_status_pagamento,
    mover_lancamento,
    pagar_fatura,
    recalcular_fatura,
)


class FaturasServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="u1@example.com",
            password="x",
            nome="Usuario Teste",
        )
        self.conta = Conta.objects.create(usuario=self.user, nome="Conta", tipo="corrente", ativa=True)
        self.cartao = Cartao.objects.create(
            usuario=self.user,
            nome="Cartao",
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

    @staticmethod
    def _first_day_shift_months(d: date, delta_months: int) -> date:
        m = d.month - 1 + delta_months
        y = d.year + m // 12
        m = m % 12 + 1
        return date(y, m, 1)

    def test_obter_ou_criar_fatura_mantem_faturas_distintas_por_competencia(self):
        hoje = timezone.localdate()
        data_mes_anterior = self._first_day_shift_months(hoje, -1)
        data_mes_atual = date(hoje.year, hoje.month, min(hoje.day, 10))
        fatura_1 = obter_ou_criar_fatura(self.cartao, data_mes_anterior)
        fatura_2 = obter_ou_criar_fatura(self.cartao, data_mes_atual)
        self.assertNotEqual(fatura_1.id, fatura_2.id)
        self.assertNotEqual(fatura_1.competencia, fatura_2.competencia)

    def test_status_temporal_derivado(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        self.assertEqual(
            fatura.get_status_temporal(hoje=fatura.data_inicio_compras),
            Fatura.StatusTemporal.ABERTA,
        )
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

    def test_pagamento_parcial_e_total_atualizam_status(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("200.00"),
            descricao="Compra",
            data=date(2026, 4, 5),
        )
        pagar_fatura(fatura=fatura, valor=Decimal("50.00"))
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PARCIAL)
        pagar_fatura(fatura=fatura)
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PAGO)

    def test_mover_lancamento_mantem_data_competencia(self):
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
        transacao = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("80.00"),
            descricao="Compra movel",
            data=date(2026, 4, 5),
        )
        data_competencia_original = transacao.data_competencia
        mover_lancamento(transacao=transacao, fatura_destino=fatura_destino)
        transacao.refresh_from_db()
        self.assertEqual(transacao.fatura_id, fatura_destino.id)
        self.assertEqual(transacao.data, date(2026, 4, 5))
        self.assertEqual(transacao.data_competencia, data_competencia_original)

    def test_fatura_vazia_recalcula_status_valores(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        transacao = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("25.00"),
            descricao="Compra teste",
            data=date(2026, 4, 5),
        )
        resumo_com_lancamento = recalcular_fatura(fatura)
        self.assertEqual(resumo_com_lancamento.total, Decimal("25.00"))

        transacao.delete()
        fatura.refresh_from_db()
        resumo_vazio = recalcular_fatura(fatura)
        self.assertEqual(resumo_vazio.total, Decimal("0"))
        self.assertEqual(resumo_vazio.pago, Decimal("0"))
        self.assertEqual(resumo_vazio.saldo, Decimal("0"))
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PENDENTE)

    def test_movimentacao_por_direcao_respeita_ordem_cronologica(self):
        self.client.force_login(self.user)
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
        transacao = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("90.00"),
            descricao="Compra marco",
            data=date(2026, 2, 5),
        )
        Transacao.objects.filter(pk=transacao.pk).update(fatura=fatura_marco)
        transacao.refresh_from_db()
        url = reverse(
            "cartoes:mover_lancamento_fatura",
            kwargs={
                "cartao_id": self.cartao.id,
                "fatura_id": fatura_marco.id,
                "transacao_id": transacao.id,
            },
        )
        resp = self.client.post(url, {"direcao": "anterior"})
        self.assertEqual(resp.status_code, 302)
        transacao.refresh_from_db()
        fatura_fevereiro.refresh_from_db()
        self.assertEqual(transacao.fatura_id, fatura_fevereiro.id)
        # Garante que não "pulou" para janeiro.
        self.assertNotEqual(transacao.fatura_id, fatura_janeiro.id)
        # Garante que destino não permaneceu "paga" após receber novo lançamento.
        self.assertNotEqual(fatura_fevereiro.status_pagamento, Fatura.StatusPagamento.PAGO)

    def test_mover_para_fatura_paga_e_permitido_com_recalculo(self):
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
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            fatura=fatura_destino,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("20.00"),
            descricao="Compra destino",
            data=date(2026, 2, 5),
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("20.00"),
            descricao="Pagamento destino",
            data=date(2026, 2, 20),
            pagamento_de_fatura=fatura_destino,
        )
        transacao = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("40.00"),
            descricao="Compra movida para paga",
            data=date(2026, 3, 5),
        )
        Transacao.objects.filter(pk=transacao.pk).update(fatura=fatura_origem)

        mover_lancamento(transacao=transacao, fatura_destino=fatura_destino)
        transacao.refresh_from_db()
        fatura_destino.refresh_from_db()
        fatura_origem.refresh_from_db()

        self.assertEqual(transacao.fatura_id, fatura_destino.id)
        # Destino paga com novo lançamento deve recalcular para parcial.
        self.assertEqual(fatura_destino.status_pagamento, Fatura.StatusPagamento.PARCIAL)

    def test_nova_transacao_em_fatura_paga_rebaixa_status(self):
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
        # Situação inicial paga: total == pago
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            fatura=fatura,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("30.00"),
            descricao="Compra base",
            data=date(2026, 2, 3),
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("30.00"),
            descricao="Pagamento base",
            data=date(2026, 2, 20),
            pagamento_de_fatura=fatura,
        )
        recalcular_fatura(fatura)
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PAGO)

        # Nova compra deve invalidar "paga" e virar "parcial".
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            fatura=fatura,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("10.00"),
            descricao="Nova compra",
            data=date(2026, 2, 5),
        )
        fatura.refresh_from_db()
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PARCIAL)

    def test_mover_proxima_cria_fatura_quando_so_existe_atual(self):
        self.client.force_login(self.user)
        fatura_unica = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        transacao = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("15.00"),
            descricao="Compra abril",
            data=date(2026, 4, 5),
        )
        self.assertEqual(transacao.fatura_id, fatura_unica.id)
        self.assertEqual(Fatura.objects.filter(cartao=self.cartao).count(), 1)

        url = reverse(
            "cartoes:mover_lancamento_fatura",
            kwargs={
                "cartao_id": self.cartao.id,
                "fatura_id": fatura_unica.id,
                "transacao_id": transacao.id,
            },
        )
        resp = self.client.post(url, {"direcao": "proxima"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Fatura.objects.filter(cartao=self.cartao).count(), 2)
        transacao.refresh_from_db()
        self.assertNotEqual(transacao.fatura_id, fatura_unica.id)
        self.assertGreater(transacao.fatura.competencia, fatura_unica.competencia)

    def test_mover_anterior_cria_fatura_quando_so_existe_atual(self):
        self.client.force_login(self.user)
        fatura_unica = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        transacao = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.categoria,
            tipo="despesa",
            valor=Decimal("15.00"),
            descricao="Compra abril",
            data=date(2026, 4, 5),
        )
        self.assertEqual(transacao.fatura_id, fatura_unica.id)

        url = reverse(
            "cartoes:mover_lancamento_fatura",
            kwargs={
                "cartao_id": self.cartao.id,
                "fatura_id": fatura_unica.id,
                "transacao_id": transacao.id,
            },
        )
        resp = self.client.post(url, {"direcao": "anterior"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Fatura.objects.filter(cartao=self.cartao).count(), 2)
        transacao.refresh_from_db()
        self.assertNotEqual(transacao.fatura_id, fatura_unica.id)
        self.assertLess(transacao.fatura.competencia, fatura_unica.competencia)

