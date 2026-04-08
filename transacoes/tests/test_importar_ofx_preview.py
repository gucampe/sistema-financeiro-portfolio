from pathlib import Path

from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta

from transacoes.models import Transacao

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_OFX = FIXTURES / "sample.ofx"


class ImportarOfxPreviewViewTests(TestCase):
    """POST multipart /transacoes/importar/ofx/preview/"""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        cls.user = User.objects.create_user(
            email="preview@test.local",
            password="secret",
            nome="Preview User",
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user,
            nome="Conta OFX",
            tipo="corrente",
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user,
            nome="Cat despesa preview",
            tipo="despesa",
            cor="#EF4444",
            padrao=False,
        )
        cls.cat_r = Categoria.objects.create(
            usuario=cls.user,
            nome="Cat receita preview",
            tipo="receita",
            cor="#10B981",
            padrao=False,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_requer_login(self):
        with open(SAMPLE_OFX, "rb") as fp:
            r = self.client.post(
                reverse("transacoes:importar_ofx_preview"),
                {"conta_id": self.conta.pk, "arquivo": fp},
            )
        self.assertEqual(r.status_code, 302)

    def test_sem_conta_id_400(self):
        self.client.force_login(self.user)
        with open(SAMPLE_OFX, "rb") as fp:
            r = self.client.post(
                reverse("transacoes:importar_ofx_preview"),
                {"arquivo": fp},
            )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["status"], "error")

    def test_sem_arquivo_400(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_ofx_preview"),
            {"conta_id": str(self.conta.pk)},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("OFX", r.json()["message"])

    def test_conta_inexistente_404(self):
        self.client.force_login(self.user)
        with open(SAMPLE_OFX, "rb") as fp:
            r = self.client.post(
                reverse("transacoes:importar_ofx_preview"),
                {"conta_id": "99999", "arquivo": fp},
            )
        self.assertEqual(r.status_code, 404)

    def test_ofx_invalido_400(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_ofx_preview"),
            {
                "conta_id": str(self.conta.pk),
                "arquivo": ("x.ofx", b"not ofx content", "application/octet-stream"),
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["status"], "error")

    def test_sample_ofx_200_estrutura(self):
        self.client.force_login(self.user)
        with open(SAMPLE_OFX, "rb") as fp:
            r = self.client.post(
                reverse("transacoes:importar_ofx_preview"),
                {"conta_id": str(self.conta.pk), "arquivo": fp},
            )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["conta_id"], self.conta.pk)
        self.assertEqual(len(data["linhas"]), 3)
        self.assertIn("categorias", data)
        self.assertIn("receita", data["categorias"])
        self.assertIn("despesa", data["categorias"])
        ids_d = {c["id"] for c in data["categorias"]["despesa"]}
        ids_r = {c["id"] for c in data["categorias"]["receita"]}
        self.assertIn(self.cat_d.id, ids_d)
        self.assertIn(self.cat_r.id, ids_r)
        self.assertEqual(
            data["categorias_chave_por_tipo_transacao"]["ajuste"],
            "receita",
        )
        # Primeira linha: despesa com FITID
        l0 = data["linhas"][0]
        self.assertEqual(l0["tipo"], "despesa")
        self.assertEqual(l0["ofx_fitid"], "sample-fitid-1")
        self.assertIn("duplicata_por_fitid", l0)

    def test_campo_file_alternativo(self):
        self.client.force_login(self.user)
        with open(SAMPLE_OFX, "rb") as fp:
            r = self.client.post(
                reverse("transacoes:importar_ofx_preview"),
                {"conta_id": str(self.conta.pk), "file": fp},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()["linhas"]), 3)

    def test_duplicata_fitid_no_json(self):
        Transacao.objects.create(
            usuario=self.user,
            conta=self.conta,
            categoria=self.cat_d,
            tipo="despesa",
            valor="42.50",
            descricao="PADARIA CENTRAL COMPRA DEB",
            data="2024-01-15",
            ofx_fitid="sample-fitid-1",
        )
        self.client.force_login(self.user)
        with open(SAMPLE_OFX, "rb") as fp:
            r = self.client.post(
                reverse("transacoes:importar_ofx_preview"),
                {"conta_id": str(self.conta.pk), "arquivo": fp},
            )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["linhas"][0]["duplicata_por_fitid"])
