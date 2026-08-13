"""CRUD de contas — listagem, salvar, arquivar/reativar e isolamento."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from contas.models import Conta
from transacoes.models import Transacao

User = get_user_model()

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class ContasViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="contas-a@test.local", password="x", nome="Contas A"
        )
        self.other = User.objects.create_user(
            email="contas-b@test.local", password="x", nome="Contas B"
        )
        self.client.force_login(self.user)

    def _salvar(self, data, **extra):
        return self.client.post(reverse("contas:salvar"), data, **AJAX, **extra)

    def test_home_exige_login(self):
        self.client.logout()
        resp = self.client.get(reverse("contas:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_home_lista_ativas_e_arquivadas_do_usuario(self):
        ativa = Conta.objects.create(
            usuario=self.user, nome="Nubank", tipo="corrente", ativa=True
        )
        arquivada = Conta.objects.create(
            usuario=self.user, nome="Caixa antiga", tipo="poupanca", ativa=False
        )
        Conta.objects.create(
            usuario=self.other, nome="Alheia", tipo="corrente", ativa=True
        )

        resp = self.client.get(reverse("contas:home"))
        self.assertEqual(resp.status_code, 200)
        ativas = list(resp.context["contas_ativas"])
        arquivadas = list(resp.context["contas_arquivadas"])
        self.assertEqual([c.pk for c in ativas], [ativa.pk])
        self.assertEqual([c.pk for c in arquivadas], [arquivada.pk])
        self.assertTrue(hasattr(ativas[0], "saldo_atual"))

    def test_criar_conta_ajax(self):
        resp = self._salvar({"nome": "Carteira", "tipo": "carteira", "icone": "wallet"})
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "ok")
        conta = Conta.objects.get(pk=payload["id"])
        self.assertEqual(conta.usuario, self.user)
        self.assertEqual(conta.nome, "Carteira")
        self.assertEqual(conta.tipo, "carteira")
        self.assertTrue(conta.ativa)

    def test_criar_conta_com_saldo_inicial(self):
        resp = self._salvar(
            {
                "nome": "Corrente",
                "tipo": "corrente",
                "icone": "bank",
                "saldo_inicial": "1.250,50",
            }
        )
        self.assertEqual(resp.status_code, 200)
        conta = Conta.objects.get(pk=resp.json()["id"])
        self.assertEqual(conta.saldo_atual_calc, Decimal("1250.50"))
        self.assertTrue(
            Transacao.objects.filter(
                usuario=self.user, conta=conta, descricao="Saldo inicial"
            ).exists()
        )

    def test_editar_conta_nao_reaplica_saldo_inicial(self):
        conta = Conta.objects.create(
            usuario=self.user, nome="Original", tipo="corrente", ativa=True
        )
        resp = self._salvar(
            {
                "conta_id": str(conta.pk),
                "nome": "Renomeada",
                "tipo": "poupanca",
                "icone": "piggy",
                "saldo_inicial": "999,00",
            }
        )
        self.assertEqual(resp.status_code, 200)
        conta.refresh_from_db()
        self.assertEqual(conta.nome, "Renomeada")
        self.assertEqual(conta.tipo, "poupanca")
        self.assertEqual(conta.saldo_atual_calc, Decimal("0.00"))
        self.assertFalse(
            Transacao.objects.filter(usuario=self.user, conta=conta).exists()
        )

    def test_nome_duplicado_retorna_409(self):
        Conta.objects.create(
            usuario=self.user, nome="Nubank", tipo="corrente", ativa=True
        )
        resp = self._salvar({"nome": "Nubank", "tipo": "corrente"})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["status"], "erro")

    def test_nome_vazio_retorna_400(self):
        resp = self._salvar({"nome": "  ", "tipo": "corrente"})
        self.assertEqual(resp.status_code, 400)

    def test_tipo_invalido_retorna_400(self):
        resp = self._salvar({"nome": "X", "tipo": "bitcoin"})
        self.assertEqual(resp.status_code, 400)

    def test_salvar_sem_ajax_retorna_405(self):
        resp = self.client.post(
            reverse("contas:salvar"), {"nome": "X", "tipo": "corrente"}
        )
        self.assertEqual(resp.status_code, 405)

    def test_arquivar_e_reativar(self):
        conta = Conta.objects.create(
            usuario=self.user, nome="Arquivar", tipo="corrente", ativa=True
        )
        resp = self.client.post(reverse("contas:arquivar", kwargs={"id": conta.pk}))
        self.assertEqual(resp.status_code, 302)
        conta.refresh_from_db()
        self.assertFalse(conta.ativa)

        resp = self.client.post(reverse("contas:reativar", kwargs={"id": conta.pk}))
        self.assertEqual(resp.status_code, 302)
        conta.refresh_from_db()
        self.assertTrue(conta.ativa)

    def test_idor_nao_arquiva_conta_de_outro_usuario(self):
        alheia = Conta.objects.create(
            usuario=self.other, nome="Alheia", tipo="corrente", ativa=True
        )
        resp = self.client.post(reverse("contas:arquivar", kwargs={"id": alheia.pk}))
        self.assertEqual(resp.status_code, 404)
        alheia.refresh_from_db()
        self.assertTrue(alheia.ativa)

    def test_idor_nao_edita_conta_de_outro_usuario(self):
        alheia = Conta.objects.create(
            usuario=self.other, nome="Alheia", tipo="corrente", ativa=True
        )
        resp = self._salvar(
            {
                "conta_id": str(alheia.pk),
                "nome": "Invadida",
                "tipo": "corrente",
                "icone": "bank",
            }
        )
        self.assertEqual(resp.status_code, 404)
        alheia.refresh_from_db()
        self.assertEqual(alheia.nome, "Alheia")
