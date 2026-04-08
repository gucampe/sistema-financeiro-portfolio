"""
Detecção de duplicatas para importação OFX (consulta ORM).

- Duplicata por FITID (forte): mesmo FITID **e** mesma chave (data + valor + descrição
  normalizada) que no BD ou repetida no lote com esse FITID. FITID repetido no arquivo
  com dados diferentes não marca dup por FITID.
- Duplicata heurística (fraca): mesma chave no BD ou repetida no lote — vale para todas
  as linhas (com ou sem FITID), para pegar reimportações e lançamentos manuais iguais.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from contas.models import Conta

from transacoes.models import Transacao
from transacoes.ofx_parse import LinhaOfx


def normalizar_descricao(texto: str) -> str:
    """Trim, colapsa espaços e casefold (Unicode) para comparação."""
    s = (texto or "").strip().casefold()
    s = re.sub(r"\s+", " ", s)
    return s


def _chave_heuristica(data: date, valor: Decimal, descricao: str) -> tuple[date, Decimal, str]:
    return (data, valor, normalizar_descricao(descricao))


def chave_fingerprint_linha(data: date, valor: Decimal, descricao: str) -> tuple[date, Decimal, str]:
    """Mesma chave usada no preview e na confirmação OFX (data, valor, descrição normalizada)."""
    return _chave_heuristica(data, valor, descricao)


def _conta_do_usuario(conta: Conta, usuario) -> None:
    if conta.usuario_id != usuario.pk:
        raise ValueError("A conta não pertence ao usuário.")


@dataclass(frozen=True)
class ResultadoDuplicata:
    indice: int
    duplicata_por_fitid: bool
    duplicata_por_heuristica: bool


def avaliar_duplicatas_importacao(usuario, conta: Conta, linhas: list[LinhaOfx]) -> list[ResultadoDuplicata]:
    """
    Para cada linha do OFX já parseado, indica duplicata por FITID e/ou heurística.

    Duplicata por FITID: mesmo FITID e mesma chave que no BD ou repetida no lote com esse FITID.

    Duplicata heurística: mesma chave (data, valor, descrição normalizada) que qualquer
    transação da conta no BD ou que uma linha anterior no arquivo (independente de FITID).
    """
    _conta_do_usuario(conta, usuario)

    qs = Transacao.objects.filter(usuario=usuario, conta=conta)

    fitid_chave_db: dict[str, tuple[date, Decimal, str]] = {}
    for t in (
        qs.exclude(ofx_fitid__isnull=True)
        .exclude(ofx_fitid="")
        .only("ofx_fitid", "data", "valor", "descricao")
        .iterator(chunk_size=500)
    ):
        fitid_chave_db[t.ofx_fitid] = _chave_heuristica(t.data, t.valor, t.descricao)

    chaves_db: set[tuple[date, Decimal, str]] = set()
    for t in qs.iterator(chunk_size=500):
        chaves_db.add(_chave_heuristica(t.data, t.valor, t.descricao))

    # Por FITID: conjuntos de chaves já vistas no lote (várias chaves distintas com o mesmo FITID são ok).
    chaves_por_fitid_no_lote: dict[str, set[tuple[date, Decimal, str]]] = {}
    vistos_chave: set[tuple[date, Decimal, str]] = set()

    resultados: list[ResultadoDuplicata] = []

    for indice, linha in enumerate(linhas):
        dup_fitid = False
        chave = _chave_heuristica(linha.data, linha.valor, linha.descricao)

        fid = linha.ofx_fitid
        if fid:
            if fid in fitid_chave_db and fitid_chave_db[fid] == chave:
                dup_fitid = True
            if fid in chaves_por_fitid_no_lote and chave in chaves_por_fitid_no_lote[fid]:
                dup_fitid = True
            chaves_por_fitid_no_lote.setdefault(fid, set()).add(chave)

        dup_heur = chave in chaves_db or chave in vistos_chave
        vistos_chave.add(chave)

        resultados.append(
            ResultadoDuplicata(
                indice=indice,
                duplicata_por_fitid=dup_fitid,
                duplicata_por_heuristica=dup_heur,
            )
        )

    return resultados
