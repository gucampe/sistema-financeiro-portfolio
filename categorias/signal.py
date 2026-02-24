# categorias/signal.py
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Categoria
from .defaults import CATEGORIAS_DESPESA, CATEGORIAS_RECEITA


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def criar_categorias_padrao_para_usuario(sender, instance, created, **kwargs):
    if not created:
        return

    user = instance

    # Despesas
    for nome, icone, cor in CATEGORIAS_DESPESA:
        Categoria.objects.get_or_create(
            usuario=user,
            nome=nome,
            tipo="despesa",
            defaults={
                "icone": icone,
                "cor": cor,
                "padrao": False,
            },
        )

    # Receitas
    for nome, icone, cor in CATEGORIAS_RECEITA:
        Categoria.objects.get_or_create(
            usuario=user,
            nome=nome,
            tipo="receita",
            defaults={
                "icone": icone,
                "cor": cor,
                "padrao": False,
            },
        )
