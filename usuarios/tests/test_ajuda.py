"""Testes de orientação: copy, empty states, eventos, Ajuda e dica versionada."""

from __future__ import annotations

import json
from dataclasses import replace

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contas.models import Conta
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

    def test_contas_empty_explica_porque(self):
        r = self.client.get(reverse("contas:home"))
        self.assertContains(r, "Contas são onde o dinheiro está")

    def test_cartoes_empty_credito_nao_e_conta(self):
        r = self.client.get(reverse("cartoes:home"))
        self.assertContains(r, "Cartão de crédito não é uma conta")

    def test_dashboard_empty_conta(self):
        r = self.client.get(reverse("relatorios:home"))
        self.assertContains(r, "Contas são onde o dinheiro está")


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

    def test_catalogo_mvp_tem_tres_artigos(self):
        self.assertEqual({a.id for a in ARTIGOS}, {"mapa", "adicionar-dados", "cartao"})
        self.assertIsNotNone(artigo_por_id("cartao"))
        self.assertIsNone(artigo_por_id("categoria"))

    def test_drawer_no_html_autenticado(self):
        r = self.client.get(reverse("relatorios:home"))
        self.assertContains(r, 'id="ajuda-overlay"')
        self.assertContains(r, "data-modal")
        self.assertContains(r, "Como o GranaGo organiza seu dinheiro")
        self.assertContains(r, 'data-ajuda-abrir="mapa"')
        self.assertContains(r, 'data-ajuda-abrir="adicionar-dados"')
        self.assertContains(r, 'data-ajuda-abrir="cartao"')
        self.assertContains(r, "Buscar na ajuda")
        self.assertContains(r, ">Ajuda<")
        self.assertNotContains(r, ">Tutoriais<")

    def test_deep_link_query_nao_quebra_pagina(self):
        r = self.client.get(reverse("relatorios:home"), {"ajuda": "cartao"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'id="ajuda-overlay"')
        self.assertContains(r, 'id="ajuda-artigo-cartao"')


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
