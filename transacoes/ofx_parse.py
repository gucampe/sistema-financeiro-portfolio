"""
Parser OFX puro (sem dependência de Django).

Convenção de valores: o OFX usa sinal em TRNAMT (negativo = saída).
No model Transacao, `valor` é sempre magnitude positiva e `tipo` define o sentido.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from ofxparse import OfxParser


@dataclass(frozen=True)
class LinhaOfx:
    """Uma linha candidata a Transacao após leitura do OFX."""

    data: date
    valor: Decimal
    tipo: str  # receita | despesa | ajuste
    descricao: str
    ofx_fitid: str | None


def _montar_descricao(payee: str | None, memo: str | None) -> str:
    partes = [p.strip() for p in (payee or "", memo or "") if p and p.strip()]
    desc = " ".join(partes).strip()
    if not desc:
        desc = "Sem descrição"
    if len(desc) > 255:
        desc = desc[:252] + "..."
    return desc


def _normalizar_fitid(fitid: object) -> str | None:
    if fitid is None:
        return None
    s = str(fitid).strip()
    return s if s else None


def valor_e_tipo_de_importacao(
    amount: object,
    *,
    mensagem_valor_invalido: str = "Valor inválido.",
) -> tuple[Decimal, str]:
    """
    Converte um montante com sinal em (valor_absoluto_ou_zero, tipo).
    Positivo = receita, negativo = despesa (valor armazenado em magnitude), zero = ajuste.
    Usado pelo OFX e pela importação de planilha padronizada.
    """
    try:
        d = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(mensagem_valor_invalido) from exc

    if d > 0:
        return d, "receita"
    if d < 0:
        return abs(d), "despesa"
    return Decimal("0"), "ajuste"


def _data_para_date(dt: date | datetime | None) -> date:
    if dt is None:
        raise ValueError("Data da transação OFX ausente.")
    if isinstance(dt, datetime):
        return dt.date()
    return dt


def _iter_transacoes(ofx) -> Iterable:
    contas = list(ofx.accounts or [])
    if not contas and getattr(ofx, "account", None) is not None:
        contas = [ofx.account]

    for account in contas:
        stmt = getattr(account, "statement", None)
        if stmt is None:
            continue
        for t in getattr(stmt, "transactions", None) or []:
            yield t


def parse_ofx_bytes(data: bytes, *, fail_fast: bool = True) -> list[LinhaOfx]:
    """
    Lê bytes de um arquivo OFX e devolve linhas normalizadas.

    Agrega transações de todas as contas presentes no arquivo.
    """
    if not data or not data.strip():
        raise ValueError("Arquivo OFX vazio.")

    buffer = io.BytesIO(data)
    ofx = OfxParser.parse(buffer, fail_fast=fail_fast)

    linhas: list[LinhaOfx] = []
    for t in _iter_transacoes(ofx):
        valor, tipo = valor_e_tipo_de_importacao(
            t.amount,
            mensagem_valor_invalido="Valor da transação OFX inválido.",
        )
        data_tx = _data_para_date(t.date)
        desc = _montar_descricao(getattr(t, "payee", None), getattr(t, "memo", None))
        fitid = _normalizar_fitid(getattr(t, "id", None))

        linhas.append(
            LinhaOfx(
                data=data_tx,
                valor=valor,
                tipo=tipo,
                descricao=desc,
                ofx_fitid=fitid,
            )
        )

    return linhas
