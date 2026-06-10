from __future__ import annotations

from decimal import Decimal

from financial_contracts.fatura_contracts import assert_fatura_saldo, assert_fatura_total
from financial_contracts.saldo_contracts import assert_saldo_conta, calcular_saldo_esperado


def verify_saldo_conta(
    conta_id: int,
    esperado: Decimal,
    *,
    incluir_compras_cartao: bool = True,
) -> None:
    from contas.models import Conta

    conta = Conta.objects.get(pk=conta_id)
    assert_saldo_conta(
        conta, esperado, incluir_compras_cartao=incluir_compras_cartao
    )


def verify_fatura(fatura_id: int) -> None:
    from cartoes.models import Fatura

    fatura = Fatura.objects.get(pk=fatura_id)
    assert_fatura_total(fatura)
    assert_fatura_saldo(fatura)
