import json

from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta

from transacoes.models import Transacao


class ImportarPlanilhaConfirmarAliasTests(TestCase):
    """POST JSON no alias importar/planilha/confirmar/ (mesma view do OFX)."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        cls.user = User.objects.create_user(
            email="plan_confirm_alias@test.local",
            password="secret",
            nome="Alias",
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user,
            nome="Conta alias",
            tipo="corrente",
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user,
            nome="Cat desp alias",
            tipo="despesa",
            cor="#EF4444",
            padrao=False,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.url = reverse("transacoes:importar_planilha_confirmar")

    def test_cria_transacao_sem_fitid(self):
        self.client.force_login(self.user)
        payload = {
            "conta_id": self.conta.pk,
            "linhas": [
                {
                    "indice": 0,
                    "data": "2024-05-01",
                    "valor": "15.00",
                    "tipo": "despesa",
                    "descricao": "Via planilha alias",
                    "categoria_id": self.cat_d.id,
                },
            ],
        }
        r = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "criadas": 1})
        t = Transacao.objects.get(descricao="Via planilha alias")
        self.assertIsNone(t.ofx_fitid)
