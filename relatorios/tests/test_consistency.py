"""REL-FLX-*, REL-CAT-*, REL-CTA-* — consistência analítica."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from categorias.models import Categoria
from contas.models import Conta
from relatorios.services.despesas_categoria import montar_analise_despesas_categoria
from relatorios.services.filtros import RelatorioFiltros
from relatorios.services.por_conta import montar_analise_por_conta
from relatorios.tests.helpers.consistency import (
    assert_resultado_receitas_menos_despesas,
    assert_totais_filtrados,
)
from transacoes.models import Transacao
from transacoes.services import criar_transacao_saldo_inicial

User = get_user_model()


class RelAnaliticoConsistencyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="rel-flx@test.local", nome="Rel Flx", password="x"
        )
        self.conta_a = Conta.objects.create(
            usuario=self.user, nome="Conta A", ativa=True
        )
        self.conta_b = Conta.objects.create(
            usuario=self.user, nome="Conta B", ativa=True
        )
        self.cat_rec = Categoria.objects.create(
            usuario=self.user, nome="Rec", tipo="receita", ativa=True, cor="#10B981"
        )
        self.cat_desp = Categoria.objects.create(
            usuario=self.user, nome="Desp", tipo="despesa", ativa=True, cor="#EF4444"
        )
        self.hoje = timezone.localdate()
        self.filtros = RelatorioFiltros(
            data_inicio=self.hoje.replace(day=1),
            data_fim=self.hoje,
            preset="custom",
        )

    def test_rel_flx_01_totais_periodo(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("100.00"),
            data=self.hoje,
            descricao="R",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("40.00"),
            data=self.hoje,
            descricao="D",
        )
        tot = assert_totais_filtrados(self.user, self.filtros)
        assert_resultado_receitas_menos_despesas(tot)
        self.assertEqual(tot["receitas"], Decimal("100.00"))
        self.assertEqual(tot["despesas"], Decimal("40.00"))

    def test_rel_flx_02_filtro_conta(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("50.00"),
            data=self.hoje,
            descricao="A",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_b,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("25.00"),
            data=self.hoje,
            descricao="B",
        )
        filtros = RelatorioFiltros(
            data_inicio=self.filtros.data_inicio,
            data_fim=self.filtros.data_fim,
            conta_ids=(self.conta_a.id,),
            preset="custom",
        )
        tot = assert_totais_filtrados(self.user, filtros)
        self.assertEqual(tot["despesas"], Decimal("50.00"))

    def test_rel_flx_03_filtro_somente_despesa(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("100.00"),
            data=self.hoje,
            descricao="R",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("30.00"),
            data=self.hoje,
            descricao="D",
        )
        filtros = RelatorioFiltros(
            data_inicio=self.filtros.data_inicio,
            data_fim=self.filtros.data_fim,
            tipos=("despesa",),
            preset="custom",
        )
        tot = assert_totais_filtrados(self.user, filtros)
        self.assertEqual(tot["receitas"], Decimal("0"))
        self.assertEqual(tot["despesas"], Decimal("30.00"))

    def test_rel_cat_01_soma_categorias(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("60.00"),
            data=self.hoje,
            descricao="D1",
        )
        analise = montar_analise_despesas_categoria(self.user, self.filtros)
        self.assertEqual(analise["hero"].total_despesas, Decimal("60.00"))

    def test_rel_cta_01_movimento_e_patrimonio(self):
        criar_transacao_saldo_inicial(
            self.user, self.conta_a, Decimal("500.00"), self.filtros.data_inicio
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta_a,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("50.00"),
            data=self.hoje,
            descricao="Mov",
        )
        analise = montar_analise_por_conta(self.user, self.filtros)
        self.assertEqual(analise["hero"].patrimonio_total, Decimal("450.00"))
