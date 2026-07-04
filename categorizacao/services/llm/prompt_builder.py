from __future__ import annotations

import re
import unicodedata

PROMPT_VERSION = "v2"

SYSTEM_PROMPT = """Você é um classificador financeiro brasileiro. Responda SOMENTE com JSON válido no schema fornecido.
Regras:
- Use APENAS categoria_slug da lista fornecida pelo usuário.
- Não invente categorias nem dados pessoais.
- Nunca inferir relações familiares, afetivas ou sociais sem evidência clara.
- PIX ou transferência para pessoa física sem contexto comercial: prefira slug diversos ou equivalente neutro; marque ambigua=true e confianca <= 0.55.
- Em dúvida: ambigua=true, confianca baixa, prefira não categorizar com alta confiança.
- Padaria/mercado local: alimentacao ou supermercado conforme contexto explícito.
- confianca entre 0 e 1.
"""

FEW_SHOT = """
Exemplos:
- "ifood restaurante" despesa → alimentacao (0.92)
- "pix enviado pessoa" despesa → diversos (0.50, ambigua=true)
- "padaria sao jose" despesa → alimentacao (0.80)
- "uber trip" despesa → transporte (0.90)
- "amazon br" despesa → compras (0.70, ambigua=true)
"""


def slugify_categoria(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "outros"


def redact_pii_for_llm(descricao: str) -> str:
    """Reduz exposição de nomes em PIX."""
    d = descricao
    d = re.sub(
        r"(pix\s+(?:enviado|recebido|transf)?\s*)([a-z]{2,}(?:\s+[a-z]{2,}){0,3})",
        r"\1[PESSOA]",
        d,
        flags=re.IGNORECASE,
    )
    return d[:200]


def valor_faixa(valor) -> str:
    if valor is None:
        return "omitir"
    try:
        v = abs(float(valor))
    except (TypeError, ValueError):
        return "omitir"
    if v <= 100:
        return "ate_100"
    if v <= 500:
        return "100_500"
    return "500_plus"


def _template_hint(desc_norm: str, merchant_key: str) -> str:
    if "pix" in desc_norm or "pix" in merchant_key:
        return "pix"
    if not merchant_key and len(desc_norm) > 20:
        return "ruido"
    if any(w in desc_norm for w in ("amazon", "magalu", "mercado livre", "shopee")):
        return "ambiguo"
    return "geral"


def build_prompts(
    *,
    descricao_normalizada: str,
    merchant_key: str,
    tipo: str,
    valor,
    categorias: list[dict],
) -> tuple[str, str]:
    desc_safe = redact_pii_for_llm(descricao_normalizada)
    cats_lines = "\n".join(
        f"- slug: {c['slug']}, nome: {c['nome']}, tipo: {c['tipo']}"
        for c in sorted(categorias, key=lambda x: x["slug"])
    )
    hint = _template_hint(desc_safe, merchant_key)
    user = f"""tipo_transacao: {tipo}
<transacao>
descricao_normalizada: {desc_safe}
merchant_key: {merchant_key or "desconhecido"}
</transacao>
valor_faixa: {valor_faixa(valor)}
template: {hint}
prompt_version: {PROMPT_VERSION}

categorias_usuario:
{cats_lines}
"""
    system = SYSTEM_PROMPT + FEW_SHOT
    return system, user
