"""
Oracle modular de importação OFX/XLSX.

REGRA-DUP-01: duplicata_por_fitid se FITID + chave (data, valor, desc normalizada) coincide.
REGRA-DUP-02: duplicata_por_heuristica se chave_fingerprint já existe (BD ou lote).
REGRA-DUP-03: UI desmarca linhas com qualquer flag de dup (simulado em expectativa_confirmacao).
REGRA-INC-01/02: re-upload usa REGRA-DUP; confirmar só linhas novas/selecionadas.
REGRA-ENC-01: comparação via normalizar_descricao / chave_fingerprint_linha.
"""

from __future__ import annotations

from transacoes.ofx_duplicatas import (
    ResultadoDuplicata,
    avaliar_duplicatas_importacao,
)
from transacoes.ofx_parse import LinhaOfx


def expectativa_parse(linhas: list[LinhaOfx]) -> dict:
    """Estrutura mínima pós-parse."""
    fitids = [ln.ofx_fitid for ln in linhas if ln.ofx_fitid]
    return {
        "total": len(linhas),
        "linhas": linhas,
        "fitids": fitids,
    }


def expectativa_duplicatas(user, conta, linhas: list[LinhaOfx]) -> list[ResultadoDuplicata]:
    """REGRA-DUP — delega a avaliar_duplicatas_importacao."""
    return avaliar_duplicatas_importacao(user, conta, linhas)


def _linha_dup_por_padrao_ui(res: ResultadoDuplicata) -> bool:
    """REGRA-DUP-03: checkbox desmarcado por padrão se dup FITID ou heurística."""
    return res.duplicata_por_fitid or res.duplicata_por_heuristica


def expectativa_confirmacao(
    linhas: list[LinhaOfx],
    duplicatas: list[ResultadoDuplicata],
    *,
    indices_selecionados: set[int] | None = None,
) -> int:
    """
    Quantas transações seriam criadas na confirmação.

    indices_selecionados=None simula UI padrão (linhas não-dup marcadas).
    """
    if indices_selecionados is None:
        indices_selecionados = {
            res.indice
            for res in duplicatas
            if not _linha_dup_por_padrao_ui(res)
        }
    return sum(1 for i in range(len(linhas)) if i in indices_selecionados)


def expectativa_importacao(
    user,
    conta,
    linhas: list[LinhaOfx],
    *,
    indices_selecionados: set[int] | None = None,
) -> dict:
    """Compositor fino — sem lógica de negócio própria."""
    parsed = expectativa_parse(linhas)
    dups = expectativa_duplicatas(user, conta, linhas)
    return {
        **parsed,
        "duplicatas": dups,
        "criadas_se_confirmar_padrao_ui": expectativa_confirmacao(linhas, dups),
        "criadas_se_confirmar": expectativa_confirmacao(
            linhas, dups, indices_selecionados=indices_selecionados
        ),
    }
