"""Wrappers finos — delegam a financial_contracts."""

from __future__ import annotations

from decimal import Decimal

from financial_contracts.competencia_contracts import (
    assert_competencia_cartao_vencimento,
    assert_data_competencia_em_fatura,
)
from financial_contracts.fatura_contracts import (
    assert_fatura_saldo,
    assert_fatura_total,
    assert_status_fatura_coerente,
)
from financial_contracts.saldo_contracts import assert_compra_cartao_nao_altera_saldo_conta


def assert_fatura_consistente(fatura) -> None:
    assert_fatura_total(fatura)
    assert_fatura_saldo(fatura)
    assert_status_fatura_coerente(fatura)
    assert_competencia_cartao_vencimento(fatura)


def assert_compra_cartao_consistente(transacao) -> None:
    assert_data_competencia_em_fatura(transacao)


def assert_conta_saldo(conta, esperado: Decimal) -> None:
    from financial_contracts.saldo_contracts import assert_saldo_conta

    assert_saldo_conta(conta, esperado, incluir_compras_cartao=False)


def assert_compra_nao_move_saldo(conta, saldo_antes: Decimal) -> None:
    assert_compra_cartao_nao_altera_saldo_conta(conta, saldo_antes)
