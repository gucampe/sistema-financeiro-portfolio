"""Cálculo de ciclos de fatura (fechamento / vencimento) a partir do cartão e da data de compra."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from cartoes.models import Cartao


def _date_clamped(year: int, month: int, day_num: int) -> date:
    last = monthrange(year, month)[1]
    return date(year, month, min(day_num, last))


def intervalo_compras_para_data(cartao: Cartao, d: date) -> tuple[date, date]:
    """
    Retorna (data_inicio_compras, data_fim_compras) inclusivo do ciclo que contém a data de compra `d`.
    data_fim_compras é a data de fechamento (último dia do ciclo de compras).
    """
    df = cartao.dia_fechamento
    c_m = _date_clamped(d.year, d.month, df)
    if d <= c_m:
        if d.month == 1:
            py, pm = d.year - 1, 12
        else:
            py, pm = d.year, d.month - 1
        c_prev = _date_clamped(py, pm, df)
        inicio = c_prev + timedelta(days=1)
        fim = c_m
    else:
        inicio = c_m + timedelta(days=1)
        if d.month == 12:
            ny, nm = d.year + 1, 1
        else:
            ny, nm = d.year, d.month + 1
        fim = _date_clamped(ny, nm, df)
    return inicio, fim


def data_vencimento_para_fechamento(cartao: Cartao, data_fechamento: date) -> date:
    """Primeira data de vencimento (dia_vencimento) estritamente após o fechamento do ciclo."""
    dv = cartao.dia_vencimento
    cand = _date_clamped(data_fechamento.year, data_fechamento.month, dv)
    if cand > data_fechamento:
        return cand
    if data_fechamento.month == 12:
        ny, nm = data_fechamento.year + 1, 1
    else:
        ny, nm = data_fechamento.year, data_fechamento.month + 1
    return _date_clamped(ny, nm, dv)


def competencia_para_vencimento(data_vencimento: date) -> date:
    """Primeiro dia do mês de competência (único por fatura no MVP)."""
    return date(data_vencimento.year, data_vencimento.month, 1)
