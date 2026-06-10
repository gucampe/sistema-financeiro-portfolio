"""Invariantes financeiras reutilizáveis em unit, integração e E2E."""

from financial_contracts.base import ContractViolation, quantize_moeda
from financial_contracts.competencia_contracts import (
    assert_competencia_cartao_vencimento,
    assert_data_competencia_em_fatura,
)
from financial_contracts.fatura_contracts import (
    assert_fatura_saldo,
    assert_fatura_total,
    assert_pagamento_nao_conta_orcamento,
    assert_status_fatura_coerente,
)
from financial_contracts.orcamento_contracts import assert_pagamento_excluido_do_realizado
from financial_contracts.saldo_contracts import (
    assert_compra_cartao_nao_altera_saldo_conta,
    assert_exclusao_reverte_saldo,
    assert_patrimonio_contas,
    assert_saldo_conta,
)

__all__ = [
    "ContractViolation",
    "quantize_moeda",
    "assert_saldo_conta",
    "assert_patrimonio_contas",
    "assert_exclusao_reverte_saldo",
    "assert_compra_cartao_nao_altera_saldo_conta",
    "assert_fatura_total",
    "assert_fatura_saldo",
    "assert_status_fatura_coerente",
    "assert_pagamento_nao_conta_orcamento",
    "assert_data_competencia_em_fatura",
    "assert_competencia_cartao_vencimento",
    "assert_pagamento_excluido_do_realizado",
]
