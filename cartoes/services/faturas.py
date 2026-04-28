from __future__ import annotations

from datetime import date

from django.db import transaction

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
        if created:
            # Regra de negócio: apenas uma fatura aberta por cartão.
            Fatura.objects.filter(
                cartao=cartao,
                status_ciclo=Fatura.Status.ABERTA,
            ).exclude(pk=fatura.pk).update(
                status=Fatura.Status.FECHADA,
                status_ciclo=Fatura.Status.FECHADA,
            )
    return fatura
