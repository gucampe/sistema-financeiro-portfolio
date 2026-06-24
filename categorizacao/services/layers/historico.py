from __future__ import annotations

from categorizacao.services.memory_lookup import buscar_memoria_humana
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

MIN_SCORE = 0.65
MIN_CONFIRMACOES = 1


def classificar_historico(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    memoria, match_tipo = buscar_memoria_humana(ctx)
    if memoria is None:
        return None
    if memoria.confirmacoes < MIN_CONFIRMACOES:
        return None
    if memoria.score < MIN_SCORE:
        return None
    if not memoria.categoria.ativa:
        return None

    confianca = min(0.98, 0.70 + memoria.score * 0.28)
    explicacao = (
        f"Você categorizou {memoria.merchant_key} como {memoria.categoria.nome} "
        f"{memoria.confirmacoes} vez(es)"
    )
    if match_tipo.startswith("pix") or match_tipo.startswith("fuzzy"):
        explicacao = (
            f"Aprendizado anterior similar ({match_tipo}): "
            f"{memoria.categoria.nome}"
        )

    return PredicaoCategorizacao(
        categoria_id=memoria.categoria_id,
        categoria_nome=memoria.categoria.nome,
        confianca=confianca,
        fonte="historico",
        merchant_key=memoria.merchant_key,
        explicacao=explicacao,
        contexto={
            "historico_match": match_tipo,
            "human_memory": True,
        },
    )
