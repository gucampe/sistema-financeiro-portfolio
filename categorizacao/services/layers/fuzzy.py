from __future__ import annotations

from rapidfuzz import fuzz

from categorizacao.services.merchant import (
    get_merchants_ativos,
    merchant_aliases_flat,
    resolver_categoria_padrao,
)
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

FUZZY_THRESHOLD = 85


def classificar_fuzzy(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    if not ctx.merchant_key and not ctx.descricao_normalizada:
        return None

    texto = ctx.merchant_key or ctx.descricao_normalizada.lower()
    tipo = "receita" if ctx.tipo == "ajuste" else ctx.tipo
    if tipo not in ("receita", "despesa"):
        return None

    melhor_score = 0
    melhor_merchant = None
    melhor_alias = ""

    for merchant in get_merchants_ativos():
        if merchant.tipo != tipo:
            continue
        for alias in merchant_aliases_flat(merchant):
            score = fuzz.token_set_ratio(texto, alias)
            if score > melhor_score:
                melhor_score = score
                melhor_merchant = merchant
                melhor_alias = alias

    if melhor_score < FUZZY_THRESHOLD or melhor_merchant is None:
        return None

    categoria = resolver_categoria_padrao(
        ctx.usuario,
        melhor_merchant.categoria_padrao_nome,
        melhor_merchant.tipo,
    )
    if categoria is None:
        return None

    confianca = min(0.99, melhor_score / 100.0)
    return PredicaoCategorizacao(
        categoria_id=categoria.pk,
        categoria_nome=categoria.nome,
        confianca=confianca,
        fonte="fuzzy",
        merchant_key=melhor_merchant.canonical_name,
        explicacao=f"Merchant similar a {melhor_merchant.canonical_name} ({melhor_score}%)",
    )
