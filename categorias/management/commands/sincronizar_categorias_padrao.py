from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from categorias.models import Categoria
from categorias.defaults import CATEGORIAS_DESPESA, CATEGORIAS_RECEITA


class Command(BaseCommand):
    help = (
        "Cria/garante categorias padrão para usuários existentes e "
        "atualiza icone/cor quando estiverem no default."
    )

    def handle(self, *args, **options):
        User = get_user_model()

        # Converte lista de tuplas em dict para lookup rápido por nome
        mapa_despesa = {nome: (icone, cor) for (nome, icone, cor) in CATEGORIAS_DESPESA}
        mapa_receita = {nome: (icone, cor) for (nome, icone, cor) in CATEGORIAS_RECEITA}

        total_criadas = 0
        total_atualizadas = 0

        for user in User.objects.all():
            # ===== Despesas =====
            for nome, icone_padrao, cor_padrao in CATEGORIAS_DESPESA:
                obj, created = Categoria.objects.get_or_create(
                    usuario=user,
                    nome=nome,
                    tipo="despesa",
                    defaults={
                        "icone": icone_padrao,
                        "cor": cor_padrao,
                        "padrao": False,
                    },
                )
                if created:
                    total_criadas += 1
                else:
                    # Atualiza apenas se ainda estiver com default genérico
                    mudou = False

                    if (obj.icone in [None, "", "fa-ellipsis-h"]) and obj.icone != icone_padrao:
                        obj.icone = icone_padrao
                        mudou = True

                    if (obj.cor in [None, "", "#4F46E5"]) and obj.cor != cor_padrao:
                        obj.cor = cor_padrao
                        mudou = True

                    if mudou:
                        obj.save(update_fields=["icone", "cor"])
                        total_atualizadas += 1

            # ===== Receitas =====
            for nome, icone_padrao, cor_padrao in CATEGORIAS_RECEITA:
                obj, created = Categoria.objects.get_or_create(
                    usuario=user,
                    nome=nome,
                    tipo="receita",
                    defaults={
                        "icone": icone_padrao,
                        "cor": cor_padrao,
                        "padrao": False,
                    },
                )
                if created:
                    total_criadas += 1
                else:
                    mudou = False

                    if (obj.icone in [None, "", "fa-ellipsis-h"]) and obj.icone != icone_padrao:
                        obj.icone = icone_padrao
                        mudou = True

                    if (obj.cor in [None, "", "#4F46E5"]) and obj.cor != cor_padrao:
                        obj.cor = cor_padrao
                        mudou = True

                    if mudou:
                        obj.save(update_fields=["icone", "cor"])
                        total_atualizadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"OK! Categorias criadas: {total_criadas} | Categorias atualizadas (icone/cor): {total_atualizadas}"
            )
        )