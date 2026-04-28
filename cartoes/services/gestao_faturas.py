from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from categorias.models import Categoria
from transacoes.models import Transacao

from cartoes.models import Fatura


def _zero() -> Decimal:
    return Decimal("0")


def total_fatura(fatura: Fatura) -> Decimal:
    total = (
        Transacao.objects.filter(
            usuario=fatura.usuario,
            fatura=fatura,
            tipo="despesa",
        ).aggregate(s=Sum("valor"))["s"]
        or _zero()
    )
    return total


def valor_pago_fatura(fatura: Fatura) -> Decimal:
    pago = (
        Transacao.objects.filter(
            usuario=fatura.usuario,
            pagamento_de_fatura=fatura,
            tipo="despesa",
        ).aggregate(s=Sum("valor"))["s"]
        or _zero()
    )
    return pago


@dataclass
class ResumoPagamentoFatura:
    total: Decimal
    pago: Decimal
    saldo: Decimal
    status_pagamento: str


def calcular_resumo_pagamento(fatura: Fatura, hoje: date | None = None) -> ResumoPagamentoFatura:
    hoje = hoje or timezone.localdate()
    total = total_fatura(fatura)
    pago = valor_pago_fatura(fatura)
    saldo = total - pago

    if total <= _zero() and pago <= _zero():
        status = Fatura.StatusPagamento.PENDENTE
    elif saldo <= _zero():
        status = Fatura.StatusPagamento.PAGO
    elif pago > _zero():
        status = Fatura.StatusPagamento.PARCIAL
    elif hoje > fatura.data_vencimento:
        status = Fatura.StatusPagamento.ATRASADO
    else:
        status = Fatura.StatusPagamento.PENDENTE

    return ResumoPagamentoFatura(total=total, pago=pago, saldo=saldo, status_pagamento=status)


def recalcular_fatura(fatura: Fatura) -> ResumoPagamentoFatura:
    resumo = calcular_resumo_pagamento(fatura)
    update_fields = []
    if fatura.status_pagamento != resumo.status_pagamento:
        fatura.status_pagamento = resumo.status_pagamento
        update_fields.append("status_pagamento")
    # Cache opcional mantido consistente para evitar estado obsoleto.
    if fatura.valor_total != resumo.total:
        fatura.valor_total = resumo.total
        update_fields.append("valor_total")
    if update_fields:
        fatura.save(update_fields=[*update_fields, "atualizada_em"])
    return resumo


def atualizar_status_pagamento(fatura: Fatura) -> ResumoPagamentoFatura:
    # Compatibilidade com chamadas existentes.
    return recalcular_fatura(fatura)


def _categoria_pagamento(usuario) -> Categoria:
    categoria = (
        Categoria.objects.filter(
            Q(usuario=usuario) | Q(padrao=True),
            tipo="despesa",
            ativa=True,
        )
        .order_by("nome")
        .first()
    )
    if categoria is None:
        raise ValidationError("Nenhuma categoria de despesa ativa disponível para registrar pagamento.")
    return categoria


def pagar_fatura(*, fatura: Fatura, valor: Decimal | None = None, descricao: str | None = None) -> Transacao:
    with transaction.atomic():
        fatura = Fatura.objects.select_for_update().get(pk=fatura.pk, usuario=fatura.usuario)
        resumo = calcular_resumo_pagamento(fatura)
        if resumo.saldo <= _zero():
            raise ValidationError("Esta fatura já está paga.")

        valor_pagamento = resumo.saldo if valor is None else valor
        if valor_pagamento <= _zero():
            raise ValidationError("Informe um valor de pagamento maior que zero.")
        if valor_pagamento > resumo.saldo:
            raise ValidationError("Valor do pagamento maior que o saldo restante da fatura.")

        categoria = _categoria_pagamento(fatura.usuario)
        transacao_pagamento = Transacao.objects.create(
            usuario=fatura.usuario,
            conta=fatura.cartao.conta_padrao,
            categoria=categoria,
            tipo="despesa",
            valor=valor_pagamento,
            data=timezone.localdate(),
            descricao=descricao
            or f"Pagamento fatura {fatura.cartao.nome} {fatura.competencia:%m/%Y}",
            pagamento_de_fatura=fatura,
        )
        atualizar_status_pagamento(fatura)
        return transacao_pagamento


def mover_lancamento(*, transacao: Transacao, fatura_destino: Fatura) -> None:
    if transacao.pagamento_de_fatura_id:
        raise ValidationError("Transação de pagamento de fatura não pode ser movida.")
    if transacao.usuario_id != fatura_destino.usuario_id:
        raise ValidationError("A fatura destino deve pertencer ao mesmo usuário.")
    if transacao.cartao_id != fatura_destino.cartao_id:
        raise ValidationError("Só é permitido mover para faturas do mesmo cartão.")
    with transaction.atomic():
        fatura_origem_id = transacao.fatura_id
        atualizadas = Transacao.objects.filter(
            pk=transacao.pk,
            usuario=transacao.usuario,
        ).update(fatura=fatura_destino)
        if atualizadas != 1:
            raise ValidationError("Não foi possível mover o lançamento.")

        fatura_destino_atual = Fatura.objects.select_for_update().get(pk=fatura_destino.pk)
        recalcular_fatura(fatura_destino_atual)

        if fatura_origem_id and fatura_origem_id != fatura_destino_atual.pk:
            fatura_origem_atual = Fatura.objects.select_for_update().get(pk=fatura_origem_id)
            recalcular_fatura(fatura_origem_atual)
