from __future__ import annotations

from rapidfuzz import fuzz

from categorizacao.models import MemoriaMerchantUsuario
from categorizacao.services.pix_identity import (
    fingerprint_pix_person,
    is_pix_pessoa_fisica,
    keys_sao_similares,
    merchant_keys_para_busca,
)
from categorizacao.services.observability import (
    log_human_memory_used,
    log_pix_similarity_match,
)
from categorizacao.types import ContextoCategorizacao

MIN_SCORE_HUMANO = 0.65
MIN_CONFIRMACOES_HUMANO = 1
FUZZY_MEMORY_THRESHOLD = 90


def is_fonte_llm(fonte: str) -> bool:
    f = (fonte or "").lower()
    return f in ("llm_gemini", "llm", "ai") or f.startswith("llm_")


def memoria_humana_confirmada(memoria: MemoriaMerchantUsuario) -> bool:
    origem = getattr(memoria, "origem", "human") or "human"
    if origem != "human":
        return False
    if memoria.confirmacoes < MIN_CONFIRMACOES_HUMANO:
        return False
    return memoria.score >= MIN_SCORE_HUMANO


def buscar_memoria_humana(
    ctx: ContextoCategorizacao,
) -> tuple[MemoriaMerchantUsuario | None, str]:
    """
    Busca memória humana confirmada: match exato, fingerprint PIX PF ou similaridade leve.
    Retorna (memoria, motivo_match).
    """
    user_id = getattr(ctx.usuario, "pk", None) if ctx.usuario else None
    if not user_id:
        return None, ""

    candidatas = merchant_keys_para_busca(ctx.descricao, ctx.merchant_key)
    if ctx.pix_person_key and ctx.pix_person_key not in candidatas:
        candidatas.append(ctx.pix_person_key)

    memorias = list(
        MemoriaMerchantUsuario.objects.filter(usuario=ctx.usuario)
        .select_related("categoria")
        .order_by("-confirmacoes", "-score")
    )
    if not memorias:
        return None, ""

    for key in candidatas:
        for mem in memorias:
            if not memoria_humana_confirmada(mem):
                continue
            if mem.merchant_key == key:
                log_human_memory_used(user_id, key, "exact")
                return mem, "exact"

    if is_pix_pessoa_fisica(ctx.descricao, ctx.descricao_normalizada):
        fp = ctx.pix_person_key or fingerprint_pix_person(ctx.descricao)
        for mem in memorias:
            if not memoria_humana_confirmada(mem):
                continue
            if keys_sao_similares(fp, mem.merchant_key) or keys_sao_similares(
                ctx.merchant_key, mem.merchant_key
            ):
                log_pix_similarity_match(user_id, ctx.merchant_key, mem.merchant_key)
                return mem, "pix_similarity"

        for mem in memorias:
            if not memoria_humana_confirmada(mem):
                continue
            score = fuzz.token_set_ratio(
                ctx.merchant_key or fp,
                mem.merchant_key.removeprefix("pix_person:"),
            )
            if score >= FUZZY_MEMORY_THRESHOLD:
                log_pix_similarity_match(user_id, ctx.merchant_key, mem.merchant_key)
                return mem, f"fuzzy_{score}"

    return None, ""


def tem_memoria_humana_bloqueante(ctx: ContextoCategorizacao) -> bool:
    mem, _ = buscar_memoria_humana(ctx)
    return mem is not None
