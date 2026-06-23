from __future__ import annotations

from django.core.management.base import BaseCommand

from categorizacao.services.recategorizacao import recategorizar_transacoes
from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Recategoriza transações existentes com sugestões do pipeline"

    def add_arguments(self, parser):
        parser.add_argument("--usuario", type=int, required=True)
        parser.add_argument(
            "--categoria-nome",
            default="Diversos",
            help="Recategorizar transações nesta categoria (default: Diversos)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas simula, não persiste alterações",
        )
        parser.add_argument(
            "--limite",
            type=int,
            default=500,
        )

    def handle(self, *args, **options):
        usuario = Usuario.objects.get(pk=options["usuario"])
        stats = recategorizar_transacoes(
            usuario=usuario,
            categoria_nome=options["categoria_nome"],
            dry_run=options["dry_run"],
            limite=options["limite"],
        )
        modo = "DRY-RUN" if options["dry_run"] else "APLICADO"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{modo}] Analisadas: {stats['analisadas']}, "
                f"sugestões: {stats['sugestoes']}, aplicadas: {stats['aplicadas']}"
            )
        )
