from __future__ import annotations

from datetime import date

from django.db import transaction
from django.db.models import Q

from cartoes.models import Cartao, Fatura
from cartoes.services.ciclos import (
    competencia_para_vencimento,
    data_vencimento_para_fechamento,
    intervalo_compras_para_data,
)


def obter_ou_criar_fatura(cartao: Cartao, data_compra: date) -> Fatura:
    """
    Resolve ou cria a fatura do cartão para o ciclo que contém `data_compra`.
    Idempotente por (cartao, competencia).
    """
    inicio, fim = intervalo_compras_para_data(cartao, data_compra)
    dv = data_vencimento_para_fechamento(cartao, fim)
    competencia = competencia_para_vencimento(dv)
    with transaction.atomic():
        fatura, created = Fatura.objects.select_for_update().get_or_create(
            cartao=cartao,
            competencia=competencia,
            defaults={
                "usuario": cartao.usuario,
                "data_fechamento": fim,
                "data_vencimento": dv,
                "data_inicio_compras": inicio,
                "data_fim_compras": fim,
                "valor_total": None,
                "status": Fatura.Status.ABERTA,
                "status_ciclo": Fatura.Status.ABERTA,
                "status_pagamento": Fatura.StatusPagamento.PENDENTE,
            },
        )
    return fatura


def faturas_atuais_cartoes(cartoes: list[Cartao], data_ref: date) -> dict[int, Fatura]:
    """
    Resolve faturas do ciclo atual para vários cartões.
    Consulta existentes em lote; cria apenas faltantes.
    """
    if not cartoes:
        return {}

    meta: dict[int, tuple] = {}
    lookup = Q()
    for cartao in cartoes:
        inicio, fim = intervalo_compras_para_data(cartao, data_ref)
        dv = data_vencimento_para_fechamento(cartao, fim)
        competencia = competencia_para_vencimento(dv)
        meta[cartao.id] = (competencia, inicio, fim, dv)
        lookup |= Q(cartao_id=cartao.id, competencia=competencia)

    existentes = {
        f.cartao_id: f
        for f in Fatura.objects.filter(lookup)
    }

    resultado: dict[int, Fatura] = {}
    for cartao in cartoes:
        fatura = existentes.get(cartao.id)
        if fatura is None:
            competencia, inicio, fim, dv = meta[cartao.id]
            with transaction.atomic():
                fatura, _ = Fatura.objects.select_for_update().get_or_create(
                    cartao=cartao,
                    competencia=competencia,
                    defaults={
                        "usuario": cartao.usuario,
                        "data_fechamento": fim,
                        "data_vencimento": dv,
                        "data_inicio_compras": inicio,
                        "data_fim_compras": fim,
                        "valor_total": None,
                        "status": Fatura.Status.ABERTA,
                        "status_ciclo": Fatura.Status.ABERTA,
                        "status_pagamento": Fatura.StatusPagamento.PENDENTE,
                    },
                )
        resultado[cartao.id] = fatura
    return resultado
