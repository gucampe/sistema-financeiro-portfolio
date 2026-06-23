from django.core.management.base import BaseCommand

from categorizacao.services.learning import agregar_contribuicoes_globais


class Command(BaseCommand):
    help = "Promove agregações anonimizadas (k-anonymity) para regras globais"

    def add_arguments(self, parser):
        parser.add_argument("--min-usuarios", type=int, default=10)

    def handle(self, *args, **options):
        n = agregar_contribuicoes_globais(min_usuarios=options["min_usuarios"])
        self.stdout.write(self.style.SUCCESS(f"{n} regras globais criadas a partir de agregações."))
