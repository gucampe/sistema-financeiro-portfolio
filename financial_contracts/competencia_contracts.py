from __future__ import annotations

from datetime import date

from financial_contracts.base import ContractViolation


def assert_data_competencia_em_fatura(transacao, contrato_id: str = "CON-COMP-02") -> None:
    if not transacao.cartao_id:
        return
    if transacao.pagamento_de_fatura_id:
        return
    if not transacao.fatura_id:
        raise ContractViolation(
            f"{contrato_id}: transação cartão {transacao.pk} sem fatura"
        )
    venc = transacao.fatura.data_vencimento
    comp = transacao.data_competencia
    if comp != venc:
        raise ContractViolation(
            f"{contrato_id}: data_competencia {comp} != vencimento {venc} (tx={transacao.pk})"
        )


def assert_competencia_cartao_vencimento(
    fatura,
    contrato_id: str = "CON-COMP-01",
) -> None:
    """Competência = primeiro dia do mês do vencimento."""
    esperada = date(fatura.data_vencimento.year, fatura.data_vencimento.month, 1)
    if fatura.competencia != esperada:
        raise ContractViolation(
            f"{contrato_id}: competencia {fatura.competencia} != {esperada}"
        )
