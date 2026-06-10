from __future__ import annotations

from decimal import Decimal

from financial_contracts.base import assert_decimal_equal, quantize_moeda


def assert_fatura_total(fatura, contrato_id: str = "CON-FAT-01") -> None:
    from cartoes.services.gestao_faturas import total_fatura

    total_servico = quantize_moeda(total_fatura(fatura))
    if fatura.valor_total is not None:
        assert_decimal_equal(
            quantize_moeda(fatura.valor_total),
            total_servico,
            contrato_id,
            f"fatura={fatura.pk}",
        )


def assert_fatura_saldo(fatura, contrato_id: str = "CON-FAT-02") -> None:
    from cartoes.services.gestao_faturas import calcular_resumo_pagamento

    resumo = calcular_resumo_pagamento(fatura)
    esperado = quantize_moeda(resumo.total - resumo.pago)
    assert_decimal_equal(resumo.saldo, esperado, contrato_id, f"fatura={fatura.pk}")


def assert_status_fatura_coerente(fatura, contrato_id: str = "CON-FAT-04") -> None:
    from cartoes.models import Fatura
    from cartoes.services.gestao_faturas import calcular_resumo_pagamento

    resumo = calcular_resumo_pagamento(fatura)
    status = resumo.status_pagamento
    if resumo.saldo <= Decimal("0") and resumo.total > Decimal("0"):
        if status != Fatura.StatusPagamento.PAGO:
            raise AssertionError(
                f"{contrato_id}: saldo zero mas status={status} (fatura={fatura.pk})"
            )
    elif resumo.pago > Decimal("0") and resumo.saldo > Decimal("0"):
        if status != Fatura.StatusPagamento.PARCIAL:
            raise AssertionError(
                f"{contrato_id}: pagamento parcial mas status={status} (fatura={fatura.pk})"
            )


def assert_pagamento_nao_conta_orcamento(
    usuario,
    categoria,
    periodo_filtros,
    contrato_id: str = "CON-ORC-01",
) -> None:
    """Pagamentos de fatura não entram no realizado de orçamento."""
    from relatorios.services.filtros import RelatorioFiltros
    from relatorios.services.orcamentos import queryset_despesas_orcamento
    from transacoes.models import Transacao

    if not isinstance(periodo_filtros, RelatorioFiltros):
        raise TypeError("periodo_filtros deve ser RelatorioFiltros")

    qs = queryset_despesas_orcamento(usuario, periodo_filtros)
    pagamentos = Transacao.objects.filter(
        usuario=usuario,
        pagamento_de_fatura__isnull=False,
        categoria=categoria,
    )
    for pag in pagamentos:
        if qs.filter(pk=pag.pk).exists():
            raise AssertionError(
                f"{contrato_id}: pagamento_de_fatura id={pag.pk} apareceu no realizado"
            )
