from __future__ import annotations

from decimal import Decimal

from financial_contracts.base import assert_decimal_equal
from financial_contracts.fatura_contracts import assert_pagamento_nao_conta_orcamento


def assert_pagamento_excluido_do_realizado(usuario, categoria, periodo_filtros) -> None:
    assert_pagamento_nao_conta_orcamento(usuario, categoria, periodo_filtros, "CON-ORC-01")


def assert_realizado_orcamento(
    linha,
    esperado: Decimal,
    contrato_id: str = "CON-ORC-02",
) -> None:
    assert_decimal_equal(linha.realizado, esperado, contrato_id, f"categoria={linha.categoria_id}")
