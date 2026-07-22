# transacoes/services.py
from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from categorias.models import Categoria
from contas.models import Conta

from .models import Transacao

CATEGORIA_TRANSFERENCIA_NOME = "Transferência entre contas"


def obter_categoria_transferencia() -> Categoria:
    """Categoria sistema (padrao) usada nas duas pernas da transferência."""
    cat, _ = Categoria.objects.get_or_create(
        usuario=None,
        padrao=True,
        tipo="receita",
        nome=CATEGORIA_TRANSFERENCIA_NOME,
        defaults={
            "descricao": "Movimentações entre contas do mesmo usuário (não é receita nem despesa)",
            "cor": "#6B7280",
            "icone": "fa-exchange-alt",
            "ativa": True,
        },
    )
    return cat


def criar_transacao_saldo_inicial(usuario, conta, valor, data):
    """
    Cria uma transação do tipo ajuste com descrição "Saldo inicial" para a conta.
    Usada quando uma conta é criada com saldo inicial diferente de zero.
    """
    if valor == Decimal("0.00"):
        return None
    categoria_ajuste, _ = Categoria.objects.get_or_create(
        usuario=None,
        padrao=True,
        tipo="receita",
        nome="Ajustes de saldo",
        defaults={
            "descricao": "Ajustes automáticos de saldo de contas",
            "cor": "#6B7280",
            "icone": "fa-ellipsis-h",
            "ativa": True,
        },
    )
    return Transacao.objects.create(
        usuario=usuario,
        conta=conta,
        tipo="ajuste",
        valor=valor,
        descricao="Saldo inicial",
        data=data,
        categoria=categoria_ajuste,
    )


def _validar_contas_transferencia(usuario, conta_origem: Conta, conta_destino: Conta) -> None:
    if conta_origem.pk == conta_destino.pk:
        raise ValidationError({"conta_destino": "Conta de origem e destino devem ser diferentes."})
    if conta_origem.usuario_id != usuario.id or conta_destino.usuario_id != usuario.id:
        raise ValidationError("As contas devem pertencer ao usuário.")
    if not conta_origem.ativa:
        raise ValidationError({"conta_origem": "Conta de origem inválida ou inativa."})
    if not conta_destino.ativa:
        raise ValidationError({"conta_destino": "Conta de destino inválida ou inativa."})


def criar_transferencia(
    usuario,
    *,
    conta_origem: Conta,
    conta_destino: Conta,
    valor: Decimal,
    data,
    descricao: str = "Transferência",
) -> tuple[Transacao, Transacao]:
    """
    Cria as duas pernas da transferência vinculadas pelo mesmo transfer_id (UUID).
    Atomicidade: ambas ou nenhuma.
    """
    if valor is None or valor <= 0:
        raise ValidationError({"valor": "Informe um valor maior que zero."})
    _validar_contas_transferencia(usuario, conta_origem, conta_destino)

    desc = (descricao or "").strip() or "Transferência"
    categoria = obter_categoria_transferencia()
    transfer_id = uuid.uuid4()

    with transaction.atomic():
        tx_origem = Transacao(
            usuario=usuario,
            conta=conta_origem,
            tipo="transferencia",
            valor=valor,
            descricao=desc,
            data=data,
            categoria=categoria,
            transfer_id=transfer_id,
            papel_transferencia="origem",
        )
        tx_destino = Transacao(
            usuario=usuario,
            conta=conta_destino,
            tipo="transferencia",
            valor=valor,
            descricao=desc,
            data=data,
            categoria=categoria,
            transfer_id=transfer_id,
            papel_transferencia="destino",
        )
        tx_origem.save()
        tx_destino.save()

    return tx_origem, tx_destino


def obter_par_transferencia(usuario, transfer_id) -> tuple[Transacao, Transacao]:
    """Localiza as duas pernas pelo transfer_id; levanta ValidationError se incompleto."""
    qs = (
        Transacao.objects.filter(
            usuario=usuario,
            transfer_id=transfer_id,
            tipo="transferencia",
        )
        .select_related("conta", "categoria")
        .order_by("papel_transferencia")
    )
    pernas = list(qs)
    if len(pernas) != 2:
        raise ValidationError(
            f"Transferência {transfer_id} inválida: esperado 2 lançamentos, encontrados {len(pernas)}."
        )
    por_papel = {t.papel_transferencia: t for t in pernas}
    if set(por_papel) != {"origem", "destino"}:
        raise ValidationError(f"Transferência {transfer_id} sem origem e destino.")
    return por_papel["origem"], por_papel["destino"]


def atualizar_transferencia(
    usuario,
    transfer_id,
    *,
    conta_origem: Conta | None = None,
    conta_destino: Conta | None = None,
    valor: Decimal | None = None,
    data=None,
    descricao: str | None = None,
) -> tuple[Transacao, Transacao]:
    """Atualiza as duas pernas vinculadas pelo transfer_id (mesmos valor/data/descrição)."""
    with transaction.atomic():
        tx_origem, tx_destino = obter_par_transferencia(usuario, transfer_id)
        nova_origem = conta_origem or tx_origem.conta
        nova_destino = conta_destino or tx_destino.conta
        _validar_contas_transferencia(usuario, nova_origem, nova_destino)

        if valor is not None:
            if valor <= 0:
                raise ValidationError({"valor": "Informe um valor maior que zero."})
            tx_origem.valor = valor
            tx_destino.valor = valor

        if data is not None:
            tx_origem.data = data
            tx_destino.data = data

        if descricao is not None:
            desc = descricao.strip() or "Transferência"
            tx_origem.descricao = desc
            tx_destino.descricao = desc

        tx_origem.conta = nova_origem
        tx_destino.conta = nova_destino
        tx_origem.save()
        tx_destino.save()

    return tx_origem, tx_destino


def excluir_transferencia(usuario, transfer_id) -> None:
    """Exclui as duas pernas vinculadas pelo transfer_id."""
    with transaction.atomic():
        obter_par_transferencia(usuario, transfer_id)
        Transacao.objects.filter(
            usuario=usuario,
            transfer_id=transfer_id,
            tipo="transferencia",
        ).delete()
