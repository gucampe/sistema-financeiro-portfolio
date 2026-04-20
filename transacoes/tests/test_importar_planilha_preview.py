import io
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from openpyxl import Workbook

from categorias.models import Categoria
from contas.models import Conta

from transacoes.xlsx_parse import PLANILHA_CABECALHOS


def _bytes_planilha_valida():
    wb = Workbook()
    ws = wb.active
    ws.append(list(PLANILHA_CABECALHOS))
    ws.append([date(2024, 2, 1), "Compra teste", -25.50])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _upload_xlsx(nome="lanc.xlsx"):
    return SimpleUploadedFile(
        nome,
        _bytes_planilha_valida(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class ImportarPlanilhaPreviewViewTests(TestCase):
    """POST multipart /transacoes/importar/planilha/preview/"""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        cls.user = User.objects.create_user(
            email="planilha_preview@test.local",
            password="secret",
            nome="Planilha Preview",
        )
        cls.conta = Conta.objects.create(
            usuario=cls.user,
            nome="Conta planilha",
            tipo="corrente",
        )
        cls.cat_d = Categoria.objects.create(
            usuario=cls.user,
            nome="Cat despesa plan",
            tipo="despesa",
            cor="#EF4444",
            padrao=False,
        )

    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    def test_requer_login(self):
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {"conta_id": self.conta.pk, "arquivo": _upload_xlsx()},
        )
        self.assertEqual(r.status_code, 302)

    def test_sem_conta_id_400(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {"arquivo": _upload_xlsx()},
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["status"], "error")

    def test_sem_arquivo_400(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {"conta_id": str(self.conta.pk)},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("xlsx", r.json()["message"].lower())

    def test_extensao_invalida_400(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {
                "conta_id": str(self.conta.pk),
                "arquivo": SimpleUploadedFile("x.csv", b"a,b", content_type="text/csv"),
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("xlsx", r.json()["message"].lower())

    def test_conta_inexistente_404(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {
                "conta_id": "99999",
                "arquivo": _upload_xlsx(),
            },
        )
        self.assertEqual(r.status_code, 404)

    def test_planilha_ok_estrutura(self):
        self.client.force_login(self.user)
        r = self.client.post(
            reverse("transacoes:importar_planilha_preview"),
            {
                "conta_id": str(self.conta.pk),
                "arquivo": _upload_xlsx("lanc.xlsx"),
            },
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["conta_id"], self.conta.pk)
        self.assertEqual(len(data["linhas"]), 1)
        self.assertEqual(data["linhas"][0]["tipo"], "despesa")
        self.assertIn("categorias", data)
        ids_d = {c["id"] for c in data["categorias"]["despesa"]}
        self.assertIn(self.cat_d.id, ids_d)
        self.assertIsNone(data["linhas"][0]["ofx_fitid"])
