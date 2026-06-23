from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count

from categorizacao.services.ml_training import treinar_modelo_usuario
from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Retreina modelos ML de categorização por usuário (TF-IDF + LinearSVC)"

    def add_arguments(self, parser):
        parser.add_argument("--usuario", type=int, help="ID do usuário específico")
        parser.add_argument(
            "--min-amostras",
            type=int,
            default=50,
            help="Mínimo de transações categorizadas para treinar",
        )

    def handle(self, *args, **options):
        min_amostras = options["min_amostras"]
        usuario_id = options.get("usuario")

        if usuario_id:
            usuarios = Usuario.objects.filter(pk=usuario_id)
        else:
            from transacoes.models import Transacao

            usuarios = (
                Usuario.objects.annotate(n=Count("transacoes"))
                .filter(n__gte=min_amostras)
                .order_by("-n")
            )

        treinados = 0
        ignorados = 0
        for usuario in usuarios:
            ok = treinar_modelo_usuario(usuario, min_amostras=min_amostras)
            if ok:
                treinados += 1
                self.stdout.write(f"Modelo treinado: usuario={usuario.pk}")
            else:
                ignorados += 1

        self.stdout.write(
            self.style.SUCCESS(f"Concluído: {treinados} treinados, {ignorados} ignorados.")
        )
