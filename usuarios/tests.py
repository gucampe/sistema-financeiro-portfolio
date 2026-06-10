from django.contrib.auth import get_user_model

from django.test import TestCase

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
