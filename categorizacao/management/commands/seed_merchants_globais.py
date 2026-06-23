from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from categorizacao.models import MerchantGlobal
from categorizacao.services.merchant import invalidar_cache_merchants


class Command(BaseCommand):
    help = "Carrega merchants globais a partir de categorizacao/data/merchants_br.json"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Remove merchants existentes antes de importar",
        )

    def handle(self, *args, **options):
        path = Path(__file__).resolve().parent.parent.parent / "data" / "merchants_br.json"
        with path.open(encoding="utf-8") as f:
            items = json.load(f)

        if options["reset"]:
            MerchantGlobal.objects.all().delete()

        criados = 0
        atualizados = 0
        for item in items:
            obj, created = MerchantGlobal.objects.update_or_create(
                canonical_name=item["canonical_name"],
                defaults={
                    "aliases": item.get("aliases", []),
                    "categoria_padrao_nome": item["categoria_padrao_nome"],
                    "tipo": item.get("tipo", "despesa"),
                    "prioridade": item.get("prioridade", 0),
                    "ativo": True,
                },
            )
            if created:
                criados += 1
            else:
                atualizados += 1

        invalidar_cache_merchants()
        self.stdout.write(
            self.style.SUCCESS(
                f"Merchants globais: {criados} criados, {atualizados} atualizados."
            )
        )
