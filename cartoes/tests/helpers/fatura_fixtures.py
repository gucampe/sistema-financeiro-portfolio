"""Fixtures determinísticas para testes de faturas."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from cartoes.models import Cartao
from cartoes.services.faturas import obter_ou_criar_fatura
from categorias.models import Categoria
from contas.models import Conta
from transacoes.models import Transacao


def build_cartao(
    user,
    conta: Conta,
    *,
    nome: str = "Cartão teste",
    dia_fechamento: int = 10,
    dia_vencimento: int = 20,
) -> Cartao:
    return Cartao.objects.create(
        usuario=user,
        nome=nome,
        dia_fechamento=dia_fechamento,
        dia_vencimento=dia_vencimento,
        conta_padrao=conta,
        ativa=True,
    )


def build_cartao_par(user, conta: Conta) -> tuple[Cartao, Cartao]:
    a = build_cartao(user, conta, nome="Cartão A", dia_fechamento=10, dia_vencimento=20)
    b = build_cartao(user, conta, nome="Cartão B", dia_fechamento=25, dia_vencimento=5)
    return a, b


def _clamp_day(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, monthrange(year, month)[1]))


def datas_fronteira_fechamento(cartao: Cartao, *, year: int = 2026, month: int = 4) -> tuple[date, date, date]:
    """(dia antes, dia fechamento, dia depois) para o mês informado."""
    fech = _clamp_day(year, month, cartao.dia_fechamento)
    antes = fech - timedelta(days=1)
    depois = fech + timedelta(days=1)
    return antes, fech, depois


def mesma_fatura(cartao: Cartao, d1: date, d2: date) -> bool:
    return obter_ou_criar_fatura(cartao, d1).pk == obter_ou_criar_fatura(cartao, d2).pk


def seed_compra(
    user,
    conta: Conta,
    cartao: Cartao,
    categoria: Categoria,
    *,
    data: date,
    valor: Decimal | str = Decimal("10.00"),
    descricao: str = "Compra teste",
) -> Transacao:
    return Transacao.objects.create(
        usuario=user,
        conta=conta,
        cartao=cartao,
        categoria=categoria,
        tipo="despesa",
        valor=Decimal(str(valor)),
        descricao=descricao,
        data=data,
    )


def snapshot_faturas(cartoes: list[Cartao]) -> dict[int, dict[str, Any]]:
    from cartoes.services.gestao_faturas import calcular_resumo_pagamento

    out: dict[int, dict[str, Any]] = {}
    for cartao in cartoes:
        snaps = []
        for f in cartao.faturas.all().order_by("competencia"):
            r = calcular_resumo_pagamento(f)
            snaps.append(
                {
                    "fatura_id": f.pk,
                    "competencia": f.competencia,
                    "total": r.total,
                    "pago": r.pago,
                    "saldo": r.saldo,
                    "status": r.status_pagamento,
                }
            )
        out[cartao.pk] = snaps
    return out
