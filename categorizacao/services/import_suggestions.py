from __future__ import annotations

from categorizacao.services.trust_tiers import resolver_ux_importacao
from categorizacao.types import SugestaoCategorizacao


FONTE_UX_LABELS: dict[str, dict[str, str | bool]] = {
    "historico": {"label": "Histórico", "badge": "Com base no seu histórico", "aprendizado": True},
    "regra_usuario": {"label": "Regra sua", "badge": "Sua regra", "aprendizado": True},
    "regra_global": {"label": "Regra", "badge": "", "aprendizado": False},
    "fuzzy": {"label": "Baseado em transações parecidas", "badge": "", "aprendizado": False},
    "pg_trgm": {"label": "Baseado em transações parecidas", "badge": "", "aprendizado": False},
    "ml": {"label": "Sugestão inteligente", "badge": "", "aprendizado": False},
    "llm_gemini": {"label": "Sugestão inteligente", "badge": "", "aprendizado": False},
}


def enriquecer_sugestao_dict(sug_dict: dict) -> dict:
    """Adiciona metadados UX (badge, label) à sugestão serializada."""
    fonte = sug_dict.get("fonte") or ""
    ctx = sug_dict.get("contexto") or {}
    meta = FONTE_UX_LABELS.get(fonte, {"label": fonte or "Sugestão", "badge": "", "aprendizado": False})
    if fonte == "historico" or ctx.get("human_memory"):
        meta = {**meta, "badge": "Com base no seu histórico", "aprendizado": True}
    if ctx.get("historico_match", "").startswith(("pix", "fuzzy")):
        meta = {**meta, "badge": "Com base no seu histórico", "aprendizado": True}
    sug_dict["fonte_label"] = meta["label"]
    sug_dict["badge_aprendizado"] = meta.get("badge") or ""
    sug_dict["eh_aprendizado"] = bool(meta.get("aprendizado"))
    return sug_dict


def aplicar_sugestao_em_linha(item: dict, sug: SugestaoCategorizacao | None) -> dict:
    if not sug:
        return item
    sug_dict = enriquecer_sugestao_dict(sug.to_dict())
    descricao = (item.get("descricao") or "").strip()
    ux = resolver_ux_importacao(sug, descricao)

    item["categoria_sugerida_id"] = sug.categoria_id
    item["categoria_sugerida_nome"] = sug.categoria_nome
    item["categoria_sugerida_confianca"] = sug.confianca
    item["categoria_sugerida_fonte"] = sug.fonte
    item["categoria_sugerida_explicacao"] = sug.explicacao
    item["categoria_sugerida_auto_aplicar"] = sug.auto_aplicar
    item["categoria_sugerida_merchant_key"] = sug.merchant_key or ""
    item["categoria_sugerida_requires_confirmacao"] = ux.requires_confirmacao
    item["categoria_sugerida_mostrar_badge_ia"] = sug_dict.get("mostrar_badge_ia", False)
    item["categoria_sugerida_fonte_label"] = sug_dict.get("fonte_label", "")
    item["categoria_sugerida_badge_aprendizado"] = sug_dict.get("badge_aprendizado", "")
    item["categoria_sugerida_eh_aprendizado"] = sug_dict.get("eh_aprendizado", False)
    item["categoria_sugerida_pre_preencher"] = ux.pre_preencher
    item["categoria_sugerida_nivel_confianca"] = ux.nivel
    item["categoria_sugerida_trust_tier"] = ux.trust_tier
    return item
