from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from cartoes.models import Cartao, Fatura
from cartoes.services.faturas import obter_ou_criar_fatura
from cartoes.services.gestao_faturas import pagar_fatura
from categorias.models import Categoria
from contas.models import Conta
from financial_contracts.base import quantize_moeda
from financial_contracts.competencia_contracts import (
    assert_competencia_cartao_vencimento,
    assert_data_competencia_em_fatura,
)
from financial_contracts.fatura_contracts import (
    assert_fatura_saldo,
    assert_fatura_total,
    assert_status_fatura_coerente,
)
from financial_contracts.saldo_contracts import (
    assert_compra_cartao_nao_altera_saldo_conta,
    assert_saldo_conta,
    calcular_saldo_esperado,
)
from relatorios.services.filtros import RelatorioFiltros
from relatorios.services.orcamentos import listar_orcamentos_mes
from transacoes.models import Transacao

User = get_user_model()


class SaldoContractsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="c@t.com", nome="C", password="x")
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta", tipo="corrente", ativa=True
        )
        self.cat = Categoria.objects.create(
            usuario=self.user,
            nome="Alim",
            tipo="despesa",
            ativa=True,
            padrao=False,
            cor="#000",
            icone="fa-tag",
        )

    def test_con_saldo_01_receita_despesa(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat,
            tipo="receita",
            valor=Decimal("1000.00"),
            data=date(2026, 5, 1),
            descricao="salario",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("250.00"),
            data=date(2026, 5, 2),
            descricao="mercado",
        )
        assert_saldo_conta(self.conta, Decimal("750.00"))
        self.assertEqual(calcular_saldo_esperado(self.conta), Decimal("750.00"))


class FaturaContractsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="f@t.com", nome="F", password="x")
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta", tipo="corrente", ativa=True
        )
        self.cartao = Cartao.objects.create(
            usuario=self.user,
            nome="Visa",
            dia_fechamento=10,
            dia_vencimento=20,
            conta_padrao=self.conta,
            ativa=True,
        )
        self.cat, _ = Categoria.objects.get_or_create(
            usuario=self.user,
            nome="Compras Contrato FAT",
            tipo="despesa",
            defaults={
                "ativa": True,
                "padrao": False,
                "cor": "#000",
                "icone": "fa-tag",
            },
        )

    def test_con_fat_01_e_02_pagamento_parcial(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 4, 5))
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("200.00"),
            data=date(2026, 4, 5),
            descricao="Compra",
        )
        fatura.refresh_from_db()
        assert_fatura_total(fatura)
        assert_fatura_saldo(fatura)
        pagar_fatura(fatura=fatura, valor=Decimal("50.00"))
        fatura.refresh_from_db()
        assert_fatura_saldo(fatura)
        assert_status_fatura_coerente(fatura)
        self.assertEqual(fatura.status_pagamento, Fatura.StatusPagamento.PARCIAL)

    def test_con_saldo_04_compra_cartao(self):
        saldo_antes = calcular_saldo_esperado(self.conta, incluir_compras_cartao=False)
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("99.00"),
            data=date(2026, 4, 5),
            descricao="Cartao",
        )
        assert_compra_cartao_nao_altera_saldo_conta(self.conta, saldo_antes)


class CompetenciaContractsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="comp@t.com", nome="Comp", password="x")
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta", tipo="corrente", ativa=True
        )
        self.cartao = Cartao.objects.create(
            usuario=self.user,
            nome="Master",
            dia_fechamento=5,
            dia_vencimento=12,
            conta_padrao=self.conta,
            ativa=True,
        )
        self.cat = Categoria.objects.create(
            usuario=self.user,
            nome="Loja",
            tipo="despesa",
            ativa=True,
            padrao=False,
            cor="#000",
            icone="fa-tag",
        )

    def test_con_comp_01_e_02(self):
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("50.00"),
            data=date(2026, 5, 3),
            descricao="Compra maio",
        )
        tx.refresh_from_db()
        assert_data_competencia_em_fatura(tx)
        assert_competencia_cartao_vencimento(tx.fatura)


class DecimalContractsTests(TestCase):
    def test_dec_02_decimal_aritmetica(self):
        self.assertEqual(
            quantize_moeda(Decimal("0.1") + Decimal("0.2")),
            Decimal("0.30"),
        )

    def test_dec_01_mil_microtransacoes(self):
        user = User.objects.create_user(email="micro@t.com", nome="M", password="x")
        conta = Conta.objects.create(usuario=user, nome="C", tipo="corrente", ativa=True)
        cat = Categoria.objects.create(
            usuario=user,
            nome="Micro",
            tipo="despesa",
            ativa=True,
            padrao=False,
            cor="#000",
            icone="fa-tag",
        )
        for _ in range(1000):
            Transacao.objects.create(
                usuario=user,
                conta=conta,
                categoria=cat,
                tipo="receita",
                valor=Decimal("0.01"),
                data=date(2026, 5, 1),
                descricao="centavo",
            )
        assert_saldo_conta(conta, Decimal("10.00"))


class OrcamentoContractsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="orc@t.com", nome="O", password="x")
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta", tipo="corrente", ativa=True
        )
        self.cartao = Cartao.objects.create(
            usuario=self.user,
            nome="Card",
            dia_fechamento=10,
            dia_vencimento=20,
            conta_padrao=self.conta,
            ativa=True,
        )
        self.cat = Categoria.objects.create(
            usuario=self.user,
            nome="Alimentacao",
            tipo="despesa",
            ativa=True,
            padrao=False,
            cor="#000",
            icone="fa-tag",
        )
        from datetime import datetime

        from django.utils import timezone

        from relatorios.models import OrcamentoCategoria

        o = OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("500.00"),
            ativo=True,
        )
        OrcamentoCategoria.objects.filter(pk=o.pk).update(
            criado_em=timezone.make_aware(datetime(2026, 1, 1, 12, 0, 0))
        )

    def test_con_orc_01_pagamento_fatura_excluido(self):
        fatura = obter_ou_criar_fatura(self.cartao, date(2026, 5, 5))
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=self.cartao,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("100.00"),
            data=date(2026, 5, 5),
            descricao="Compra",
        )
        pagar_fatura(fatura=fatura, valor=Decimal("100.00"))
        linhas = listar_orcamentos_mes(self.user, 2026, 5)
        alim = next(l for l in linhas if l.categoria_id == self.cat.id)
        self.assertEqual(alim.realizado, Decimal("100.00"))
        from financial_contracts.orcamento_contracts import assert_pagamento_excluido_do_realizado

        filtros = RelatorioFiltros(
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        assert_pagamento_excluido_do_realizado(self.user, self.cat, filtros)
