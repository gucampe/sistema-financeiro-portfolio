from __future__ import annotations

from decimal import Decimal

from django.conf import settings

from categorizacao.services.layers.fuzzy import classificar_fuzzy
from categorizacao.services.layers.historico import classificar_historico
from categorizacao.services.layers.ml_classico import classificar_ml
from categorizacao.services.layers.pg_trgm import classificar_pg_trgm
from categorizacao.services.layers.regras import (
    classificar_regras_globais,
    classificar_regras_usuario,
)
from categorizacao.services.normalizer import preparar_descricao
from categorizacao.services.pix_identity import (
    fingerprint_pix_person,
    is_pix_pessoa_fisica,
)
from categorizacao.types import (
    ContextoCategorizacao,
    PreferenciasCategorizacao,
    PredicaoCategorizacao,
    SugestaoCategorizacao,
    predicao_para_sugestao,
)

LIMIARES_PARADA = {
    "regra_usuario": 0.95,
    "regra_global": 0.90,
    "fuzzy": 0.85,
    "historico": 0.75,
    "pg_trgm": 0.78,
    "ml": 0.65,
}

CAMADAS = [
    ("regra_usuario", classificar_regras_usuario),
    ("regra_global", classificar_regras_globais),
    ("fuzzy", classificar_fuzzy),
    ("historico", classificar_historico),
    ("pg_trgm", classificar_pg_trgm),
    ("ml", classificar_ml),
]


def _construir_contexto(
    usuario,
    descricao: str,
    tipo: str,
    valor: Decimal | None = None,
) -> ContextoCategorizacao:
    norm, merchant = preparar_descricao(descricao or "")
    is_pf = is_pix_pessoa_fisica(descricao or "", norm)
    pix_key = fingerprint_pix_person(descricao or "") if is_pf else ""
    return ContextoCategorizacao(
        usuario=usuario,
        descricao=descricao or "",
        tipo=tipo,
        valor=valor,
        descricao_normalizada=norm,
        merchant_key=merchant,
        pix_person_key=pix_key,
        is_pix_pf=is_pf,
    )


def classificar(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    melhor: PredicaoCategorizacao | None = None
    for nome, fn in CAMADAS:
        pred = fn(ctx)
        if pred is None:
            continue
        limiar = LIMIARES_PARADA.get(nome, 0.70)
        if pred.confianca >= limiar:
            return pred
        if melhor is None or pred.confianca > melhor.confianca:
            melhor = pred
    return melhor


def _classificar_para_sugestao(
    ctx: ContextoCategorizacao,
    *,
    usar_llm: bool | None = None,
) -> PredicaoCategorizacao | None:
    llm_ligada = getattr(settings, "ENABLE_CATEGORIZACAO_LLM", False)
    if usar_llm is None:
        usar_llm = llm_ligada
    else:
        usar_llm = bool(usar_llm) and llm_ligada
    if usar_llm:
        from categorizacao.services.llm.orchestrator import classificar_com_llm

        return classificar_com_llm(ctx)
    return classificar(ctx)


def sugerir(
    usuario,
    descricao: str,
    tipo: str,
    valor: Decimal | None = None,
    prefs: PreferenciasCategorizacao | None = None,
    *,
    usar_llm: bool | None = None,
) -> SugestaoCategorizacao | None:
    ctx = _construir_contexto(usuario, descricao, tipo, valor)
    pred = _classificar_para_sugestao(ctx, usar_llm=usar_llm)
    if pred is None:
        return None
    if prefs is None:
        prefs = PreferenciasCategorizacao.from_usuario(usuario)
    return predicao_para_sugestao(pred, prefs, descricao=ctx.descricao)


def sugerir_batch(
    usuario,
    linhas: list[dict],
    prefs: PreferenciasCategorizacao | None = None,
    *,
    usar_llm: bool | None = None,
) -> list[SugestaoCategorizacao | None]:
    if prefs is None:
        prefs = PreferenciasCategorizacao.from_usuario(usuario)
    resultados = []
    for linha in linhas:
        descricao = linha.get("descricao", "")
        tipo = linha.get("tipo", "despesa")
        valor = linha.get("valor")
        if valor is not None and not isinstance(valor, Decimal):
            try:
                valor = Decimal(str(valor))
            except Exception:
                valor = None
        resultados.append(
            sugerir(usuario, descricao, tipo, valor, prefs, usar_llm=usar_llm)
        )
    return resultados
