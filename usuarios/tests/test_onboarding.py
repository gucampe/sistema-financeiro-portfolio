"""Testes do onboarding leve — Central de Primeiros Passos."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from cartoes.models import Cartao
from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao
from transacoes.services import criar_transacao_saldo_inicial
from usuarios.models import Perfil
from usuarios.services.onboarding import (
    deve_mostrar_atalho_primeiros_passos,
    progresso_primeiros_passos,
)

User = get_user_model()


class OnboardingTestMixin:
    """Fixtures compartilhadas para cenários de onboarding."""

    def criar_usuario(self, email: str, nome: str = "Test User") -> User:
        return User.objects.create_user(email=email, nome=nome, password="x")

    def categoria_despesa(self, user: User) -> Categoria:
        cat, _ = Categoria.objects.get_or_create(
            usuario=user,
            nome=f"Despesa {user.pk}",
            tipo="despesa",
            defaults={"ativa": True, "cor": "#EF4444"},
        )
        return cat

    def categoria_receita(self, user: User) -> Categoria:
        cat, _ = Categoria.objects.get_or_create(
            usuario=user,
            nome=f"Receita {user.pk}",
            tipo="receita",
            defaults={"ativa": True, "cor": "#10B981"},
        )
        return cat

    def criar_conta(self, user: User, *, ativa: bool = True, nome: str = "Conta") -> Conta:
        return Conta.objects.create(
            usuario=user,
            nome=f"{nome} {user.pk}",
            tipo="corrente",
            ativa=ativa,
        )

    def criar_movimentacao(
        self,
        user: User,
        conta: Conta,
        *,
        tipo: str = "despesa",
        cat: Categoria | None = None,
    ) -> Transacao:
        if cat is None:
            cat = self.categoria_despesa(user) if tipo == "despesa" else self.categoria_receita(user)
        return Transacao.objects.create(
            usuario=user,
            conta=conta,
            categoria=cat,
            tipo=tipo,
            valor=Decimal("10.00"),
            data=timezone.localdate(),
            descricao="Movimentação teste",
        )

    def criar_cartao(self, user: User, conta: Conta) -> Cartao:
        return Cartao.objects.create(
            usuario=user,
            nome=f"Cartão {user.pk}",
            limite=Decimal("1000.00"),
            dia_fechamento=1,
            dia_vencimento=10,
            conta_padrao=conta,
            ativa=True,
        )


class PrimeirosPassosServiceTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("onboarding-svc@test.local")
        self.cat_desp = self.categoria_despesa(self.user)

    def _progresso(self, user=None):
        return progresso_primeiros_passos(user or self.user)

    def test_usuario_novo_zero_porcento(self):
        p = self._progresso()
        self.assertEqual(p["concluidas"], 0)
        self.assertEqual(p["total"], 3)
        self.assertEqual(p["percentual"], 0)
        self.assertFalse(p["essencial_completo"])
        self.assertFalse(p["total_completo"])

    def test_conta_inativa_nao_conclui_etapa_conta(self):
        self.criar_conta(self.user, ativa=False)
        p = self._progresso()
        self.assertFalse(next(e for e in p["etapas"] if e["id"] == "conta")["concluida"])
        self.assertEqual(p["concluidas"], 0)

    def test_saldo_inicial_nao_conta_como_movimentacao(self):
        conta = self.criar_conta(self.user)
        criar_transacao_saldo_inicial(
            usuario=self.user,
            conta=conta,
            valor=Decimal("500.00"),
            data=timezone.localdate(),
        )
        p = self._progresso()
        self.assertTrue(next(e for e in p["etapas"] if e["id"] == "conta")["concluida"])
        self.assertFalse(next(e for e in p["etapas"] if e["id"] == "movimentacao")["concluida"])
        self.assertEqual(p["concluidas"], 1)
        self.assertEqual(p["percentual"], 33)

    def test_ajuste_manual_nao_conta_como_movimentacao(self):
        conta = self.criar_conta(self.user)
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=self.cat_desp,
            tipo="ajuste",
            valor=Decimal("100.00"),
            data=timezone.localdate(),
            descricao="Ajuste manual",
        )
        p = self._progresso()
        self.assertFalse(next(e for e in p["etapas"] if e["id"] == "movimentacao")["concluida"])

    def test_despesa_conclui_movimentacao(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta, tipo="despesa")
        p = self._progresso()
        self.assertTrue(next(e for e in p["etapas"] if e["id"] == "movimentacao")["concluida"])
        self.assertTrue(p["essencial_completo"])

    def test_receita_conclui_movimentacao(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta, tipo="receita")
        p = self._progresso()
        self.assertTrue(next(e for e in p["etapas"] if e["id"] == "movimentacao")["concluida"])

    def test_cartao_ativo_conclui_etapa_cartao(self):
        conta = self.criar_conta(self.user)
        self.criar_cartao(self.user, conta)
        p = self._progresso()
        self.assertTrue(next(e for e in p["etapas"] if e["id"] == "cartao")["concluida"])

    def test_tres_de_tres_total_completo(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)
        self.criar_cartao(self.user, conta)
        p = self._progresso()
        self.assertEqual(p["concluidas"], 3)
        self.assertEqual(p["percentual"], 100)
        self.assertTrue(p["essencial_completo"])
        self.assertTrue(p["total_completo"])

    def test_dois_de_tres_sem_cartao(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)
        p = self._progresso()
        self.assertEqual(p["concluidas"], 2)
        self.assertEqual(p["percentual"], 67)
        self.assertTrue(p["essencial_completo"])
        self.assertFalse(p["total_completo"])

    def test_atalho_permanece_quando_essencial_completo(self):
        self.assertTrue(deve_mostrar_atalho_primeiros_passos(self.user))
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)
        self.assertTrue(deve_mostrar_atalho_primeiros_passos(self.user))

    def test_atalho_some_quando_usuario_pede_para_ocultar(self):
        perfil, _ = Perfil.objects.get_or_create(usuario=self.user)
        perfil.ocultar_atalho_primeiros_passos = True
        perfil.save(update_fields=["ocultar_atalho_primeiros_passos"])
        self.assertFalse(deve_mostrar_atalho_primeiros_passos(self.user))

    def test_apenas_tres_etapas_sem_meta(self):
        p = self._progresso()
        self.assertEqual(len(p["etapas"]), 3)
        ids = {e["id"] for e in p["etapas"]}
        self.assertEqual(ids, {"conta", "movimentacao", "cartao"})

    def test_ctas_das_etapas(self):
        p = self._progresso()
        by_id = {e["id"]: e for e in p["etapas"]}
        self.assertEqual(by_id["conta"]["cta_acao"], "link_conta")
        self.assertEqual(by_id["movimentacao"]["cta_acao"], "link_transacoes")
        self.assertIn("extrato", by_id["movimentacao"]["descricao"])
        self.assertEqual(by_id["cartao"]["cta_acao"], "link_cartao")
        self.assertFalse(by_id["cartao"]["obrigatoria"])

    def test_progresso_isolado_por_usuario(self):
        outro = self.criar_usuario("onboarding-outro@test.local")
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)

        p_user = self._progresso(self.user)
        p_outro = self._progresso(outro)

        self.assertEqual(p_user["concluidas"], 2)
        self.assertEqual(p_outro["concluidas"], 0)


class PrimeirosPassosFluxoIntegradoTests(OnboardingTestMixin, TestCase):
    """Simula a jornada do usuário etapa a etapa."""

    def setUp(self):
        self.user = self.criar_usuario("fluxo-onb@test.local")
        self.client = Client()
        self.client.force_login(self.user)
        self.home_url = reverse("relatorios:home")
        self.page_url = reverse("usuarios:primeiros_passos")

    def _get_progresso_json(self, response) -> dict:
        import json
        import re

        match = re.search(
            r'<script id="primeiros-passos-data" type="application/json">(.*?)</script>',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(match, "JSON primeiros-passos-data não encontrado")
        return json.loads(match.group(1))

    def _banner_conclusao_visivel(self, response) -> bool:
        import re

        html = response.content.decode()
        match = re.search(
            r'<section[^>]*id="pp-done-banner"[^>]*class="([^"]*)"',
            html,
        )
        if not match:
            return False
        return " hidden " not in f" {match.group(1)} "

    def test_jornada_completa_dashboard_e_pagina(self):
        # 1 — Usuário novo: FAB e progresso 0/3 no dashboard
        r_home = self.client.get(self.home_url)
        self.assertEqual(r_home.status_code, 200)
        self.assertContains(r_home, 'id="pp-fab"')
        self.assertContains(r_home, "0/3")
        self.assertContains(r_home, reverse("usuarios:primeiros_passos"))

        r_page = self.client.get(self.page_url)
        self.assertEqual(r_page.status_code, 200)
        self.assertContains(r_page, "0 de 3 etapas concluídas")
        self.assertFalse(self._banner_conclusao_visivel(r_page))

        # 2 — Cria conta: 1/3
        self.criar_conta(self.user)
        p = progresso_primeiros_passos(self.user)
        self.assertEqual(p["concluidas"], 1)

        r_page = self.client.get(self.page_url)
        self.assertContains(r_page, "1 de 3 etapas concluídas")
        self.assertContains(r_page, f'{reverse("contas:home")}?nova=1')
        self.assertContains(r_page, f'{reverse("transacoes:historico")}?nova=1')
        self.assertContains(r_page, f'{reverse("transacoes:historico")}?importar=1')
        self.assertContains(r_page, f'{reverse("cartoes:home")}?nova=1')
        self.assertContains(r_page, "data-pp-skip-cartao")

        # 3 — Movimentação: essencial completo, botão ocultar visível; FAB permanece
        conta = Conta.objects.get(usuario=self.user, ativa=True)
        self.criar_movimentacao(self.user, conta)
        r_page = self.client.get(self.page_url)
        self.assertContains(r_page, "2 de 3 etapas concluídas")
        self.assertContains(r_page, "pp-btn-dismiss-essencial")
        r_home = self.client.get(self.home_url)
        self.assertContains(r_home, 'id="pp-fab"')

        # 4 — Cartão: total completo + banner; FAB some só após “não mostrar”
        self.criar_cartao(self.user, conta)
        r_page = self.client.get(self.page_url)
        self.assertContains(r_page, "3 de 3 etapas concluídas")
        self.assertTrue(self._banner_conclusao_visivel(r_page))
        self.assertContains(r_page, "pp-btn-dismiss-done")

        r_home = self.client.get(self.home_url)
        self.assertContains(r_home, 'id="pp-fab"')
        data = self._get_progresso_json(r_home)
        self.assertTrue(data["total_completo"])
        self.assertEqual(data["concluidas"], 3)

        self.client.post(reverse("usuarios:primeiros_passos_ocultar_atalho"))
        r_home = self.client.get(self.home_url)
        self.assertNotContains(r_home, 'id="pp-fab"')


class PrimeirosPassosDashboardTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("dash-onb@test.local")
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("relatorios:home")

    def test_dashboard_inclui_assets_onboarding(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "primeiros-passos.css")
        self.assertContains(response, "primeiros-passos.js")
        self.assertContains(response, "primeiros-passos-data")
        self.assertContains(response, f'data-pp-user-id="{self.user.pk}"')

    def test_login_nao_bloqueia_acesso_ao_dashboard(self):
        client = Client()
        user = self.criar_usuario("login-livre@test.local")
        response = client.post(
            reverse("usuarios:login"),
            {"email": "login-livre@test.local", "senha": "x"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("relatorios:home"))

    def test_dashboard_mantem_fab_apos_essencial(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)
        response = self.client.get(self.url)
        self.assertContains(response, 'id="pp-fab"')
        self.assertContains(response, "primeiros-passos.js")

    def test_ocultar_atalho_persiste_no_perfil(self):
        url = reverse("usuarios:primeiros_passos_ocultar_atalho")
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        perfil = Perfil.objects.get(usuario=self.user)
        self.assertTrue(perfil.ocultar_atalho_primeiros_passos)
        home = self.client.get(self.url)
        self.assertNotContains(home, 'id="pp-fab"')


class PrimeirosPassosStatusViewTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("pp-status@test.local")
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("usuarios:primeiros_passos_status")

    def test_endpoint_retorna_json_progresso(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["concluidas"], 0)
        self.assertEqual(data["total"], 3)
        self.assertIn("etapas", data)
        self.assertIn("percentual", data)
        self.assertIn("essencial_completo", data)
        self.assertIn("total_completo", data)

    def test_endpoint_reflete_dados_reais(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)
        data = self.client.get(self.url).json()
        self.assertEqual(data["concluidas"], 2)
        self.assertTrue(data["essencial_completo"])
        self.assertFalse(data["total_completo"])

    def test_endpoint_requer_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class PrimeirosPassosPageViewTests(OnboardingTestMixin, TestCase):
    def setUp(self):
        self.user = self.criar_usuario("pp-page@test.local")
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("usuarios:primeiros_passos")

    def test_pagina_renders_estrutura(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Seu espaço financeiro está quase pronto")
        self.assertContains(response, "Configuração inicial")
        self.assertContains(response, "Conta financeira")
        self.assertContains(response, "Primeira movimentação")
        self.assertContains(response, "Cartão de crédito")
        self.assertContains(response, "Adicionar transação")
        self.assertContains(response, "Importar extrato")
        self.assertContains(response, 'data-pp-user-id')
        self.assertContains(response, "Voltar ao dashboard")
        self.assertNotContains(response, "Meta financeira")

    def test_pagina_requer_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_etapas_concluidas_marcadas_na_pagina(self):
        conta = self.criar_conta(self.user)
        self.criar_movimentacao(self.user, conta)
        response = self.client.get(self.url)
        self.assertEqual(response.content.decode().count("Concluído"), 2)
        self.assertContains(response, "pp-btn-dismiss-essencial")
