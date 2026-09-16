"""Testes de orientação: copy, empty states, eventos, Ajuda e dica versionada."""

from __future__ import annotations

import json
from dataclasses import replace

from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contas.models import Conta
from usuarios.ajuda.busca import artigo_corresponde_busca, normalizar_texto_ajuda
from usuarios.ajuda.catalogo import ARTIGOS, artigo_por_id
from usuarios.ajuda.dicas import DICAS, deve_mostrar_dica, marcar_dica_dispensada
from usuarios.models import Perfil, ProdutoEvento
from usuarios.services.produto_eventos import registrar_evento, sanitizar_payload
from usuarios.tests.test_onboarding import OnboardingTestMixin


class VocabularioHintsTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("vocab@test.com")
        self.client.force_login(self.user)

    def test_dashboard_unifica_resultado_e_saldo_das_contas(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)
        r = self.client.get(reverse("relatorios:home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Resultado do período")
        self.assertNotContains(r, "Saldo do período")
        self.assertContains(r, "Saldo das contas")
        self.assertNotContains(r, "Patrimônio disponível")
        self.assertContains(r, "Soma do que está nas contas ativas")
        self.assertContains(r, "hint-panel-resultado-periodo-desktop")
        self.assertContains(r, "O que entrou menos o que saiu neste período. Não é o dinheiro que você tem.")
        self.assertContains(r, "?ajuda=resultado")
        self.assertContains(r, "Entender o resultado →")
        self.assertContains(r, "Soma do que está nas suas contas hoje.")
        self.assertContains(r, "?ajuda=mapa")
        self.assertContains(r, "Entender melhor →")

    def test_transacoes_copy_resultado_e_importar_extrato(self):
        r = self.client.get(reverse("transacoes:historico"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "<h1", html=False)
        self.assertContains(r, "Transações")
        self.assertNotContains(r, ">Lançamentos<")
        self.assertContains(r, "Importar extrato")
        self.assertNotContains(r, "Importar OFX")
        self.assertContains(r, "Resultado")
        self.assertContains(r, "Move dinheiro entre as suas contas")
        self.assertContains(r, "?ajuda=transferencia")
        self.assertContains(r, "Entender transferências →")

    def test_por_conta_alinha_rotulo(self):
        self.criar_conta(self.user)
        r = self.client.get(reverse("relatorios:por_conta"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Saldo das contas")
        self.assertContains(r, "Saldo por conta")
        self.assertNotContains(r, "Patrimônio total")
        self.assertNotContains(r, "Patrimônio por conta")


class EmptyStatesTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("empty@test.com")
        self.client.force_login(self.user)

    def test_historico_empty_tem_porque_e_ctas(self):
        r = self.client.get(reverse("transacoes:historico"))
        self.assertContains(r, "Lance na mão ou importe o extrato")
        self.assertContains(r, f'{reverse("transacoes:historico")}?nova=1')
        self.assertContains(r, f'{reverse("transacoes:historico")}?importar=1')
        self.assertContains(r, "Não conseguiu importar?")
        self.assertContains(r, "Lance na mão.")
        self.assertContains(r, "?ajuda=adicionar-dados")
        self.assertContains(r, "Como adicionar seus dados →")
        self.assertContains(r, "?ajuda=corrigir-categoria")
        self.assertContains(r, "Entender categorização →")

    def test_contas_empty_explica_porque(self):
        r = self.client.get(reverse("contas:home"))
        self.assertContains(r, "Contas são onde o seu dinheiro está")
        self.assertContains(r, "saldo e patrimônio")

    def test_cartoes_empty_credito_nao_e_conta(self):
        r = self.client.get(reverse("cartoes:home"))
        self.assertContains(r, "A compra aparece na fatura")
        self.assertContains(r, "?ajuda=cartao")
        self.assertContains(r, "Entender cartões →")

    def test_dashboard_empty_conta(self):
        r = self.client.get(reverse("relatorios:home"))
        self.assertContains(r, "Contas são onde o seu dinheiro está")
        self.assertContains(r, "Entender cartões →")


class PrimeirosPassosCopyTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("ppcopy@test.com")
        self.client.force_login(self.user)

    def test_movimentacao_dual_path_e_cartao_opcional(self):
        r = self.client.get(reverse("usuarios:primeiros_passos"))
        self.assertContains(r, "Lance uma transação na mão ou importe o extrato")
        self.assertContains(r, f'{reverse("transacoes:historico")}?nova=1')
        self.assertContains(r, f'{reverse("transacoes:historico")}?importar=1')
        self.assertContains(r, "Opcional. Cartão de crédito não é uma conta")
        self.assertContains(r, "Opcional")


class ProdutoEventoTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("evt@test.com")
        self.client.force_login(self.user)

    def test_first_eventos_sao_idempotentes(self):
        a = registrar_evento(self.user, "first_account_created")
        b = registrar_evento(self.user, "first_account_created")
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(
            ProdutoEvento.objects.filter(usuario=self.user, evento="first_account_created").count(),
            1,
        )

    def test_payload_remove_pii_e_valores(self):
        limpo = sanitizar_payload(
            {
                "valor": "10.00",
                "email": "x@y.com",
                "descricao": "supermercado",
                "q": "cartão fatura",
                "article_id": "cartao",
            }
        )
        self.assertEqual(limpo, {"q": "cartão fatura", "article_id": "cartao"})
        registrar_evento(self.user, "help_search_used", {"q": "cartão", "valor": 99})
        ev = ProdutoEvento.objects.get(usuario=self.user, evento="help_search_used")
        self.assertNotIn("valor", ev.payload)
        self.assertEqual(ev.payload.get("q"), "cartão")

    def test_post_recorrente_cria_varios(self):
        url = reverse("usuarios:produto_evento")
        body = json.dumps({"evento": "help_opened", "payload": {"origem": "nav"}})
        r1 = self.client.post(url, data=body, content_type="application/json")
        r2 = self.client.post(url, data=body, content_type="application/json")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(
            ProdutoEvento.objects.filter(usuario=self.user, evento="help_opened").count(),
            2,
        )

    def test_post_rejeita_evento_invalido(self):
        r = self.client.post(
            reverse("usuarios:produto_evento"),
            data=json.dumps({"evento": "login_failed"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_post_aceita_eventos_pwa(self):
        url = reverse("usuarios:produto_evento")
        r = self.client.post(
            url,
            data=json.dumps({"evento": "pwa_opened_standalone", "payload": {"origem": "standalone"}}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(
            ProdutoEvento.objects.filter(usuario=self.user, evento="pwa_opened_standalone").exists()
        )

    def test_hooks_conta_transacao_dashboard(self):
        self.client.post(
            reverse("contas:salvar"),
            data={"nome": "Nubank", "tipo": "corrente", "icone": "nubank"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertTrue(
            ProdutoEvento.objects.filter(usuario=self.user, evento="first_account_created").exists()
        )

        conta = Conta.objects.get(usuario=self.user)
        cat = self.categoria_despesa(self.user)
        resp_tx = self.client.post(
            reverse("transacoes:historico"),
            data={
                "tipo": "despesa",
                "valor": "10.00",
                "data": timezone.localdate().isoformat(),
                "descricao": "Teste",
                "conta": conta.pk,
                "categoria": cat.pk,
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp_tx.status_code, 200, resp_tx.content)
        self.assertTrue(
            ProdutoEvento.objects.filter(
                usuario=self.user, evento="first_transaction_created"
            ).exists()
        )

        self.client.get(reverse("relatorios:home"))
        self.assertTrue(
            ProdutoEvento.objects.filter(
                usuario=self.user, evento="first_dashboard_view_with_data"
            ).exists()
        )

    def test_primeiros_passos_emite_onboarding_started(self):
        self.client.get(reverse("usuarios:primeiros_passos"))
        self.client.get(reverse("usuarios:primeiros_passos"))
        self.assertEqual(
            ProdutoEvento.objects.filter(usuario=self.user, evento="onboarding_started").count(),
            1,
        )


class DrawerAjudaTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("ajuda@test.com")
        self.client.force_login(self.user)

    def test_catalogo_tem_oito_artigos(self):
        self.assertEqual(
            [a.id for a in ARTIGOS],
            [
                "mapa",
                "adicionar-dados",
                "transacao",
                "corrigir-categoria",
                "transferencia",
                "cartao",
                "pagar-fatura",
                "resultado",
            ],
        )
        transacao = artigo_por_id("transacao")
        self.assertIsNotNone(transacao)
        self.assertEqual(transacao.titulo, "Como funciona uma transação")
        self.assertIn("despesas registram gastos", transacao.resumo)
        self.assertIn("transação", transacao.tags)
        self.assertEqual(transacao.grupo, "comece")
        self.assertEqual(transacao.tipo, "entenda")
        self.assertIsNotNone(artigo_por_id("corrigir-categoria"))
        self.assertIsNotNone(artigo_por_id("transferencia"))
        self.assertIsNotNone(artigo_por_id("resultado"))
        self.assertIsNotNone(artigo_por_id("pagar-fatura"))
        self.assertIsNone(artigo_por_id("categoria"))
        self.assertEqual(artigo_por_id("resultado").grupo, "entenda")
        self.assertEqual(artigo_por_id("cartao").grupo, "entenda")
        self.assertEqual(artigo_por_id("pagar-fatura").grupo, "entenda")
        self.assertEqual(artigo_por_id("pagar-fatura").tipo, "faca_comigo")

    def test_drawer_no_html_autenticado(self):
        r = self.client.get(reverse("relatorios:home"))
        self.assertContains(r, 'id="ajuda-overlay"')
        self.assertContains(r, "data-modal")
        self.assertContains(r, "Como o GranaGo organiza seu dinheiro")
        self.assertContains(r, "O GranaGo organiza seu dinheiro de forma simples")
        self.assertContains(r, "Ir para a Visão geral")
        self.assertContains(r, "Lance uma transação ou importe o extrato")
        self.assertContains(r, "Tem duas formas de adicionar seus dados ao GranaGo")
        self.assertContains(r, "Adicionar uma transação")
        self.assertContains(r, "Importar seu extrato")
        self.assertContains(r, ">Organize<")
        self.assertContains(r, "Como corrigir uma categoria")
        self.assertContains(r, "Como funcionam as transferências")
        self.assertContains(r, "alterá-la diretamente na transação")
        self.assertContains(r, "não é considerada receita nem despesa")
        self.assertContains(r, "Transferência = dinheiro de uma conta para outra.")
        self.assertContains(r, "Ir para transações")
        self.assertContains(r, 'data-ajuda-abrir="mapa"')
        self.assertContains(r, 'data-ajuda-abrir="adicionar-dados"')
        self.assertContains(r, 'data-ajuda-abrir="transacao"')
        self.assertContains(r, 'data-ajuda-abrir="corrigir-categoria"')
        self.assertContains(r, 'data-ajuda-abrir="transferencia"')
        self.assertContains(r, 'data-ajuda-abrir="cartao"')
        self.assertContains(r, 'data-ajuda-abrir="resultado"')
        self.assertContains(r, 'data-ajuda-abrir="pagar-fatura"')
        self.assertContains(r, "Como funciona uma transação")
        self.assertContains(r, "três tipos principais")
        self.assertContains(r, "registra um gasto")
        self.assertContains(r, "Como funciona o resultado")
        self.assertContains(r, "Como pagar a fatura")
        self.assertContains(r, "receitas − despesas")
        self.assertContains(r, "conta padrão do cartão")
        self.assertContains(r, "Ir para cartões")
        self.assertContains(r, reverse("cartoes:home"))
        self.assertContains(r, "Saldo das contas")
        self.assertNotContains(r, "Patrimônio disponível")
        self.assertNotContains(r, "Como o GranaGo funciona")
        self.assertContains(r, "nada é gravado antes disso")
        self.assertContains(r, "Buscar na ajuda")
        self.assertContains(r, 'id="ajuda-titulo"')
        self.assertContains(r, ">Ajuda<")
        self.assertNotContains(r, ">Tutoriais<")
        self.assertContains(r, 'data-ajuda-grupo="organize"')
        self.assertContains(r, "fa-chevron-right")
        self.assertContains(r, "Leia também")
        self.assertContains(r, "data-modal-close")

    def test_deep_link_query_nao_quebra_pagina(self):
        r = self.client.get(reverse("relatorios:home"), {"ajuda": "cartao"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="ajuda-overlay"')
        self.assertContains(r, 'id="ajuda-artigo-cartao"')
        self.assertContains(r, "Como funciona o cartão de crédito")
        self.assertContains(r, "o dinheiro ainda não sai da sua conta")
        self.assertContains(r, "Compra → Fatura → Pagamento → Saída da conta")
        self.assertContains(r, "conta padrão do cartão")

    def test_deep_link_artigos_novos(self):
        for artigo_id, trecho in (
            ("corrigir-categoria", 'id="ajuda-artigo-corrigir-categoria"'),
            ("transferencia", 'id="ajuda-artigo-transferencia"'),
            ("resultado", 'id="ajuda-artigo-resultado"'),
            ("pagar-fatura", 'id="ajuda-artigo-pagar-fatura"'),
            ("transacao", 'id="ajuda-artigo-transacao"'),
        ):
            r = self.client.get(reverse("relatorios:home"), {"ajuda": artigo_id})
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, trecho)

    def test_artigo_resultado_cta_fecha_drawer(self):
        r = self.client.get(reverse("relatorios:home"), {"ajuda": "resultado"})
        self.assertContains(r, "Como funciona o resultado")
        self.assertContains(r, "não significa")
        self.assertContains(r, "Saldo das contas")
        self.assertContains(r, "perguntas diferentes")
        self.assertNotContains(r, "Patrimônio disponível")
        self.assertContains(r, "data-modal-close")
        self.assertContains(r, ">Entendi<")

    def test_leia_tambem_declarativo(self):
        mapa = artigo_por_id("mapa")
        html = render_to_string(
            "usuarios/ajuda/partials/leia_tambem.html",
            {"artigo": mapa},
        )
        self.assertIn("Leia também", html)
        self.assertIn('data-ajuda-abrir="transacao"', html)
        self.assertIn('data-ajuda-abrir="cartao"', html)
        self.assertNotIn('data-ajuda-abrir="mapa"', html)

        transacao = artigo_por_id("transacao")
        html_tx = render_to_string(
            "usuarios/ajuda/partials/leia_tambem.html",
            {"artigo": transacao},
        )
        self.assertIn('data-ajuda-abrir="adicionar-dados"', html_tx)
        self.assertIn('data-ajuda-abrir="transferencia"', html_tx)
        self.assertIn('data-ajuda-abrir="resultado"', html_tx)
        self.assertNotIn('data-ajuda-abrir="transacao"', html_tx)

        cartao = artigo_por_id("cartao")
        html_cartao = render_to_string(
            "usuarios/ajuda/partials/leia_tambem.html",
            {"artigo": cartao},
        )
        self.assertIn('data-ajuda-abrir="pagar-fatura"', html_cartao)
        self.assertNotIn('data-ajuda-abrir="cartao"', html_cartao.split("Leia também", 1)[-1])

        pagar = artigo_por_id("pagar-fatura")
        html_pagar = render_to_string(
            "usuarios/ajuda/partials/leia_tambem.html",
            {"artigo": pagar},
        )
        self.assertIn('data-ajuda-abrir="cartao"', html_pagar)
        self.assertNotIn('data-ajuda-abrir="pagar-fatura"', html_pagar)

        vazio = replace(mapa, relacionados=())
        html_vazio = render_to_string(
            "usuarios/ajuda/partials/leia_tambem.html",
            {"artigo": vazio},
        )
        self.assertNotIn("Leia também", html_vazio)

        invalido = replace(mapa, relacionados=("mapa", "nao-existe", "cartao"))
        html_invalido = render_to_string(
            "usuarios/ajuda/partials/leia_tambem.html",
            {"artigo": invalido},
        )
        self.assertIn("Leia também", html_invalido)
        self.assertIn('data-ajuda-abrir="cartao"', html_invalido)
        self.assertNotIn("nao-existe", html_invalido)
        self.assertEqual(
            [rel.id for rel in invalido.artigos_relacionados()],
            ["cartao"],
        )

    def test_busca_normaliza_acentos(self):
        self.assertEqual(normalizar_texto_ajuda("cartão"), "cartao")
        self.assertEqual(normalizar_texto_ajuda("orçamento"), "orcamento")
        casos = (
            ("cartao", "cartao", "cartão"),
            ("transferencia", "transferencia", "transferência"),
            ("mapa", "orcamento", "orçamento"),
            ("adicionar-dados", "transacao", "transação"),
            ("resultado", "resultado", "resultado"),
            ("pagar-fatura", "fatura", "fatura"),
            ("pagar-fatura", "cartao", "cartão"),
            ("transacao", "transacao", "transação"),
            ("transacao", "receita", "receita"),
            ("transacao", "despesa", "despesa"),
            ("transacao", "transferencia", "transferência"),
            ("transacao", "lancamento", "lançamento"),
        )
        for artigo_id, sem_acento, com_acento in casos:
            artigo = artigo_por_id(artigo_id)
            self.assertTrue(artigo_corresponde_busca(artigo, sem_acento), sem_acento)
            self.assertTrue(artigo_corresponde_busca(artigo, com_acento), com_acento)
        self.assertTrue(artigo_corresponde_busca(artigo_por_id("cartao"), "cartao"))
        self.assertTrue(artigo_corresponde_busca(artigo_por_id("cartao"), "cartão"))
        self.assertFalse(artigo_corresponde_busca(artigo_por_id("cartao"), "zzzz"))

    def test_js_preserva_busca_ao_voltar(self):
        from pathlib import Path

        js = Path("usuarios/static/usuarios/js/ajuda.js").read_text(encoding="utf-8")
        inicio = js.index("function mostrarHome()")
        fim = js.index("function abrirArtigo")
        bloco = js[inicio:fim]
        self.assertIn('filtrar(busca ? busca.value : "")', bloco)
        self.assertNotIn('busca.value = ""', bloco)
        self.assertIn('.normalize("NFD")', js)

    def test_fatura_detalhe_tem_link_contextual(self):
        from datetime import date

        from cartoes.models import Fatura

        conta = self.criar_conta(self.user)
        cartao = self.criar_cartao(self.user, conta)
        fatura = Fatura.objects.create(
            usuario=self.user,
            cartao=cartao,
            competencia=date(2026, 8, 1),
            data_fechamento=date(2026, 8, 10),
            data_vencimento=date(2026, 8, 20),
            data_inicio_compras=date(2026, 7, 11),
            data_fim_compras=date(2026, 8, 10),
        )
        r = self.client.get(
            reverse("cartoes:fatura_detalhe", args=[cartao.id, fatura.id])
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "?ajuda=pagar-fatura")
        self.assertContains(r, "Como pagar a fatura →")


class DicaCartaoVersionadaTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("dica@test.com")
        self.client.force_login(self.user)
        self.perfil, _ = Perfil.objects.get_or_create(usuario=self.user)

    def test_v1_aparece_depois_some_e_v2_reaparece(self):
        self.assertTrue(deve_mostrar_dica(self.perfil, "cartao"))
        r = self.client.get(reverse("cartoes:home"))
        self.assertContains(r, DICAS["cartao"].titulo)
        self.assertContains(r, "?ajuda=cartao")

        resp = self.client.post(
            reverse("usuarios:dica_dispensar"),
            data=json.dumps({"dica_id": "cartao"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.perfil.refresh_from_db()
        self.assertEqual(self.perfil.dicas_dispensadas.get("cartao"), 1)
        self.assertFalse(deve_mostrar_dica(self.perfil, "cartao"))

        r2 = self.client.get(reverse("cartoes:home"))
        self.assertNotContains(r2, DICAS["cartao"].titulo)

        original = DICAS["cartao"]
        DICAS["cartao"] = replace(original, versao=2)
        try:
            self.perfil.refresh_from_db()
            self.assertTrue(deve_mostrar_dica(self.perfil, "cartao"))
            marcar_dica_dispensada(self.perfil, "cartao")
            self.perfil.refresh_from_db()
            self.assertEqual(self.perfil.dicas_dispensadas.get("cartao"), 2)
            self.assertFalse(deve_mostrar_dica(self.perfil, "cartao"))
        finally:
            DICAS["cartao"] = original

    def test_context_tip_shown_no_primeiro_get(self):
        self.client.get(reverse("cartoes:home"))
        self.assertTrue(
            ProdutoEvento.objects.filter(usuario=self.user, evento="context_tip_shown").exists()
        )
