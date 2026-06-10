"""ORC-REC/VIG/MUL/GRP/PCT/LIM/FAT — orçamentos avançados."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from categorias.models import Categoria
from contas.models import Conta
from relatorios.models import OrcamentoCategoria
from relatorios.services.filtros import RelatorioFiltros
from relatorios.services.orcamentos import (
    _filtros_orcamento_despesas,
    historico_utilizacao_categoria,
    listar_orcamentos,
    listar_orcamentos_mes,
    montar_linha_orcamento,
    painel_mes_orcamento,
    planejado_mes,
    periodo_orcamento_multi_mes,
    referencia_mes_orcamento,
    resumo_linhas_orcamento,
    rotulo_periodo_orcamento,
)
from relatorios.tests.helpers.orcamentos_consistency import (
    assert_barra_exibicao_capped,
    assert_painel_agregado,
    assert_percentual_linha,
    assert_status_linha,
)
from transacoes.models import Transacao

User = get_user_model()


class OrcRecorrenciaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="orc-rec@t.com", nome="R", password="x")
        self.cat = Categoria.objects.create(
            usuario=self.user, nome="Rec Cat", tipo="despesa", ativa=True
        )
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("500"),
            inicio_ano=2026,
            inicio_mes=1,
            ativo=True,
        )

    def test_orc_rec_01_planejado_mes_recorrente(self):
        for mes in (1, 2, 3):
            pm = planejado_mes(self.user, 2026, mes)
            self.assertIn(self.cat.id, pm)
            self.assertEqual(pm[self.cat.id].valor_planejado, Decimal("500"))

    def test_orc_rec_03_pausar_zera_planejado(self):
        o = OrcamentoCategoria.objects.get(usuario=self.user, categoria=self.cat)
        o.ativo = False
        o.save()
        pm = planejado_mes(self.user, 2026, 2)
        self.assertNotIn(self.cat.id, pm)

    def test_orc_rec_05_historico_tres_meses(self):
        conta = Conta.objects.create(usuario=self.user, nome="C", tipo="corrente")
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("250"),
            data=date(2026, 6, 10),
            descricao="gasto",
        )
        hist = historico_utilizacao_categoria(
            self.user, self.cat.id, meses=3, referencia=date(2026, 6, 15)
        )
        self.assertEqual(len(hist), 3)
        jun = next(h for h in hist if h["mes"] == 6)
        self.assertEqual(jun["percentual"], 50.0)


class OrcVigenciaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="orc-vig@t.com", nome="V", password="x")
        self.cat = Categoria.objects.create(
            usuario=self.user, nome="Vig Cat", tipo="despesa", ativa=True
        )

    def test_orc_vig_01_inicio_futuro(self):
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("300"),
            inicio_ano=2026,
            inicio_mes=6,
            ativo=True,
        )
        linhas = listar_orcamentos_mes(self.user, 2026, 5)
        nomes = {l.nome for l in linhas}
        self.assertNotIn("Vig Cat", nomes)

    def test_orc_vig_03_fim_aberto(self):
        o = OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("300"),
            inicio_ano=2026,
            inicio_mes=1,
            ativo=True,
        )
        self.assertTrue(o.vigente_em(2027, 12))

    def test_orc_vig_04_fim_antes_inicio_rejeitado(self):
        o = OrcamentoCategoria(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("100"),
            inicio_ano=2026,
            inicio_mes=6,
            fim_ano=2026,
            fim_mes=3,
            ativo=True,
        )
        with self.assertRaises(ValidationError):
            o.save()

    def test_orc_vig_06_referencia_ultimo_mes_intervalo(self):
        filtros = RelatorioFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 6, 30),
            preset="custom",
        )
        ano, mes = referencia_mes_orcamento(filtros)
        self.assertEqual((ano, mes), (2026, 6))


class OrcMultimesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="orc-mul@t.com", nome="M", password="x")
        self.cat = Categoria.objects.create(
            usuario=self.user, nome="Mul Cat", tipo="despesa", ativa=True
        )
        OrcamentoCategoria.objects.create(
            usuario=self.user,
            categoria=self.cat,
            valor_planejado=Decimal("100"),
            inicio_ano=2026,
            inicio_mes=1,
            ativo=True,
        )

    def test_orc_mul_02_gasto_um_mes_intervalo(self):
        conta = Conta.objects.create(usuario=self.user, nome="C", tipo="corrente")
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat,
            tipo="despesa",
            valor=Decimal("40"),
            data=date(2026, 4, 15),
            descricao="abr",
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
        linha = next(l for l in linhas if l.categoria_id == self.cat.id)
        self.assertEqual(linha.planejado, Decimal("200"))
        self.assertEqual(linha.realizado, Decimal("40"))

    def test_orc_mul_03_rotulo_multi_mes(self):
        filtros = RelatorioFiltros(
            data_inicio=date(2026, 4, 1),
            data_fim=date(2026, 5, 31),
            preset="custom",
        )
        self.assertTrue(periodo_orcamento_multi_mes(filtros))
        rotulo = rotulo_periodo_orcamento(filtros)
        self.assertIn("–", rotulo)
        self.assertIn("04", rotulo)


class OrcProgressoLimitesTests(TestCase):
    def test_orc_pct_02_limiar_atencao(self):
        linha = montar_linha_orcamento(
            orcamento_id=1,
            categoria_id=1,
            nome="A",
            cor="#000",
            icone="x",
            planejado=Decimal("100"),
            realizado=Decimal("85"),
        )
        assert_percentual_linha(linha, 85.0)
        assert_status_linha(linha, "risco")

    def test_orc_pct_04_estouro_barra_cap(self):
        linha = montar_linha_orcamento(
            orcamento_id=1,
            categoria_id=1,
            nome="B",
            cor="#000",
            icone="x",
            planejado=Decimal("100"),
            realizado=Decimal("150"),
        )
        assert_percentual_linha(linha, 150.0)
        assert_status_linha(linha, "excedido")
        assert_barra_exibicao_capped(linha)
        self.assertEqual(linha.disponivel, Decimal("-50"))

    def test_orc_grp_01_painel_soma_somente_vigentes(self):
        linhas = [
            montar_linha_orcamento(
                orcamento_id=1,
                categoria_id=1,
                nome="Vig",
                cor="#000",
                icone="x",
                planejado=Decimal("100"),
                realizado=Decimal("50"),
            ),
            montar_linha_orcamento(
                orcamento_id=2,
                categoria_id=2,
                nome="Fora",
                cor="#000",
                icone="x",
                planejado=Decimal("0"),
                realizado=Decimal("30"),
            ),
        ]
        painel = assert_painel_agregado(linhas)
        self.assertEqual(painel["planejado"], Decimal("100"))
        self.assertEqual(painel["realizado"], Decimal("50"))

    def test_orc_grp_02_contagem_saude(self):
        linhas = [
            montar_linha_orcamento(
                orcamento_id=i,
                categoria_id=i,
                nome=f"C{i}",
                cor="#000",
                icone="x",
                planejado=Decimal("100"),
                realizado=Decimal(r),
            )
            for i, r in enumerate([50, 90, 110], start=1)
        ]
        resumo = resumo_linhas_orcamento(linhas)
        painel = painel_mes_orcamento(linhas, resumo)
        self.assertEqual(painel["contagem_saude"]["ok"], 1)
        self.assertEqual(painel["contagem_saude"]["risco"], 1)
        self.assertEqual(painel["contagem_saude"]["excedido"], 1)

    def test_orc_lim_03_painel_global_excedido(self):
        linhas = [
            montar_linha_orcamento(
                orcamento_id=1,
                categoria_id=1,
                nome="X",
                cor="#000",
                icone="x",
                planejado=Decimal("100"),
                realizado=Decimal("120"),
            )
        ]
        resumo = resumo_linhas_orcamento(linhas)
        painel = painel_mes_orcamento(linhas, resumo)
        self.assertEqual(painel["status"], "excedido")
        self.assertLess(painel["disponivel"], Decimal("0"))
