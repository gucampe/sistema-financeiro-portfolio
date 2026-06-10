from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

MOEDA_QUANT = Decimal("0.01")


class ContractViolation(AssertionError):
    """Violação de invariante financeiro (CON-*)."""


def quantize_moeda(valor: Decimal) -> Decimal:
    return Decimal(valor).quantize(MOEDA_QUANT, rounding=ROUND_HALF_UP)


def assert_decimal_equal(
    atual: Decimal,
    esperado: Decimal,
    contrato_id: str,
    contexto: str = "",
) -> None:
    a = quantize_moeda(atual)
    e = quantize_moeda(esperado)
    if a != e:
        msg = f"{contrato_id} violado: {a} != {e}"
        if contexto:
            msg = f"{msg} ({contexto})"
        raise ContractViolation(msg)
