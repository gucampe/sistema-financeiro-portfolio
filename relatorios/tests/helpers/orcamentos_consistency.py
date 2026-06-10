"""Asserts reutilizáveis ORC-CON-* para orçamentos avançados."""

from __future__ import annotations

from decimal import Decimal

from relatorios.services.orcamentos import (
    LIMITE_ATENCAO,
    LIMITE_ESTOURO,
    LinhaOrcamento,
    classificar_status,
    painel_mes_orcamento,
    resumo_linhas_orcamento,
)


class OrcamentoConsistencyError(AssertionError):
    pass


def assert_percentual_linha(
    linha: LinhaOrcamento,
    esperado: float,
    *,
    contrato: str = "ORC-CON-07",
) -> None:
    if linha.percentual is None:
        raise OrcamentoConsistencyError(f"{contrato}: percentual None")
    atual = round(linha.percentual, 2)
    esp = round(esperado, 2)
    if atual != esp:
        raise OrcamentoConsistencyError(
            f"{contrato}: percentual {atual}% != {esp}% (categoria={linha.nome})"
        )


def assert_status_linha(
    linha: LinhaOrcamento,
    status: str,
    *,
    contrato: str = "ORC-CON-09",
) -> None:
    if linha.status != status:
        raise OrcamentoConsistencyError(
            f"{contrato}: status {linha.status} != {status} (categoria={linha.nome})"
        )


def assert_painel_agregado(
    linhas: list[LinhaOrcamento],
    *,
    contrato: str = "ORC-CON-08",
) -> dict:
    resumo = resumo_linhas_orcamento(linhas)
    painel = painel_mes_orcamento(linhas, resumo)
    vigentes = [l for l in linhas if l.planejado > 0]
    if vigentes:
        planejado = sum(l.planejado for l in vigentes)
        realizado = sum(l.realizado for l in vigentes)
        if planejado > 0:
            esperado_pct = float(realizado / planejado * 100)
            if painel["percentual"] is None or round(painel["percentual"], 2) != round(
                esperado_pct, 2
            ):
                raise OrcamentoConsistencyError(
                    f"{contrato}: painel % {painel['percentual']} != {esperado_pct}"
                )
    return painel


def assert_barra_exibicao_capped(linha: LinhaOrcamento, *, contrato: str = "ORC-CON-07") -> None:
    if linha.percentual is None:
        return
    if linha.percentual > 100:
        if linha.percentual_exibicao != 100.0:
            raise OrcamentoConsistencyError(f"{contrato}: barra deveria cap em 100%")
    else:
        if round(linha.percentual_exibicao, 2) != round(linha.percentual, 2):
            raise OrcamentoConsistencyError(f"{contrato}: percentual_exibicao diverge")
