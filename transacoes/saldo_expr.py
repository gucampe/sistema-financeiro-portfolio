"""Expressões e helpers de saldo do ledger (CON-SALDO-01)."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import Case, DecimalField, F, Q, Value, When


def saldo_case_expression(
    *,
    valor_field: str = "valor",
    tipo_field: str = "tipo",
    papel_field: str = "papel_transferencia",
):
    """
    CON-SALDO-01 estendido:
    saldo = receitas - despesas + ajustes
            - transferências (origem) + transferências (destino)

    Aceita prefixos de related (ex.: transacoes__valor) para annotate em Conta.
    """
    v = F(valor_field)
    return Case(
        When(**{tipo_field: "receita"}, then=v),
        When(**{tipo_field: "despesa"}, then=-v),
        When(**{tipo_field: "ajuste"}, then=v),
        When(
            Q(**{tipo_field: "transferencia", papel_field: "origem"}),
            then=-v,
        ),
        When(
            Q(**{tipo_field: "transferencia", papel_field: "destino"}),
            then=v,
        ),
        default=Value(Decimal("0.00")),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
