"""
Calibragem de confiança por trust tier — separa risco semântico de confiança da sugestão.

Política UX (importação): assumir posição — auto-selecionar sempre que houver sugestão;
prudência agregada no modal de confirmação, não linha a linha.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from categorizacao.services.normalizer import normalizar_texto
from categorizacao.services.pix_identity import is_pix_pessoa_fisica, is_pix_transferencia_raw
from categorizacao.types import SugestaoCategorizacao

TIER_BAIXO_RISCO = 1
TIER_MEDIO_RISCO = 2
TIER_ALTO_RISCO = 3

_LIMIAR_ALTA = 0.85
_LIMIAR_MEDIA = 0.55

# Merchants / padrões financeiros altamente reconhecíveis (Tier 1)
_TIER1_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(cdb|rdb|lci|lca|debenture|tesouro|selic|cdi)\b",
        r"\b(aplicacao|aplicação|aplicac|resgate|investimento|investimentos)\b",
        r"\b(rendimento|dividendo|juros\s+sobre|remuneracao|remuneração)\b",
        r"\b(netflix|spotify|amazon\s*prime|prime\s*video|disney\+?|hbo|globoplay|deezer)\b",
        r"\b(uber|99pop|99\s*app|ifood|rappi|ze\s*delivery)\b",
        r"\b(iof|tarifa\s+bancaria|tarifa\s+bancária|anuidade)\b",
        r"\b(salario|salário|folha\s+de\s+pagamento|provento)\b",
        r"\b(aluguel|condominio|condomínio)\b",
        r"\b(fatura\s+cartao|fatura\s+cartão|pagamento\s+fatura)\b",
    )
)

_TIER3_TRANSFER_MARKERS = re.compile(
    r"\b(pix|ted|doc|transferencia|transferência|transf)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResultadoUXConfianca:
    pre_preencher: bool
    nivel: str  # alta | media | baixa
    trust_tier: int
    requires_confirmacao: bool


def classificar_trust_tier(descricao: str, contexto: dict | None = None) -> int:
    ctx = contexto or {}
    if ctx.get("is_pix_pf"):
        return TIER_ALTO_RISCO

    raw = (descricao or "").strip()
    norm = normalizar_texto(raw).lower()

    if is_pix_pessoa_fisica(raw, norm):
        return TIER_ALTO_RISCO

    if _TIER3_TRANSFER_MARKERS.search(raw) or _TIER3_TRANSFER_MARKERS.search(norm):
        if not any(p.search(norm) or p.search(raw) for p in _TIER1_PATTERNS):
            return TIER_ALTO_RISCO

    if any(p.search(norm) or p.search(raw) for p in _TIER1_PATTERNS):
        return TIER_BAIXO_RISCO

    return TIER_MEDIO_RISCO


def _nivel_visual(sug: SugestaoCategorizacao, conf: float) -> str:
    ctx = sug.contexto or {}
    fonte = sug.fonte or ""
    if (
        conf >= _LIMIAR_ALTA
        or fonte in ("historico", "regra_usuario")
        or ctx.get("human_memory")
    ):
        return "alta"
    if conf >= _LIMIAR_MEDIA:
        return "media"
    return "baixa"


def resolver_ux_importacao(
    sug: SugestaoCategorizacao,
    descricao: str,
) -> ResultadoUXConfianca:
    """
    Auto-seleciona sempre que existir categoria sugerida.
    Sem hipótese utilizável → combobox vazia + nível baixa.
  Prudência apenas no popup agregado (requires_confirmacao=False por linha).
    """
    ctx = dict(sug.contexto or {})
    tier = classificar_trust_tier(descricao, ctx)

    if not sug.categoria_id:
        return ResultadoUXConfianca(
            pre_preencher=False,
            nivel="baixa",
            trust_tier=tier,
            requires_confirmacao=False,
        )

    conf = float(sug.confianca or 0)
    nivel = _nivel_visual(sug, conf)

    return ResultadoUXConfianca(
        pre_preencher=True,
        nivel=nivel,
        trust_tier=tier,
        requires_confirmacao=False,
    )


def deve_exigir_confirmacao_llm(
    descricao: str,
    confianca: float,
    contexto: dict | None = None,
) -> bool:
    """Gate LLM — apenas PIX PF alto risco sem memória humana exige flag interna."""
    ctx = contexto or {}
    if (classificar_trust_tier(descricao, ctx) == TIER_ALTO_RISCO or ctx.get("is_pix_pf")) and not (
        ctx.get("human_memory")
    ):
        return confianca < _LIMIAR_MEDIA
    return False
