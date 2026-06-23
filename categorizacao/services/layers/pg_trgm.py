from __future__ import annotations

from django.db import connection

from categorizacao.services.merchant import (
    get_merchants_ativos,
    resolver_categoria_padrao,
)
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

MIN_SIMILARITY = 0.35


def _pg_trgm_disponivel() -> bool:
    if connection.vendor != "postgresql":
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"
            )
            return cursor.fetchone() is not None
    except Exception:
        return False


def classificar_pg_trgm(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    if not _pg_trgm_disponivel():
        return None
    if not ctx.merchant_key:
        return None

    tipo = "receita" if ctx.tipo == "ajuste" else ctx.tipo
    if tipo not in ("receita", "despesa"):
        return None

    melhor_sim = 0.0
    melhor_nome = None

    with connection.cursor() as cursor:
        for merchant in get_merchants_ativos():
            if merchant.tipo != tipo:
                continue
            cursor.execute(
                "SELECT similarity(%s, %s)",
                [ctx.merchant_key, merchant.canonical_name],
            )
            row = cursor.fetchone()
            sim = float(row[0]) if row else 0.0
            if sim > melhor_sim:
                melhor_sim = sim
                melhor_nome = merchant

    if melhor_sim < MIN_SIMILARITY or melhor_nome is None:
        return None

    categoria = resolver_categoria_padrao(
        ctx.usuario,
        melhor_nome.categoria_padrao_nome,
        melhor_nome.tipo,
    )
    if categoria is None:
        return None

    confianca = min(0.92, 0.55 + melhor_sim * 0.4)
    return PredicaoCategorizacao(
        categoria_id=categoria.pk,
        categoria_nome=categoria.nome,
        confianca=confianca,
        fonte="pg_trgm",
        merchant_key=melhor_nome.canonical_name,
        explicacao=f"Similaridade textual com {melhor_nome.canonical_name}",
    )
