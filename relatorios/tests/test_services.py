from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse

from categorias.models import Categoria
from relatorios.models import OrcamentoCategoria
from relatorios.services.despesas_categoria import (
    filtros_periodo_anterior,
    montar_analise_despesas_categoria,
)
from relatorios.services.por_conta import montar_analise_por_conta
from relatorios.services.filtros import RelatorioFiltros, parse_relatorio_filtros
from relatorios.services.insights import avaliar_alertas_orcamento, gerar_insights_dashboard
from relatorios.services.orcamentos import (
    _filtros_orcamento_despesas,
    classificar_status,
    listar_orcamentos,
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


class CoresGraficoCategoriasTests(TestCase):
    def test_cores_distintas_quando_todas_iguais(self):
        from relatorios.services.dashboard import cores_distintas_para_categorias

        entrada = [
            {"nome": "A", "cor": "#4F46E5", "total": 100},
            {"nome": "B", "cor": "#4F46E5", "total": 80},
            {"nome": "C", "cor": "#4F46E5", "total": 50},
        ]
        saida = cores_distintas_para_categorias(entrada)
        cores = [c["cor"] for c in saida]
        self.assertEqual(len(cores), len(set(cores)))


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


class DespesasCategoriaAnaliseTests(TestCase):
    def setUp(self):
        from contas.models import Conta

        self.user = User.objects.create_user(email="cat-analise@t.com", nome="C", password="x")
        self.conta = Conta.objects.create(usuario=self.user, nome="Conta analise", ativa=True)
        self.cat_a = Categoria.objects.create(
            usuario=self.user, nome="Moradia analise", tipo="despesa", ativa=True, cor="#6366f1"
        )
        self.cat_b = Categoria.objects.create(
            usuario=self.user, nome="Lazer analise", tipo="despesa", ativa=True, cor="#f43f5e"
        )

    def _tx(self, categoria, valor, dia, mes=5, ano=2026):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=categoria,
            tipo="despesa",
            valor=Decimal(str(valor)),
            descricao=f"Teste {categoria.nome}",
            data=date(ano, mes, dia),
        )

    def test_filtros_periodo_anterior_mesma_duracao(self):
        f = RelatorioFiltros(
            data_inicio=date(2026, 5, 10),
            data_fim=date(2026, 5, 20),
            preset="custom",
        )
        ant = filtros_periodo_anterior(f)
        self.assertEqual((ant.data_fim - ant.data_inicio).days, (f.data_fim - f.data_inicio).days)

    def test_montar_analise_ordena_e_compara(self):
        self._tx(self.cat_a, 400, 5)
        self._tx(self.cat_a, 100, 8)
        self._tx(self.cat_b, 50, 6)
        # período anterior: só moradia menor
        self._tx(self.cat_a, 200, 5, mes=4)

        f = RelatorioFiltros(
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        analise = montar_analise_despesas_categoria(self.user, f, limite_lista=10)
        self.assertTrue(analise["tem_dados"])
        self.assertEqual(analise["categorias"][0]["nome"], "Moradia analise")
        self.assertEqual(analise["hero"].maior_gasto_nome, "Moradia analise")
        self.assertGreater(analise["categorias"][0]["delta_pct"], 0)
        self.assertGreaterEqual(len(analise["insights"]), 1)


class PorContaAnaliseTests(TestCase):
    def setUp(self):
        from contas.models import Conta

        self.user = User.objects.create_user(email="conta-analise@t.com", nome="P", password="x")
        self.conta_a = Conta.objects.create(
            usuario=self.user, nome="Principal", tipo="corrente", ativa=True, icone="bank"
        )
        self.conta_b = Conta.objects.create(
            usuario=self.user, nome="Reserva", tipo="poupanca", ativa=True, icone="bank"
        )
        self.cat = Categoria.objects.create(
            usuario=self.user, nome="Mercado conta", tipo="despesa", ativa=True
        )

    def _tx(self, conta, tipo, valor, dia, mes=5, ano=2026, categoria=None):
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=categoria or self.cat,
            tipo=tipo,
            valor=Decimal(str(valor)),
            descricao=f"Teste {tipo}",
            data=date(ano, mes, dia),
        )

    def test_montar_analise_patrimonio_e_movimento(self):
        self._tx(self.conta_a, "receita", 1000, 5, categoria=None)
        self._tx(self.conta_a, "despesa", 200, 8)
        self._tx(self.conta_b, "receita", 500, 6, categoria=None)
        self._tx(self.conta_b, "despesa", 50, 10)

        f = RelatorioFiltros(
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        analise = montar_analise_por_conta(self.user, f)
        self.assertTrue(analise["tem_dados"])
        self.assertTrue(analise["tem_patrimonio"])
        self.assertEqual(analise["hero"].maior_saldo_nome, "Principal")
        self.assertGreater(analise["patrimonio_total"], 0)
        self.assertGreaterEqual(len(analise["contas"]), 2)
        self.assertGreaterEqual(len(analise["insights"]), 1)
        principal = next(c for c in analise["contas"] if c["nome"] == "Principal")
        self.assertGreater(principal["saldo"], 0)
        self.assertGreater(principal["quantidade_transacoes"], 0)


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

    def test_nao_exibe_gastos_sem_orcamento_como_pausado(self):
        """Categorias só com transação não devem aparecer como orçamento pausado."""
        from contas.models import Conta

        cat_extra = Categoria.objects.create(
            usuario=self.user, nome="Extra sem orc", tipo="despesa", ativa=True
        )
        conta = Conta.objects.create(usuario=self.user, nome="C-extra", tipo="corrente")
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=cat_extra,
            tipo="despesa",
            valor=Decimal("80"),
            data=date(2026, 5, 10),
            descricao="extra",
        )
        filtros = RelatorioFiltros(
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        linhas = listar_orcamentos(
            self.user,
            _filtros_orcamento_despesas(filtros),
            ano_ref=2026,
            mes_ref=5,
            incluir_inativos=False,
            incluir_gasto_sem_orcamento=False,
        )
        nomes = {l.nome for l in linhas}
        self.assertIn("A", nomes)
        self.assertNotIn("Extra sem orc", nomes)
        self.assertTrue(all(l.orcamento_id for l in linhas))

    def test_listar_orcamentos_usa_intervalo_filtro_nao_ano_mes_nav(self):
        """Gastos no período do drawer, mesmo com ano/mes de navegação em outro mês."""
        from contas.models import Conta

        conta = Conta.objects.create(usuario=self.user, nome="C-nav", tipo="corrente")
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat_a,
            tipo="despesa",
            valor=Decimal("120"),
            data=date(2026, 4, 15),
            descricao="abril",
        )
        filtros = RelatorioFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 4, 30),
            preset="custom",
        )
        linhas = listar_orcamentos(
            self.user,
            _filtros_orcamento_despesas(filtros),
            ano_ref=2026,
            mes_ref=6,
            incluir_inativos=True,
        )
        linha = next(l for l in linhas if l.categoria_id == self.cat_a.pk)
        self.assertEqual(linha.realizado, Decimal("120"))

    def test_listar_orcamentos_soma_planejado_em_periodo_multimes(self):
        OrcamentoCategoria.objects.filter(usuario=self.user, categoria=self.cat_a).update(
            inicio_ano=2026,
            inicio_mes=1,
            fim_ano=None,
            fim_mes=None,
        )
        filtros = RelatorioFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        linhas = listar_orcamentos(
            self.user,
            _filtros_orcamento_despesas(filtros),
            ano_ref=2026,
            mes_ref=5,
            incluir_inativos=True,
        )
        linha = next(l for l in linhas if l.categoria_id == self.cat_a.pk)
        self.assertEqual(linha.planejado, Decimal("200"))

    def test_realizado_cartao_no_mes_da_competencia(self):
        """Compra em maio com vencimento em junho deve contar no orçamento de junho."""
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
        data_compra = date(2026, 5, 28)
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            cartao=cartao,
            categoria=self.cat_a,
            tipo="despesa",
            valor=Decimal("75"),
            data=data_compra,
            descricao="compra cartão",
        )
        fatura = obter_ou_criar_fatura(cartao, data_compra)
        self.assertEqual(fatura.data_vencimento.month, 6)

        linhas_maio = listar_orcamentos_mes(self.user, 2026, 5)
        linha_maio = next(l for l in linhas_maio if l.categoria_id == self.cat_a.pk)
        self.assertEqual(linha_maio.realizado, Decimal("0"))

        linhas_junho = listar_orcamentos_mes(self.user, 2026, 6)
        linha_junho = next(l for l in linhas_junho if l.categoria_id == self.cat_a.pk)
        self.assertEqual(linha_junho.realizado, Decimal("75"))

    def test_realizado_alinha_categoria_padrao_e_do_usuario(self):
        """Orçamento na categoria global; lançamento na cópia do usuário com mesmo nome."""
        cat_padrao = Categoria.objects.create(
            nome="Padrao Orc",
            tipo="despesa",
            ativa=True,
            padrao=True,
        )
        cat_user = Categoria.objects.create(
            usuario=self.user,
            nome="Padrao Orc",
            tipo="despesa",
            ativa=True,
        )
        OrcamentoCategoria.objects.filter(usuario=self.user).delete()
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=cat_padrao,
            valor_planejado=Decimal("200"),
            inicio_ano=2026,
            inicio_mes=5,
            ativo=True,
        )
        from contas.models import Conta

        conta = Conta.objects.create(usuario=self.user, nome="C2", tipo="corrente")
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=cat_user,
            tipo="despesa",
            valor=Decimal("42"),
            data=date(2026, 5, 12),
            descricao="gasto user cat",
        )
        linhas = listar_orcamentos_mes(self.user, 2026, 5)
        linha = next(l for l in linhas if l.categoria_id == cat_padrao.pk)
        self.assertEqual(linha.realizado, Decimal("42"))

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


class FluxoCaixaServicoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="fluxo@t.com", nome="F", password="x")
        self.client.force_login(self.user)
        from contas.models import Conta

        self.conta = Conta.objects.create(usuario=self.user, nome="Conta", tipo="corrente")
        self.cat_rec = Categoria.objects.create(
            usuario=self.user, nome="Receita Fluxo Test", tipo="receita", ativa=True
        )
        self.cat_desp = Categoria.objects.create(
            usuario=self.user, nome="Despesa Fluxo Test", tipo="despesa", ativa=True
        )

    def test_destaques_maior_entrada_e_pior_dia(self):
        from relatorios.services.agregacoes import aplicar_filtros_relatorio, serie_fluxo_diario
        from relatorios.services.fluxo_caixa import destaques_fluxo_periodo
        from relatorios.selectors import transacoes_base_qs

        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("2500"),
            data=date(2026, 5, 10),
            descricao="Salário",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("890"),
            data=date(2026, 5, 12),
            descricao="Fatura",
        )
        filtros = RelatorioFiltros(
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        qs = aplicar_filtros_relatorio(transacoes_base_qs(self.user), filtros)
        serie = serie_fluxo_diario(qs, filtros)
        dest = destaques_fluxo_periodo(qs, filtros, serie)
        self.assertEqual(dest["maior_entrada"]["valor"], Decimal("2500"))
        self.assertEqual(dest["maior_entrada"]["titulo"], "Receita Fluxo Test")
        self.assertEqual(dest["maior_saida"]["valor"], Decimal("890"))
        self.assertIsNotNone(dest["melhor_dia"])

    def test_resumo_minimo_periodo(self):
        from relatorios.services.fluxo_caixa import resumo_minimo_periodo

        serie = {
            "liquido": [100.0, -50.0, 20.0],
            "acumulado": [100.0, 50.0, 70.0],
        }
        resumo = resumo_minimo_periodo(serie, Decimal("70"))
        self.assertEqual(resumo["saldo_inicial"], Decimal("0"))
        self.assertEqual(resumo["saldo_final"], Decimal("70"))
        self.assertEqual(resumo["variacao_liquida"], Decimal("70"))
        self.assertTrue(resumo["tem_movimentacao"])

    def test_dinamica_fluxo_periodo(self):
        from relatorios.services.fluxo_caixa import dinamica_fluxo_periodo

        serie = {
            "labels": ["01/05", "02/05", "03/05", "04/05", "05/05"],
            "entradas": [0.0, 500.0, 0.0, 0.0, 100.0],
            "saidas": [0.0, 0.0, 300.0, 0.0, 50.0],
        }
        dest = {"melhor_dia": {"rotulo": "02/05", "valor": Decimal("500")}, "pior_dia": None}
        din = dinamica_fluxo_periodo(serie, dest)
        self.assertEqual(din["pico_entrada"]["valor"], Decimal("500"))
        self.assertEqual(din["pico_entrada"]["rotulo"], "02/05")
        self.assertEqual(din["pico_saida"]["valor"], Decimal("300"))
        self.assertEqual(din["dias_com_movimento"], 3)
        self.assertTrue(din["entradas_pontuais"])

    def test_interpretacao_dinamica_fluxo(self):
        from relatorios.services.fluxo_caixa import interpretacao_dinamica_fluxo

        dinamica = {
            "fluxo_irregular": True,
            "entradas_pontuais": True,
            "dias_com_movimento": 3,
            "total_dias": 31,
            "pico_saida": {"rotulo": "12/05", "valor": Decimal("890")},
        }
        totais = {"receitas": Decimal("5200"), "despesas": Decimal("2850")}
        frases = interpretacao_dinamica_fluxo(dinamica, totais)
        self.assertTrue(len(frases) >= 1)
        self.assertTrue(any("irregular" in f.lower() or "pontuais" in f.lower() for f in frases))

    def test_interpretacao_acionavel(self):
        from relatorios.services.fluxo_caixa import interpretacao_acionavel

        totais = {"receitas": Decimal("5200"), "despesas": Decimal("2850")}
        top_d = [{"nome": "Alimentação", "total": Decimal("890"), "percentual": Decimal("31")}]
        top_r = [{"nome": "Salário", "total": Decimal("5000"), "percentual": Decimal("96")}]
        comp = {"tem_base": True, "despesas_pct": Decimal("12")}
        frases = interpretacao_acionavel("Maio", totais, Decimal("2350"), comp, top_d, top_r)
        self.assertTrue(len(frases) >= 1)
        self.assertTrue(any("Alimentação" in f or "Salário" in f for f in frases))

    def test_interpretacao_periodo_positivo(self):
        from relatorios.services.fluxo_caixa import interpretacao_fluxo_periodo

        totais = {"receitas": Decimal("5200"), "despesas": Decimal("2850")}
        serie = {"liquido": [100.0] * 20 + [-50.0] * 11, "acumulado": list(range(31))}
        msg = interpretacao_fluxo_periodo(totais, serie)
        self.assertIn("positivo", msg.lower())

    def test_insights_rapidos(self):
        from relatorios.services.fluxo_caixa import insights_rapidos

        totais = {"receitas": Decimal("5200"), "despesas": Decimal("2850")}
        dest = {
            "maior_saida": {"titulo": "Alimentação", "valor": Decimal("890"), "rotulo": "12/05"},
            "maior_entrada": {"titulo": "Salário", "valor": Decimal("5000"), "rotulo": "05/05"},
        }
        ind = {"dias_positivos": 18, "dias_negativos": 7}
        ins = insights_rapidos(totais, Decimal("2350"), dest, ind)
        self.assertEqual(ins["modo"], "completo")
        self.assertTrue(any("saldo positivo" in i.lower() for i in ins["itens"]))
        self.assertTrue(any("Alimentação" in i for i in ins["itens"]))
        self.assertTrue(any("poupou" in i for i in ins["itens"]))

    def test_contexto_periodo_negativo(self):
        from relatorios.services.fluxo_caixa import insights_rapidos

        totais = {"receitas": Decimal("1000"), "despesas": Decimal("1500")}
        ins = insights_rapidos(totais, Decimal("-500"), {}, {"dias_positivos": 5, "dias_negativos": 10})
        self.assertTrue(any("negativo" in i.lower() for i in ins["itens"]))

    def test_serie_fluxo_entradas_saidas(self):
        from relatorios.services.agregacoes import aplicar_filtros_relatorio, serie_fluxo_diario
        from relatorios.selectors import transacoes_base_qs

        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_rec,
            tipo="receita",
            valor=Decimal("100"),
            data=date(2026, 5, 5),
            descricao="entrada teste",
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_desp,
            tipo="despesa",
            valor=Decimal("40"),
            data=date(2026, 5, 5),
            descricao="saida teste",
        )
        filtros = RelatorioFiltros(
            data_inicio=date(2026, 5, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        qs = aplicar_filtros_relatorio(transacoes_base_qs(self.user), filtros)
        serie = serie_fluxo_diario(qs, filtros)
        self.assertIn("entradas", serie)
        self.assertIn("saidas", serie)
        idx = serie["labels"].index("05/05")
        self.assertEqual(serie["entradas"][idx], 100.0)
        self.assertEqual(serie["saidas"][idx], 40.0)

    def test_resumo_o_que_aconteceu(self):
        from relatorios.services.fluxo_caixa import resumo_o_que_aconteceu

        totais = {"receitas": Decimal("5200"), "despesas": Decimal("2850")}
        resumo = resumo_o_que_aconteceu("Maio", totais, Decimal("2350"), {})
        self.assertEqual(resumo["modo"], "completo")

    def test_indicadores_saude(self):
        from relatorios.services.fluxo_caixa import indicadores_saude_fluxo

        totais = {"receitas": Decimal("100"), "despesas": Decimal("50")}
        serie = {"liquido": [10.0, -5.0, 20.0]}
        destaques = {"melhor_dia": {"valor": Decimal("20"), "rotulo": "03/05"}}
        ind = indicadores_saude_fluxo(totais, serie, destaques)
        self.assertEqual(ind["dias_positivos"], 2)
        self.assertEqual(ind["dias_negativos"], 1)

    def test_tela_fluxo_caixa_ok(self):
        res = self.client.get(reverse("relatorios:fluxo_caixa"), {"ano": 2026, "mes": 5})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Entradas x Saídas")
        self.assertContains(res, "Entradas")
        self.assertContains(res, "Resultado líquido")
        self.assertContains(res, "Como seu dinheiro se movimentou")
        self.assertContains(res, "Ver transações do período")
        self.assertContains(res, "chart-fluxo")
        self.assertNotContains(res, "Movimentações de destaque")
        self.assertNotContains(res, "vs mês anterior")
