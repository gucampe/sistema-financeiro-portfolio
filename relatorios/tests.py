from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from categorias.models import Categoria
from relatorios.models import OrcamentoCategoria
from relatorios.services.filtros import RelatorioFiltros, parse_relatorio_filtros
from relatorios.services.insights import avaliar_alertas_orcamento, gerar_insights_dashboard
from relatorios.services.orcamentos import (
    classificar_status,
    listar_orcamentos_dashboard,
    listar_orcamentos_mes,
    montar_linha_orcamento,
    navegacao_mes_context,
    painel_mes_orcamento,
    queryset_despesas_orcamento,
    resumo_linhas_orcamento,
)
from transacoes.models import Transacao

User = get_user_model()


class RelatorioFiltrosParseTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="t@t.com", nome="T", password="x")

    def test_preset_este_mes(self):
        q = QueryDict(mutable=True)
        q["preset"] = "este_mes"
        f = parse_relatorio_filtros(q, usuario=self.user)
        self.assertEqual(f.preset, "este_mes")
        self.assertIn(f.data_inicio.month, range(1, 13))

    def test_custom_inicio_fim(self):
        q = QueryDict(mutable=True)
        q["inicio"] = "2026-01-10"
        q["fim"] = "2026-01-20"
        f = parse_relatorio_filtros(q, usuario=self.user)
        self.assertEqual(f.data_inicio, date(2026, 1, 10))
        self.assertEqual(f.data_fim, date(2026, 1, 20))
        self.assertEqual(f.preset, "custom")

    def test_drill_query_string_sem_categoria(self):
        f = RelatorioFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 4, 30),
            conta_ids=(1, 2),
            categoria_ids=(9,),
            tipos=("despesa",),
            preset="custom",
            meio_pagamento="todos",
            modo_data="fluxo",
        )
        s = f.to_drill_transacoes_query_string()
        self.assertIn("inicio=2026-04-01", s)
        self.assertIn("fim=2026-04-30", s)
        self.assertIn("conta=1", s)
        self.assertNotIn("categoria", s)

    def test_contagem_filtros_ativos_padrao(self):
        f = RelatorioFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 4, 30),
            preset="este_mes",
        )
        self.assertEqual(f.contagem_filtros_ativos(), 0)

    def test_contagem_filtros_ativos_multiplos(self):
        f = RelatorioFiltros(
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
            conta_ids=(1,),
            categoria_ids=(2, 3),
            tipos=("despesa",),
            preset="ultimos_30d",
        )
        self.assertEqual(f.contagem_filtros_ativos(), 4)


class OrcamentoCategoriaModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="orc@t.com", nome="O", password="x")
        self.cat = Categoria.objects.create(usuario=self.user, nome="Mercado", tipo="despesa", ativa=True)

    def test_vigente_em_respeita_inicio_fim_e_ativo(self):
        o = OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("500"),
            inicio_ano=2026,
            inicio_mes=3,
            fim_ano=2026,
            fim_mes=6,
            ativo=True,
        )
        self.assertTrue(o.vigente_em(2026, 4))
        self.assertFalse(o.vigente_em(2026, 2))
        self.assertFalse(o.vigente_em(2026, 7))
        o.ativo = False
        o.save()
        self.assertFalse(o.vigente_em(2026, 4))


class OrcamentosServicoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="svc@t.com", nome="S", password="x")
        self.cat_a = Categoria.objects.create(usuario=self.user, nome="A", tipo="despesa", ativa=True)
        self.cat_b = Categoria.objects.create(usuario=self.user, nome="B", tipo="despesa", ativa=True)
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat_a,
            valor_planejado=Decimal("100"),
            inicio_ano=2026,
            inicio_mes=1,
            ativo=True,
        )
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat_b,
            valor_planejado=Decimal("200"),
            inicio_ano=2026,
            inicio_mes=1,
            ativo=True,
        )

    def test_disponivel_negativo(self):
        linha = montar_linha_orcamento(
            orcamento_id=1,
            categoria_id=1,
            nome="Teste",
            cor="#000",
            icone="fa-x",
            planejado=Decimal("100"),
            realizado=Decimal("150"),
        )
        self.assertEqual(linha.disponivel, Decimal("-50"))
        self.assertEqual(linha.status, "excedido")

    def test_classificar_status_limites(self):
        self.assertEqual(classificar_status(84)[0], "ok")
        self.assertEqual(classificar_status(85)[0], "risco")
        self.assertEqual(classificar_status(100)[0], "excedido")

    def test_painel_mes_contagem_saude(self):
        linhas = [
            montar_linha_orcamento(
                orcamento_id=1,
                categoria_id=1,
                nome="A",
                cor="#000",
                icone="x",
                planejado=Decimal("100"),
                realizado=Decimal("50"),
            ),
            montar_linha_orcamento(
                orcamento_id=2,
                categoria_id=2,
                nome="B",
                cor="#000",
                icone="x",
                planejado=Decimal("100"),
                realizado=Decimal("90"),
            ),
            montar_linha_orcamento(
                orcamento_id=3,
                categoria_id=3,
                nome="C",
                cor="#000",
                icone="x",
                planejado=Decimal("100"),
                realizado=Decimal("110"),
            ),
        ]
        resumo = resumo_linhas_orcamento(linhas)
        painel = painel_mes_orcamento(linhas, resumo)
        self.assertEqual(painel["contagem_saude"]["ok"], 1)
        self.assertEqual(painel["contagem_saude"]["risco"], 1)
        self.assertEqual(painel["contagem_saude"]["excedido"], 1)
        self.assertAlmostEqual(painel["percentual"], 83.33, places=1)

    def test_navegacao_mes_context(self):
        nav = navegacao_mes_context(2026, 5)
        self.assertEqual(nav["mes_anterior"], 4)
        self.assertEqual(nav["ano_anterior"], 2026)
        self.assertEqual(nav["mes_proximo"], 6)
        self.assertEqual(nav["nav_qs_extra"], "")
        nav_extra = navegacao_mes_context(2026, 5, nav_qs_extra="&foo=1")
        self.assertEqual(nav_extra["nav_qs_extra"], "&foo=1")

    def test_exclui_pagamento_de_fatura(self):
        from contas.models import Conta
        from cartoes.models import Cartao
        from cartoes.services.faturas import obter_ou_criar_fatura

        conta = Conta.objects.create(usuario=self.user, nome="C", tipo="corrente")
        cartao = Cartao.objects.create(
            usuario=self.user,
            nome="Visa",
            dia_fechamento=10,
            dia_vencimento=20,
            conta_padrao=conta,
        )
        fatura = obter_ou_criar_fatura(cartao, date(2026, 5, 10))
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat_a,
            tipo="despesa",
            valor=Decimal("40"),
            data=date(2026, 5, 10),
            descricao="compra",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat_a,
            tipo="despesa",
            valor=Decimal("999"),
            data=date(2026, 5, 11),
            descricao="pagamento fatura",
            pagamento_de_fatura=fatura,
        )
        from relatorios.services.orcamentos import filtros_mes

        qs = queryset_despesas_orcamento(self.user, filtros_mes(2026, 5))
        total = sum(t.valor for t in qs)
        self.assertEqual(total, Decimal("40"))

    def test_dashboard_ordenacao_por_percentual(self):
        from contas.models import Conta

        conta = Conta.objects.create(usuario=self.user, nome="C", tipo="corrente")
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat_a,
            tipo="despesa",
            valor=Decimal("90"),
            data=date(2026, 5, 5),
            descricao="a",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat_b,
            tipo="despesa",
            valor=Decimal("50"),
            data=date(2026, 5, 5),
            descricao="b",
        )
        linhas = listar_orcamentos_mes(self.user, 2026, 5)
        dash = listar_orcamentos_dashboard(self.user, limite=3)
        self.assertEqual(len(dash), 2)
        self.assertGreaterEqual(dash[0].percentual or 0, dash[1].percentual or 0)

    def test_insights_integra_alertas_orcamento(self):
        linhas = [{"nome": "A", "planejado": Decimal("100"), "percentual": 90.0}]
        alertas = avaliar_alertas_orcamento(linhas)
        self.assertEqual(len(alertas), 1)
        insights = gerar_insights_dashboard(
            self.user,
            RelatorioFiltros(data_inicio=date(2026, 5, 1), data_fim=date(2026, 5, 31), preset="custom"),
            totais_atual={"receitas": Decimal("0"), "despesas": Decimal("0")},
            top_despesa=[],
            orcamento_linhas=linhas,
        )
        self.assertTrue(any("limite" in i["titulo"].lower() or "orçamento" in i["titulo"].lower() for i in insights))


class OrcamentosViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="v@t.com", nome="V", password="x")
        self.client.force_login(self.user)
        self.cat = Categoria.objects.create(usuario=self.user, nome="Cat", tipo="despesa", ativa=True)

    def test_tela_orcamentos_ok(self):
        res = self.client.get(reverse("relatorios:orcamentos"))
        self.assertEqual(res.status_code, 200)

    def test_salvar_orcamento_json(self):
        res = self.client.post(
            reverse("relatorios:orcamentos_salvar"),
            {
                "categoria": self.cat.pk,
                "valor_planejado": "350.00",
                "inicio_ano": 2026,
                "inicio_mes": 5,
                "ativo": "on",
                "ref_ano": 2026,
                "ref_mes": 5,
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")
        self.assertTrue(OrcamentoCategoria.objects.filter(usuario=self.user, categoria=self.cat).exists())

    def test_toggle_ativo(self):
        o = OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("100"),
            inicio_ano=2026,
            inicio_mes=5,
            ativo=True,
        )
        url = reverse("relatorios:orcamentos_toggle_ativo", args=[o.pk])
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        o.refresh_from_db()
        self.assertFalse(o.ativo)
