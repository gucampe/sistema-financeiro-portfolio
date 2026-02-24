from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from categorias.models import Categoria
from categorias.signal import CATEGORIAS_DESPESA, CATEGORIAS_RECEITA


class Command(BaseCommand):
    help = "Cria categorias padrão para usuários existentes"

    def handle(self, *args, **options):
        User = get_user_model()

        for user in User.objects.all():
            for nome in CATEGORIAS_DESPESA:
                Categoria.objects.get_or_create(
                    usuario=user,
                    nome=nome,
                    defaults={"tipo": "despesa", "padrao": False},
                )
            for nome in CATEGORIAS_RECEITA:
                Categoria.objects.get_or_create(
                    usuario=user,
                    nome=nome,
                    defaults={"tipo": "receita", "padrao": False},
                )

        self.stdout.write(self.style.SUCCESS("Categorias padrão garantidas para todos os usuários."))
        