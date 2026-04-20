from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Perfil, Usuario


@receiver(post_save, sender=Usuario)
def garantir_perfil_usuario(sender, instance, **kwargs):
    Perfil.objects.get_or_create(usuario=instance)
