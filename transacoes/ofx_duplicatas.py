"""
Detecção de duplicatas para importação OFX (consulta ORM).

- Com FITID na linha: critério forte = mesma conta + mesmo ofx_fitid (BD ou no próprio lote).
- Sem FITID na linha: critério fraco = mesma conta + mesma data + mesmo valor + descrição normalizada
  (BD ou no próprio lote).
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

    A heurística só é avaliada quando `linha.ofx_fitid` é None (ausente).
    """
    _conta_do_usuario(conta, usuario)

    qs = Transacao.objects.filter(usuario=usuario, conta=conta)

    fitids_db: set[str] = set(
        qs.exclude(ofx_fitid__isnull=True)
        .exclude(ofx_fitid="")
        .values_list("ofx_fitid", flat=True)
    )

    chaves_db: set[tuple[date, Decimal, str]] = set()
    for t in qs.iterator(chunk_size=500):
        chaves_db.add(_chave_heuristica(t.data, t.valor, t.descricao))

    vistos_fitid: set[str] = set()
    vistos_chave: set[tuple[date, Decimal, str]] = set()

    resultados: list[ResultadoDuplicata] = []

    for indice, linha in enumerate(linhas):
        dup_fitid = False
        dup_heur = False

        fid = linha.ofx_fitid
        if fid:
            if fid in fitids_db or fid in vistos_fitid:
                dup_fitid = True
            vistos_fitid.add(fid)
        else:
            chave = _chave_heuristica(linha.data, linha.valor, linha.descricao)
            if chave in chaves_db or chave in vistos_chave:
                dup_heur = True
            vistos_chave.add(chave)

        resultados.append(
            ResultadoDuplicata(
                indice=indice,
                duplicata_por_fitid=dup_fitid,
                duplicata_por_heuristica=dup_heur,
            )
        )

    return resultados
