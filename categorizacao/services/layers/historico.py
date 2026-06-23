from __future__ import annotations

from categorizacao.models import MemoriaMerchantUsuario
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

MIN_SCORE = 0.65
MIN_CONFIRMACOES = 1


def classificar_historico(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    if not ctx.merchant_key:
        return None

    memoria = (
        MemoriaMerchantUsuario.objects.filter(
            usuario=ctx.usuario,
            merchant_key=ctx.merchant_key,
        )
        .select_related("categoria")
        .first()
    )
    if memoria is None or memoria.confirmacoes < MIN_CONFIRMACOES:
        return None
    if memoria.score < MIN_SCORE:
        return None
    if not memoria.categoria.ativa:
        return None

    confianca = min(0.98, 0.70 + memoria.score * 0.28)
    return PredicaoCategorizacao(
        categoria_id=memoria.categoria_id,
        categoria_nome=memoria.categoria.nome,
        confianca=confianca,
        fonte="historico",
        merchant_key=ctx.merchant_key,
        explicacao=(
            f"Você categorizou {ctx.merchant_key} como {memoria.categoria.nome} "
            f"{memoria.confirmacoes} vez(es)"
        ),
    )
