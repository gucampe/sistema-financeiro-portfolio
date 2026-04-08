import json
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta

from transacoes.models import Transacao


class ImportarOfxConfirmarViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        cls.user = User.objects.create_user(
            email="confirm@test.local",
            password="secret",
            nome="Confirm User",
        )
        cls.outro = User.objects.create_user(
            email="outro_confirm@test.local",
            password="secret",
            nome="Outro",
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user,
            nome="Conta confirm",
            tipo="corrente",
        )
        cls.conta_outro = Conta.objects.create(
            usuario=cls.outro,
            nome="Conta outro",
            tipo="corrente",
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user,
            nome="Cat desp confirm",
            tipo="despesa",
            cor="#EF4444",
            padrao=False,
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user,
            nome="Cat rec confirm",
            tipo="receita",
            cor="#10B981",
            padrao=False,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.url = reverse("transacoes:importar_ofx_confirmar")

    def _post_json(self, payload):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_requer_login(self):
        r = self._post_json({"conta_id": self.conta.pk, "linhas": []})
        self.assertEqual(r.status_code, 302)

    def test_json_invalido_400(self):
        self.client.force_login(self.user)
        r = self.client.post(
            self.url,
            data="{nao json",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_lista_vazia_ok(self):
        self.client.force_login(self.user)
        r = self._post_json({"conta_id": self.conta.pk, "linhas": []})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"status": "ok", "criadas": 0})

    def test_cria_duas_transacoes(self):
        self.client.force_login(self.user)
        payload = {
            "conta_id": self.conta.pk,
            "linhas": [
                {
                    "indice": 0,
                    "data": "2024-03-01",
                    "valor": "10.50",
                    "tipo": "despesa",
                    "descricao": "Item A",
                    "categoria_id": self.cat_d.id,
                    "ofx_fitid": "fit-a",
                },
                {
                    "indice": 1,
                    "data": "2024-03-02",
                    "valor": "100.00",
                    "tipo": "receita",
                    "descricao": "Item B",
                    "categoria_id": self.cat_r.id,
                    "ofx_fitid": "fit-b",
                },
            ],
        }
        r = self._post_json(payload)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["criadas"], 2)
        self.assertEqual(Transacao.objects.filter(conta=self.conta).count(), 2)
        ta = Transacao.objects.get(ofx_fitid="fit-a")
        self.assertEqual(ta.valor, Decimal("10.50"))
        self.assertEqual(ta.tipo, "despesa")

    def test_conta_inexistente_404(self):
        self.client.force_login(self.user)
        r = self._post_json(
            {
                "conta_id": 99999,
                "linhas": [
                    {
                        "data": "2024-01-01",
                        "valor": "1.00",
                        "tipo": "despesa",
                        "descricao": "X",
                        "categoria_id": self.cat_d.id,
                    }
                ],
            }
        )
        self.assertEqual(r.status_code, 404)

    def test_categoria_receita_em_despesa_400(self):
        self.client.force_login(self.user)
        r = self._post_json(
            {
                "conta_id": self.conta.pk,
                "linhas": [
                    {
                        "data": "2024-01-01",
                        "valor": "1.00",
                        "tipo": "despesa",
                        "descricao": "X",
                        "categoria_id": self.cat_r.id,
                    }
                ],
            }
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("erros", r.json())

    def test_ajuste_com_categoria_receita_ok(self):
        self.client.force_login(self.user)
        r = self._post_json(
            {
                "conta_id": self.conta.pk,
                "linhas": [
                    {
                        "data": "2024-06-01",
                        "valor": "0.00",
                        "tipo": "ajuste",
                        "descricao": "Zeragem OFX",
                        "categoria_id": self.cat_r.id,
                    }
                ],
            }
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["criadas"], 1)
        t = Transacao.objects.get(conta=self.conta, tipo="ajuste")
        self.assertEqual(t.categoria_id, self.cat_r.id)

    def test_fitid_repetido_no_envio_chave_diferente_importa_segunda_sem_fitid(self):
        """Mesmo FITID com lançamentos distintos: primeira mantém FITID, segunda grava sem FITID."""
        self.client.force_login(self.user)
        linha = {
            "data": "2024-01-01",
            "valor": "1.00",
            "tipo": "despesa",
            "descricao": "A",
            "categoria_id": self.cat_d.id,
            "ofx_fitid": "dup",
        }
        r = self._post_json(
            {
                "conta_id": self.conta.pk,
                "linhas": [linha, {**linha, "descricao": "B"}],
            }
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["criadas"], 2)
        com_fitid = Transacao.objects.get(ofx_fitid="dup")
        self.assertEqual(com_fitid.descricao, "A")
        sem_fitid = Transacao.objects.filter(conta=self.conta, ofx_fitid__isnull=True).get(
            descricao="B"
        )
        self.assertIsNone(sem_fitid.ofx_fitid)

    def test_fitid_repetido_no_envio_mesma_chave_importa_com_segunda_sem_fitid(self):
        self.client.force_login(self.user)
        linha = {
            "data": "2024-01-01",
            "valor": "1.00",
            "tipo": "despesa",
            "descricao": "Igual",
            "categoria_id": self.cat_d.id,
            "ofx_fitid": "dup-exato",
        }
        r = self._post_json(
            {
                "conta_id": self.conta.pk,
                "linhas": [linha, {**linha, "indice": 1}],
            }
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["criadas"], 2)
        self.assertEqual(
            Transacao.objects.filter(conta=self.conta, ofx_fitid="dup-exato").count(),
            1,
        )
        self.assertEqual(
            Transacao.objects.filter(conta=self.conta, descricao="Igual", ofx_fitid__isnull=True).count(),
            1,
        )

    def test_fitid_no_banco_chave_diferente_importa_sem_conflito(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_d,
            tipo="despesa",
            valor=Decimal("42.50"),
            descricao="Existente",
            data="2024-01-15",
            ofx_fitid="sample-fitid-1",
        )
        self.client.force_login(self.user)
        r = self._post_json(
            {
                "conta_id": self.conta.pk,
                "linhas": [
                    {
                        "data": "2024-01-15",
                        "valor": "42.50",
                        "tipo": "despesa",
                        "descricao": "Outra descrição",
                        "categoria_id": self.cat_d.id,
                        "ofx_fitid": "sample-fitid-1",
                    }
                ],
            }
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["criadas"], 1)
        nova = Transacao.objects.get(conta=self.conta, descricao="Outra descrição")
        self.assertIsNone(nova.ofx_fitid)
        self.assertTrue(
            Transacao.objects.filter(conta=self.conta, ofx_fitid="sample-fitid-1").exists()
        )

    def test_fitid_ja_existe_no_banco_mesma_chave_importa_sem_fitid(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_d,
            tipo="despesa",
            valor=Decimal("99.00"),
            descricao="Pix igual",
            data="2024-02-01",
            ofx_fitid="fit-exato",
        )
        self.client.force_login(self.user)
        r = self._post_json(
            {
                "conta_id": self.conta.pk,
                "linhas": [
                    {
                        "data": "2024-02-01",
                        "valor": "99.00",
                        "tipo": "despesa",
                        "descricao": "Pix igual",
                        "categoria_id": self.cat_d.id,
                        "ofx_fitid": "fit-exato",
                    }
                ],
            }
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["criadas"], 1)
        nova = Transacao.objects.get(conta=self.conta, descricao="Pix igual", ofx_fitid__isnull=True)
        self.assertIsNone(nova.ofx_fitid)
        self.assertEqual(
            Transacao.objects.filter(conta=self.conta, ofx_fitid="fit-exato").count(),
            1,
        )

    def test_linha_invalida_nao_reserva_fitid_para_proxima(self):
        """
        Linha com erro não deve registrar FITID no lote; a seguinte com o mesmo FITID deve poder passar
        se a primeira for corrigida — aqui a segunda é válida e a primeira inválida (valor ruim).
        """
        self.client.force_login(self.user)
        r = self._post_json(
            {
                "conta_id": self.conta.pk,
                "linhas": [
                    {
                        "indice": 0,
                        "data": "2024-01-01",
                        "valor": "não-numérico",
                        "tipo": "despesa",
                        "descricao": "Ruim",
                        "categoria_id": self.cat_d.id,
                        "ofx_fitid": "shared-fit",
                    },
                    {
                        "indice": 1,
                        "data": "2024-01-02",
                        "valor": "5.00",
                        "tipo": "despesa",
                        "descricao": "Boa",
                        "categoria_id": self.cat_d.id,
                        "ofx_fitid": "shared-fit",
                    },
                ],
            }
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("0", r.json()["erros"])
        self.assertNotIn("1", r.json().get("erros", {}))
