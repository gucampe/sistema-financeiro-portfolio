from django.core.management.base import BaseCommand

from e2e.factories.personas import (
    E2E_PASSWORD,
    seed_persona_basic,
    seed_persona_card_user,
    seed_persona_empty,
    seed_persona_orcamentos,
    seed_persona_relatorios,
)


class Command(BaseCommand):
    help = "Cria personas determinísticas para testes E2E e staging."

    def add_arguments(self, parser):
        parser.add_argument(
            "--persona",
            choices=["empty", "basic", "card_user", "relatorios", "orcamentos", "all"],
            default="all",
        )

    def handle(self, *args, **options):
        persona = options["persona"]
        if persona in ("empty", "all"):
            u = seed_persona_empty()
            self.stdout.write(f"empty: {u.email} / {E2E_PASSWORD}")
        if persona in ("basic", "all"):
            d = seed_persona_basic()
            self.stdout.write(f"basic: {d['user'].email} / {E2E_PASSWORD}")
        if persona in ("card_user", "all"):
            d = seed_persona_card_user()
            self.stdout.write(
                f"card_user: {d['user'].email} / {E2E_PASSWORD} "
                f"(cartao={d['cartao'].id}, fatura={d['fatura'].id if d['fatura'] else None})"
            )
        if persona in ("relatorios", "all"):
            d = seed_persona_relatorios()
            self.stdout.write(
                f"relatorios: {d['user'].email} / {E2E_PASSWORD} "
                f"(contas={d['conta_a'].id},{d['conta_b'].id})"
            )
        if persona in ("orcamentos", "all"):
            d = seed_persona_orcamentos()
            self.stdout.write(f"orcamentos: {d['user'].email} / {E2E_PASSWORD}")
        self.stdout.write(self.style.SUCCESS("Seed E2E concluído."))
