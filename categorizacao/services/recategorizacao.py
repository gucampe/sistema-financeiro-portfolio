from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from categorias.models import Categoria
from categorizacao.services.learning import processar_feedback_transacao
from categorizacao.services.pipeline import sugerir
from categorizacao.types import LIMIARES_FONTE
from transacoes.models import Transacao


def recategorizar_transacoes(
    *,
    usuario,
    categoria_nome: str = "Diversos",
    dry_run: bool = False,
    limite: int = 500,
) -> dict:
    categoria = Categoria.objects.filter(
        Q(usuario=usuario) | Q(padrao=True),
        nome__iexact=categoria_nome,
        ativa=True,
    ).first()
    if not categoria:
        return {"analisadas": 0, "sugestoes": 0, "aplicadas": 0}

    transacoes = (
        Transacao.objects.filter(usuario=usuario, categoria=categoria)
        .order_by("-data")[:limite]
    )

    analisadas = 0
    sugestoes = 0
    aplicadas = 0

    for tx in transacoes:
        analisadas += 1
        sug = sugerir(usuario, tx.descricao, tx.tipo, tx.valor)
        if sug is None:
            continue
        limiar = LIMIARES_FONTE.get(sug.fonte, {}).get("preencher", 0.70)
        if sug.confianca < limiar:
            continue
        sugestoes += 1
        if dry_run:
            aplicadas += 1
            continue
        with transaction.atomic():
            tx.categoria_id = sug.categoria_id
            tx.save(update_fields=["categoria"])
            processar_feedback_transacao(
                usuario=usuario,
                transacao=tx,
                descricao=tx.descricao,
                categoria_final=tx.categoria,
                categoria_sugerida_id=sug.categoria_id,
                confianca=sug.confianca,
                fonte=sug.fonte,
                merchant_key=sug.merchant_key or "",
            )
            aplicadas += 1

    return {"analisadas": analisadas, "sugestoes": sugestoes, "aplicadas": aplicadas}
