"""UNIT-DASH-01..08 — KPIs da Visão Geral (kpi_home)."""

from __future__ import annotations

import calendar
import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cartoes.models import Cartao
from categorias.models import Categoria
from contas.models import Conta
from relatorios.services.agregacoes import saldos_por_conta_totais
from relatorios.services.dashboard import contas_dashboard, top_despesas_mes_atual
from relatorios.services.filtros import parse_relatorio_filtros
from financial_contracts.saldo_contracts import (
    assert_compra_cartao_nao_altera_saldo_conta,
    calcular_saldo_esperado,
)
from relatorios.tests.helpers.consistency import assert_totais_filtrados
from relatorios.tests.helpers.kpi_home import kpi_home
from transacoes.models import Transacao
from transacoes.services import criar_transacao_saldo_inicial
from usuarios.models import Perfil

User = get_user_model()


class UnitDashTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="unit-dash@test.local", nome="Unit Dash", password="x"
        )
        self.conta = Conta.objects.create(
            usuario=self.user, nome="Conta A", tipo="corrente", ativa=True
        )
        self.conta_b = Conta.objects.create(
            usuario=self.user, nome="Conta B", tipo="poupanca", ativa=True
        )
        self.cat_rec, _ = Categoria.objects.get_or_create(
            usuario=self.user,
            nome="Unit Dash Receita",
            tipo="receita",
            defaults={"ativa": True, "cor": "#10B981"},
        )
        self.cat_desp, _ = Categoria.objects.get_or_create(
            usuario=self.user,
            nome="Unit Dash Despesa",
            tipo="despesa",
            defaults={"ativa": True, "cor": "#EF4444"},
        )
        self.hoje = timezone.localdate()
        self.inicio_mes = self.hoje.replace(day=1)

    def test_unit_dash_01_totais_mes_atual(self):
        """Receitas/despesas só no mês atual; TX fora do mês ignorada."""
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("100.00"),
            data=self.inicio_mes,
            descricao="R1",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("50.00"),
            data=self.hoje,
            descricao="R2",
        )
        fora = (
            self.inicio_mes.replace(month=1, day=15)
            if self.hoje.month > 1
            else date(self.hoje.year - 1, 12, 15)
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("999.00"),
            data=fora,
            descricao="Fora",
        )
        kpi = kpi_home(self.user)
        self.assertEqual(kpi["receitas"], Decimal("150.00"))

    def test_unit_dash_02_equivalencia_este_mes(self):
        """kpi_home totais == preset este_mes."""
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("200.00"),
            data=self.hoje,
            descricao="R",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("75.00"),
            data=self.hoje,
            descricao="D",
        )
        kpi = kpi_home(self.user)
        q = QueryDict(mutable=True)
        q["preset"] = "este_mes"
        filtros = parse_relatorio_filtros(q, usuario=self.user)
        tot = assert_totais_filtrados(self.user, filtros)
        self.assertEqual(kpi["receitas"], tot["receitas"])
        self.assertEqual(kpi["despesas"], tot["despesas"])
        self.assertEqual(kpi["resultado"], tot["receitas"] - tot["despesas"])

    def test_unit_dash_03_filtros_url_nao_afetam_kpi(self):
        """kpi_home (mês calendário) não muda só por parsear URL — baseline isolado."""
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("300.00"),
            data=self.hoje,
            descricao="Mes",
        )
        antes = kpi_home(self.user)
        q = QueryDict(mutable=True)
        q["preset"] = "ultimos_90d"
        parse_relatorio_filtros(q, usuario=self.user)
        depois = kpi_home(self.user)
        self.assertEqual(antes["receitas"], depois["receitas"])
        self.assertEqual(antes["despesas"], depois["despesas"])

    def test_unit_dash_03b_contexto_respeita_filtros(self):
        """montar_contexto_dashboard aplica período/conta dos filtros."""
        from relatorios.services.dashboard_context import montar_contexto_dashboard

        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("100.00"),
            data=self.hoje,
            descricao="Mes atual",
        )
        fora = self.inicio_mes - timedelta(days=5)
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("400.00"),
            data=fora,
            descricao="Fora do mes",
        )
        q = QueryDict(mutable=True)
        q["preset"] = "este_mes"
        filtros_mes = parse_relatorio_filtros(q, usuario=self.user)
        ctx_mes = montar_contexto_dashboard(self.user, filtros=filtros_mes)
        self.assertEqual(ctx_mes["totais_mes"]["receitas"], Decimal("100.00"))

        q90 = QueryDict(mutable=True)
        q90["preset"] = "ultimos_90d"
        filtros_90 = parse_relatorio_filtros(q90, usuario=self.user)
        ctx_90 = montar_contexto_dashboard(self.user, filtros=filtros_90)
        self.assertEqual(ctx_90["totais_mes"]["receitas"], Decimal("500.00"))
        self.assertNotEqual(ctx_mes["rotulo_periodo"], ctx_90["rotulo_periodo"])

    def test_unit_dash_04_comparativo_mes_anterior(self):
        """delta_pct correto; None se anterior zerado; jan usa dez/ano-1."""
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("150.00"),
            data=self.hoje,
            descricao="Atual",
        )
        comp = kpi_home(self.user)["comparacao"]
        self.assertIsNone(comp["delta_pct_receitas"])

        if self.hoje.month == 1:
            ant_ano, ant_mes = self.hoje.year - 1, 12
        else:
            ant_ano, ant_mes = self.hoje.year, self.hoje.month - 1
        dia_ant = min(15, calendar.monthrange(ant_ano, ant_mes)[1])
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("100.00"),
            data=date(ant_ano, ant_mes, dia_ant),
            descricao="Anterior",
        )
        comp = kpi_home(self.user)["comparacao"]
        self.assertEqual(comp["delta_pct_receitas"], Decimal("50.00"))

        fake_hoje = date(2026, 1, 20)
        with patch("relatorios.services.dashboard.timezone.localdate", return_value=fake_hoje):
            u2 = User.objects.create_user(email="jan@test.local", nome="Jan", password="x")
            c2 = Conta.objects.create(usuario=u2, nome="C", ativa=True)
            cr, _ = Categoria.objects.get_or_create(
                usuario=u2, nome="Rec Jan", tipo="receita", defaults={"ativa": True, "cor": "#10B981"}
            )
            Transacao.objects.create(
                usuario=u2, conta=c2, categoria=cr, tipo="receita",
                valor=Decimal("80.00"), data=date(2026, 1, 10), descricao="Jan",
            )
            Transacao.objects.create(
                usuario=u2, conta=c2, categoria=cr, tipo="receita",
                valor=Decimal("40.00"), data=date(2025, 12, 10), descricao="Dez",
            )
            comp_jan = kpi_home(u2)["comparacao"]
            self.assertEqual(comp_jan["anterior"]["receitas"], Decimal("40.00"))
            self.assertEqual(comp_jan["delta_pct_receitas"], Decimal("100.00"))

    def test_unit_dash_05_patrimonio_multi_conta(self):
        """Patrimônio agrega saldos; limit=5 não altera total."""
        criar_transacao_saldo_inicial(
            self.user, self.conta, Decimal("1000.00"), self.inicio_mes
        )
        criar_transacao_saldo_inicial(
            self.user, self.conta_b, Decimal("500.00"), self.inicio_mes
        )
        _, total_servico = saldos_por_conta_totais(self.user)
        kpi = kpi_home(self.user)
        self.assertEqual(kpi["patrimonio"], total_servico)
        self.assertEqual(kpi["patrimonio"], Decimal("1500.00"))
        dash_limit = contas_dashboard(self.user, limit=1)
        self.assertEqual(dash_limit["patrimonio_total"], total_servico)

    def test_unit_dash_06_resultado_e_top_despesas(self):
        """resultado == receitas - despesas; sum(top) == despesas."""
        for nome, val in [("A", "40"), ("B", "30"), ("C", "30")]:
            cat = Categoria.objects.create(
                usuario=self.user,
                nome=f"Cat {nome}",
                tipo="despesa",
                ativa=True,
                cor="#6366f1",
            )
            Transacao.objects.create(
                usuario=self.user,
                conta=self.conta,
                categoria=cat,
                tipo="despesa",
                valor=Decimal(val),
                data=self.hoje,
                descricao=nome,
            )
        kpi = kpi_home(self.user)
        self.assertEqual(kpi["resultado"], kpi["receitas"] - kpi["despesas"])
        top = top_despesas_mes_atual(self.user, limit=10)
        soma_top = sum(Decimal(str(t["total"])) for t in top)
        self.assertEqual(soma_top, kpi["despesas"])

    def test_unit_dash_07_despesa_cartao(self):
        """Despesa cartão entra no KPI; saldo disponível da conta inalterado (CON-SALDO-04)."""
        criar_transacao_saldo_inicial(
            self.user, self.conta, Decimal("1000.00"), self.inicio_mes
        )
        cartao = Cartao.objects.create(
            usuario=self.user,
            nome="Visa",
            conta_padrao=self.conta,
            dia_fechamento=5,
            dia_vencimento=12,
            ativa=True,
        )
        saldo_disponivel = calcular_saldo_esperado(
            self.conta, incluir_compras_cartao=False
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            cartao=cartao,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("70.00"),
            data=self.hoje,
            descricao="Cartão",
        )
        assert_compra_cartao_nao_altera_saldo_conta(self.conta, saldo_disponivel)
        kpi = kpi_home(self.user)
        self.assertEqual(kpi["despesas"], Decimal("70.00"))

        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("30.00"),
            data=self.hoje,
            descricao="Conta",
        )
        kpi = kpi_home(self.user)
        self.assertEqual(kpi["despesas"], Decimal("100.00"))
        self.assertEqual(
            calcular_saldo_esperado(self.conta, incluir_compras_cartao=False),
            saldo_disponivel - Decimal("30.00"),
        )

    def test_unit_dash_08_toggle_ocultar_valores(self):
        """POST alterna Perfil.ocultar_valores_dashboard."""
        self.client.force_login(self.user)
        url = reverse("relatorios:toggle_ocultar_valores")
        Perfil.objects.filter(usuario=self.user).delete()

        r1 = self.client.post(url)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(json.loads(r1.content), {"ocultar": True})
        self.assertTrue(
            Perfil.objects.get(usuario=self.user).ocultar_valores_dashboard
        )

        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(json.loads(r2.content), {"ocultar": False})
        self.assertFalse(
            Perfil.objects.get(usuario=self.user).ocultar_valores_dashboard
        )
