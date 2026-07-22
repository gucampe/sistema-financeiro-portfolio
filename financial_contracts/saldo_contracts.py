from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum

from financial_contracts.base import assert_decimal_equal, quantize_moeda
from transacoes.saldo_expr import saldo_case_expression


def _qs_saldo_conta(conta, *, incluir_compras_cartao: bool = True):
    from transacoes.models import Transacao

    qs = Transacao.objects.filter(conta=conta, usuario=conta.usuario)
    if not incluir_compras_cartao:
        qs = qs.exclude(
            cartao__isnull=False,
            pagamento_de_fatura__isnull=True,
            tipo="despesa",
        )
    return qs


def calcular_saldo_esperado(conta, *, incluir_compras_cartao: bool = True) -> Decimal:
    """
    CON-SALDO-01: saldo = receitas - despesas + ajustes
    ± transferências (origem −, destino +). Compras cartão opcional.
    """
    result = _qs_saldo_conta(conta, incluir_compras_cartao=incluir_compras_cartao).aggregate(
        saldo=Sum(saldo_case_expression())
    )["saldo"]
    return quantize_moeda(result or Decimal("0.00"))


def assert_saldo_conta(
    conta,
    esperado: Decimal,
    contrato_id: str = "CON-SALDO-01",
    *,
    incluir_compras_cartao: bool = True,
) -> None:
    atual = calcular_saldo_esperado(
        conta, incluir_compras_cartao=incluir_compras_cartao
    )
    assert_decimal_equal(atual, esperado, contrato_id, f"conta={conta.pk}")


def assert_patrimonio_contas(usuario, esperado: Decimal, contrato_id: str = "CON-SALDO-02") -> None:
    from contas.models import Conta

    total = Decimal("0.00")
    for conta in Conta.objects.filter(usuario=usuario, ativa=True):
        total += quantize_moeda(conta.saldo_atual_calc)
    assert_decimal_equal(total, esperado, contrato_id, f"usuario={usuario.pk}")


def assert_exclusao_reverte_saldo(
    conta,
    saldo_antes: Decimal,
    contrato_id: str = "CON-SALDO-03",
) -> None:
    assert_saldo_conta(conta, saldo_antes, contrato_id)


def assert_compra_cartao_nao_altera_saldo_conta(
    conta,
    saldo_antes: Decimal,
    contrato_id: str = "CON-SALDO-04",
) -> None:
    assert_saldo_conta(
        conta,
        saldo_antes,
        contrato_id,
        incluir_compras_cartao=False,
    )
