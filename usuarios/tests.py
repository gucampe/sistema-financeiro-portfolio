from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from categorias.models import Categoria
from contas.models import Conta

from .forms import PreferenciasFinanceirasForm
from .models import Perfil

User = get_user_model()


class PerfilSignalTests(TestCase):
    def test_novo_usuario_recebe_perfil(self):
        user = User.objects.create_user(
            email="novo@test.com",
            password="senha-segura-1",
            nome="Novo",
        )
        self.assertTrue(Perfil.objects.filter(usuario=user).exists())


class ConfiguracoesAuthTests(TestCase):
    def test_anonimo_redireciona_login(self):
        c = Client()
        r = c.get(reverse("usuarios:configuracoes"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("usuarios:login"), r.url)

    def test_logado_carrega_pagina(self):
        user = User.objects.create_user(
            email="logado@test.com",
            password="senha-segura-1",
            nome="Logado",
        )
        c = Client()
        self.assertTrue(c.login(email="logado@test.com", password="senha-segura-1"))
        r = c.get(reverse("usuarios:configuracoes"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Preferências financeiras")


class PreferenciasFinanceirasFormTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(
            email="a@test.com",
            password="senha-segura-1",
            nome="A",
        )
        self.b = User.objects.create_user(
            email="b@test.com",
            password="senha-segura-1",
            nome="B",
        )
        self.conta_a = Conta.objects.create(
            usuario=self.a,
            nome="Conta A",
            tipo="corrente",
        )
        self.cat_a = Categoria.objects.create(
            usuario=self.a,
            nome="Cat despesa A",
            tipo="despesa",
        )
        self.cat_b = Categoria.objects.create(
            usuario=self.b,
            nome="Cat despesa B",
            tipo="despesa",
        )
        self.perfil_a, _ = Perfil.objects.get_or_create(usuario=self.a)

    def test_categoria_de_outro_usuario_invalida(self):
        form = PreferenciasFinanceirasForm(
            data={
                "moeda": "BRL",
                "tipo_transacao_padrao": "despesa",
                "conta_padrao": str(self.conta_a.pk),
                "categoria_padrao": str(self.cat_b.pk),
                "ocultar_valores_dashboard": False,
            },
            instance=self.perfil_a,
            user=self.a,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("categoria_padrao", form.errors)

    def test_categoria_incompativel_com_tipo(self):
        cat_rec = Categoria.objects.create(
            usuario=self.a,
            nome="Rec A",
            tipo="receita",
        )
        form = PreferenciasFinanceirasForm(
            data={
                "moeda": "BRL",
                "tipo_transacao_padrao": "despesa",
                "conta_padrao": str(self.conta_a.pk),
                "categoria_padrao": str(cat_rec.pk),
                "ocultar_valores_dashboard": False,
            },
            instance=self.perfil_a,
            user=self.a,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("categoria_padrao", form.errors)
