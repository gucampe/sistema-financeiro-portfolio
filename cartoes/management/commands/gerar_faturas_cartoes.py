"""Pré-gera registros de Fatura para um cartão (útil para popular a lista sem lançamentos)."""
from calendar import monthrange
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from cartoes.models import Cartao
from cartoes.services.faturas import obter_ou_criar_fatura


def _first_day_shift_months(d: date, delta_months: int) -> date:
    base = date(d.year, d.month, 1)
    m = base.month - 1 + delta_months
    y = base.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)


class Command(BaseCommand):
    help = "Gera faturas (get_or_create) para N meses a partir do mês de referência."

    def add_arguments(self, parser):
        parser.add_argument(
            "--cartao-id",
            type=int,
            default=None,
            help="ID do cartão (opcional; todos os ativos se omitido)",
        )
        parser.add_argument("--meses", type=int, default=12, help="Quantidade de meses (padrão 12, máx 120)")
        parser.add_argument(
            "--referencia",
            type=str,
            default=None,
            help="Data YYYY-MM-DD de referência (usa mês/calendário; padrão: hoje)",
        )

    def handle(self, *args, **options):
        ref_str = options["referencia"]
        if ref_str:
            y, m, d = ref_str.split("-")
            referencia = date(int(y), int(m), int(d))
        else:
            referencia = date.today()

        meses = max(1, min(int(options["meses"] or 12), 120))
        cartao_id = options["cartao_id"]

        qs = Cartao.objects.filter(ativa=True)
        if cartao_id:
            qs = qs.filter(pk=cartao_id)

        total = 0
        with transaction.atomic():
            for cartao in qs.iterator():
                for i in range(meses):
                    alvo = _first_day_shift_months(referencia, -i)
                    last = monthrange(alvo.year, alvo.month)[1]
                    d_compra = date(alvo.year, alvo.month, min(cartao.dia_fechamento, last))
                    obter_ou_criar_fatura(cartao, d_compra)
                    total += 1

        self.stdout.write(self.style.SUCCESS(f"Faturas resolvidas/criadas: {total} (chamadas get_or_create)."))
