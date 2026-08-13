"""CRUD de categorias — criar/editar, arquivar, exclusão com migração e isolamento."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao

User = get_user_model()

AJAX = {"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"}


@override_settings(ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"])
class CategoriasViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cat-a@test.local", password="x", nome="Cat A"
        )
        self.other = User.objects.create_user(
            email="cat-b@test.local", password="x", nome="Cat B"
        )
        self.client.force_login(self.user)

    def _post(self, name, data, **kwargs):
        return self.client.post(reverse(name), data, **AJAX, **kwargs)

    def test_home_exige_login(self):
        self.client.logout()
        resp = self.client.get(reverse("categorias:home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/login/", resp["Location"])

    def test_home_separa_ativas_arquivadas_por_tipo(self):
        desp = Categoria.objects.create(
            usuario=self.user, nome="Mercado", tipo="despesa", cor="#EF4444", ativa=True
        )
        rec = Categoria.objects.create(
            usuario=self.user, nome="Salário extra", tipo="receita", cor="#10B981", ativa=True
        )
        arq = Categoria.objects.create(
            usuario=self.user, nome="Velha", tipo="despesa", cor="#6B7280", ativa=False
        )
        Categoria.objects.create(
            usuario=self.other, nome="Alheia", tipo="despesa", cor="#EF4444", ativa=True
        )

        resp = self.client.get(reverse("categorias:home"))
        self.assertEqual(resp.status_code, 200)
        ativas_desp = list(resp.context["categorias_ativas_despesa"])
        ativas_rec = list(resp.context["categorias_ativas_receita"])
        arq_desp = list(resp.context["categorias_arquivadas_despesa"])
        self.assertIn(desp, ativas_desp)
        self.assertIn(rec, ativas_rec)
        self.assertIn(arq, arq_desp)
        self.assertFalse(any(c.usuario_id == self.other.pk for c in ativas_desp))

    def test_criar_categoria_ajax(self):
        resp = self._post(
            "categorias:adicionar",
            {
                "nome": "Farmácia",
                "tipo": "despesa",
                "icone": "fa-heart",
                "cor": "#EF4444",
            },
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.json()
        self.assertEqual(payload["status"], "ok")
        cat = Categoria.objects.get(pk=payload["id"])
        self.assertEqual(cat.usuario, self.user)
        self.assertFalse(cat.padrao)
        self.assertEqual(cat.nome, "Farmácia")

    def test_editar_categoria_propria(self):
        cat = Categoria.objects.create(
            usuario=self.user,
            nome="Cat QA Editavel",
            tipo="despesa",
            icone="fa-gamepad",
            cor="#4F46E5",
            ativa=True,
        )
        resp = self._post(
            "categorias:adicionar",
            {
                "categoria_id": str(cat.pk),
                "nome": "Cat QA Hobby",
                "tipo": "despesa",
                "icone": "fa-utensils",
                "cor": "#F59E0B",
            },
        )
        self.assertEqual(resp.status_code, 200)
        cat.refresh_from_db()
        self.assertEqual(cat.nome, "Cat QA Hobby")
        self.assertEqual(cat.icone, "fa-utensils")

    def test_nome_duplicado_mesmo_tipo_409(self):
        Categoria.objects.create(
            usuario=self.user, nome="Cat QA Dup", tipo="despesa", cor="#F59E0B", ativa=True
        )
        resp = self._post(
            "categorias:adicionar",
            {
                "nome": "Cat QA Dup",
                "tipo": "despesa",
                "icone": "fa-home",
                "cor": "#F59E0B",
            },
        )
        self.assertEqual(resp.status_code, 409)

    def test_arquivar_e_restaurar(self):
        cat = Categoria.objects.create(
            usuario=self.user, nome="Temp", tipo="despesa", cor="#6B7280", ativa=True
        )
        resp = self._post("categorias:arquivar", {"categoria_id": str(cat.pk)})
        self.assertEqual(resp.status_code, 200)
        cat.refresh_from_db()
        self.assertFalse(cat.ativa)

        resp = self._post("categorias:restaurar", {"categoria_id": str(cat.pk)})
        self.assertEqual(resp.status_code, 200)
        cat.refresh_from_db()
        self.assertTrue(cat.ativa)

    def test_excluir_bloqueada_se_ativa(self):
        cat = Categoria.objects.create(
            usuario=self.user, nome="Ativa", tipo="despesa", cor="#6B7280", ativa=True
        )
        resp = self.client.post(
            reverse("categorias:excluir", kwargs={"id": cat.pk}), **AJAX
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["reason"], "not_archived")
        self.assertTrue(Categoria.objects.filter(pk=cat.pk).exists())

    def test_excluir_bloqueada_se_em_uso(self):
        cat = Categoria.objects.create(
            usuario=self.user, nome="Usada", tipo="despesa", cor="#6B7280", ativa=False
        )
        conta = Conta.objects.create(
            usuario=self.user, nome="Conta", tipo="corrente", ativa=True
        )
        Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=cat,
            tipo="despesa",
            valor=Decimal("10.00"),
            data=timezone.localdate(),
            descricao="Uso",
        )
        resp = self.client.post(
            reverse("categorias:excluir", kwargs={"id": cat.pk}), **AJAX
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["reason"], "in_use")

    def test_excluir_arquivada_sem_uso(self):
        cat = Categoria.objects.create(
            usuario=self.user, nome="Lixo", tipo="despesa", cor="#6B7280", ativa=False
        )
        resp = self.client.post(
            reverse("categorias:excluir", kwargs={"id": cat.pk}), **AJAX
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Categoria.objects.filter(pk=cat.pk).exists())

    def test_excluir_com_migracao(self):
        origem = Categoria.objects.create(
            usuario=self.user, nome="Origem", tipo="despesa", cor="#6B7280", ativa=False
        )
        destino = Categoria.objects.create(
            usuario=self.user, nome="Destino", tipo="despesa", cor="#EF4444", ativa=True
        )
        conta = Conta.objects.create(
            usuario=self.user, nome="Conta", tipo="corrente", ativa=True
        )
        tx = Transacao.objects.create(
            usuario=self.user,
            conta=conta,
            categoria=origem,
            tipo="despesa",
            valor=Decimal("25.00"),
            data=timezone.localdate(),
            descricao="Migrar",
        )
        resp = self._post(
            "categorias:excluir_com_migracao",
            {
                "categoria_id": str(origem.pk),
                "nova_categoria_id": str(destino.pk),
            },
        )
        self.assertEqual(resp.status_code, 200)
        tx.refresh_from_db()
        self.assertEqual(tx.categoria_id, destino.pk)
        self.assertFalse(Categoria.objects.filter(pk=origem.pk).exists())

    def test_listar_ativas_inclui_padrao_e_do_usuario(self):
        padrao = Categoria.objects.create(
            usuario=None,
            padrao=True,
            nome="Alimentação",
            tipo="despesa",
            cor="#F59E0B",
            ativa=True,
        )
        propria = Categoria.objects.create(
            usuario=self.user, nome="Delivery", tipo="despesa", cor="#F97316", ativa=True
        )
        Categoria.objects.create(
            usuario=self.other, nome="Alheia", tipo="despesa", cor="#EF4444", ativa=True
        )
        resp = self.client.get(
            reverse("categorias:listar_ativas"),
            {"tipo": "despesa"},
            **AJAX,
        )
        self.assertEqual(resp.status_code, 200)
        ids = {c["id"] for c in resp.json()["categorias"]}
        self.assertIn(padrao.pk, ids)
        self.assertIn(propria.pk, ids)
        self.assertNotIn(
            Categoria.objects.get(usuario=self.other, nome="Alheia").pk, ids
        )

    def test_idor_nao_arquiva_categoria_de_outro(self):
        alheia = Categoria.objects.create(
            usuario=self.other, nome="Alheia", tipo="despesa", cor="#EF4444", ativa=True
        )
        resp = self._post("categorias:arquivar", {"categoria_id": str(alheia.pk)})
        self.assertEqual(resp.status_code, 404)
        alheia.refresh_from_db()
        self.assertTrue(alheia.ativa)
