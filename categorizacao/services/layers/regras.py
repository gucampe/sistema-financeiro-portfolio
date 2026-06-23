from __future__ import annotations

import re

from categorizacao.models import RegraCategorizacao
from categorizacao.services.cache import get_regras_globais, get_regras_usuario
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao


def _tipo_compativel(ctx: ContextoCategorizacao, regra: RegraCategorizacao) -> bool:
    if not regra.tipo_transacao:
        return True
    if ctx.tipo == "ajuste":
        return regra.tipo_transacao == "receita"
    return regra.tipo_transacao == ctx.tipo


def _categoria_ativa_para_usuario(ctx: ContextoCategorizacao, regra: RegraCategorizacao) -> bool:
    cat = regra.categoria
    if not cat.ativa:
        return False
    if cat.padrao:
        return True
    return cat.usuario_id == ctx.usuario.pk


def _match_regra(ctx: ContextoCategorizacao, regra: RegraCategorizacao) -> bool:
    texto = ctx.descricao_normalizada.lower()
    padrao = regra.padrao_normalizado
    if regra.tipo_regra == "contains":
        return padrao in texto or padrao in ctx.merchant_key
    if regra.tipo_regra == "startswith":
        return texto.startswith(padrao) or ctx.merchant_key.startswith(padrao)
    if regra.tipo_regra == "merchant_exact":
        return ctx.merchant_key == padrao
    if regra.tipo_regra == "regex":
        try:
            return bool(re.search(regra.padrao, ctx.descricao, re.IGNORECASE))
        except re.error:
            return False
    return False


def _avaliar_regras(
    ctx: ContextoCategorizacao,
    regras: list[RegraCategorizacao],
    fonte: str,
) -> PredicaoCategorizacao | None:
    for regra in regras:
        if not _tipo_compativel(ctx, regra):
            continue
        if not _categoria_ativa_para_usuario(ctx, regra):
            continue
        if not _match_regra(ctx, regra):
            continue
        return PredicaoCategorizacao(
            categoria_id=regra.categoria_id,
            categoria_nome=regra.categoria.nome,
            confianca=regra.confianca_base,
            fonte=fonte,
            merchant_key=ctx.merchant_key or None,
            explicacao=f'Regra: descrição corresponde a "{regra.padrao}"',
        )
    return None


def classificar_regras_usuario(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    regras = get_regras_usuario(ctx.usuario.pk)
    return _avaliar_regras(ctx, regras, "regra_usuario")


def classificar_regras_globais(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    regras = get_regras_globais()
    return _avaliar_regras(ctx, regras, "regra_global")
