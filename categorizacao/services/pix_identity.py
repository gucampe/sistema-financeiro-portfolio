from __future__ import annotations

import re

from unidecode import unidecode

from categorizacao.services.normalizer import (
    _CODIGO_NUMERICO,
    _RUIDO_BANCARIO,
    _STOPWORDS,
    extrair_merchant_key,
    normalizar_texto,
)

_PIX_RAW_MARKERS = re.compile(
    r"\b(pix|ted|doc|transferencia)\b",
    re.IGNORECASE,
)

_CORPORATE_TOKENS = frozenset(
    {
        "LTDA",
        "ME",
        "EPP",
        "SA",
        "S/A",
        "EIRELI",
        "INSTITUICAO",
        "INSTITUIÇÃO",
        "PAGAMENTOS",
        "PAGAMENTO",
        "BANCO",
        "FOOD",
        "SERVICOS",
        "SERVIÇOS",
        "DISTRIBUICAO",
        "DISTRIBUIÇÃO",
        "COMERCIO",
        "COMÉRCIO",
        "HOLDING",
        "PARTICIPACOES",
        "PARTICIPAÇÕES",
        "FAST",
        "INTERNACIONAL",
        "BRASIL",
        "DIGITAIS",
    }
)


def is_pix_transferencia_raw(descricao: str) -> bool:
    return bool(_PIX_RAW_MARKERS.search(descricao or ""))


def _tokens_nome(texto: str) -> list[str]:
    tokens = [
        t
        for t in texto.split()
        if len(t) >= 2 and t not in _STOPWORDS and not t.isdigit()
    ]
    return tokens


def is_pix_pessoa_fisica(descricao: str, descricao_normalizada: str | None = None) -> bool:
    """Heurística conservadora: PIX/TED com nome de pessoa, sem sinais corporativos."""
    raw = descricao or ""
    if not is_pix_transferencia_raw(raw):
        return False
    norm = descricao_normalizada or normalizar_texto(raw)
    upper = norm.upper()
    if any(tok in upper.split() for tok in _CORPORATE_TOKENS):
        return False
    tokens = _tokens_nome(norm)
    if len(tokens) < 2:
        return False
    # Nome pessoal típico: pelo menos 2 tokens alfabéticos sem dígitos longos
    alpha_tokens = [t for t in tokens if t.isalpha() and len(t) >= 3]
    return len(alpha_tokens) >= 2


def extrair_nome_pix_pf(descricao: str) -> str:
    """Remove ruído bancário e numérico; preserva nome completo possível."""
    texto = unidecode(descricao or "").upper().strip()
    texto = _RUIDO_BANCARIO.sub(" ", texto)
    texto = _CODIGO_NUMERICO.sub(" ", texto)
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    tokens = _tokens_nome(texto)
    if not tokens:
        return ""
    # Ordena por posição original para manter ordem do nome
    tokens.sort(key=lambda t: texto.find(t))
    return " ".join(tokens).lower()[:120]


def fingerprint_pix_person(descricao: str) -> str:
    """Chave canônica estável para PIX pessoa física."""
    nome = extrair_nome_pix_pf(descricao)
    if not nome:
        return ""
    return f"pix_person:{nome}"


def merchant_keys_para_busca(descricao: str, merchant_key: str) -> list[str]:
    """Chaves candidatas para lookup de memória (exata + PIX PF)."""
    keys: list[str] = []
    if merchant_key:
        keys.append(merchant_key)
    if is_pix_pessoa_fisica(descricao):
        fp = fingerprint_pix_person(descricao)
        if fp and fp not in keys:
            keys.append(fp)
        nome = extrair_nome_pix_pf(descricao)
        if nome and nome not in keys:
            keys.append(nome)
    return keys


def tokens_relevantes(key: str) -> set[str]:
    raw = key.removeprefix("pix_person:")
    return {t for t in raw.split() if len(t) >= 3 and t not in _STOPWORDS}


def overlap_tokens(a: str, b: str) -> int:
    return len(tokens_relevantes(a) & tokens_relevantes(b))


def keys_sao_similares(a: str, b: str, *, min_overlap: int = 2) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    na = a.removeprefix("pix_person:")
    nb = b.removeprefix("pix_person:")
    if na in nb or nb in na:
        return True
    ta, tb = tokens_relevantes(a), tokens_relevantes(b)
    if len(ta & tb) >= min_overlap:
        return True
    sa, sb = " ".join(sorted(ta)), " ".join(sorted(tb))
    return sa in sb or sb in sa
