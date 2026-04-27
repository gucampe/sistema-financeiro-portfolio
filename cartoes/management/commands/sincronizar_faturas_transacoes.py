"""Reatribui fatura e data_competencia em transações que já têm cartão (útil após migração)."""
from django.core.management.base import BaseCommand

from transacoes.models import Transacao


class Command(BaseCommand):
    help = "Percorre transações com cartão e executa save() para sincronizar fatura/data_competencia."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=None, help="Máximo de registros a processar")

    def handle(self, *args, **options):
        limite = options["limite"]
        qs = Transacao.objects.filter(cartao__isnull=False).order_by("id")
        if limite:
            qs = qs[: int(limite)]

        n = 0
        for tx in qs.iterator(chunk_size=200):
            tx.save()
            n += 1

        self.stdout.write(self.style.SUCCESS(f"Transações sincronizadas: {n}"))
