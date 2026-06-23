from __future__ import annotations

import re

from unidecode import unidecode

# Ruído comum em extratos bancários brasileiros
_RUIDO_BANCARIO = re.compile(
    r"\b("
    r"COMPRA\s+CARTAO|COMPRA\s+CART|DEBITO|CREDITO|CRED|"
    r"PIX\s+(ENVIADO|RECEBIDO|TRANSF)|TED|DOC|TRANSFERENCIA|"
    r"PAGTO|PAGAMENTO|PGTO|TAR|"
    r"SAO\s+PAULO|RIO\s+DE\s+JANEIRO|BRASIL|BR\b"
    r")\b",
    re.IGNORECASE,
)
_DATA_PATTERN = re.compile(r"\b\d{2}[/.]\d{2}([/.]\d{2,4})?\b")
_CODIGO_NUMERICO = re.compile(r"\b\d{4,}\b")
_CARACTERES_ESPECIAIS = re.compile(r"[^\w\s]")
_ESPACOS = re.compile(r"\s+")

_STOPWORDS = frozenset(
    {
        "DE",
        "DA",
        "DO",
        "DAS",
        "DOS",
        "EM",
        "NO",
        "NA",
        "PARA",
        "COM",
        "POR",
        "LTDA",
        "ME",
        "EPP",
        "SA",
        "EIRELI",
        "THE",
        "AND",
    }
)


def normalizar_texto(descricao: str) -> str:
    if not descricao:
        return ""
    texto = unidecode(descricao).upper().strip()
    texto = _DATA_PATTERN.sub(" ", texto)
    texto = _RUIDO_BANCARIO.sub(" ", texto)
    texto = _CODIGO_NUMERICO.sub(" ", texto)
    texto = _CARACTERES_ESPECIAIS.sub(" ", texto)
    texto = _ESPACOS.sub(" ", texto).strip()
    return texto


def extrair_merchant_key(descricao_normalizada: str) -> str:
    if not descricao_normalizada:
        return ""
    tokens = [
        t
        for t in descricao_normalizada.split()
        if len(t) >= 2 and t not in _STOPWORDS and not t.isdigit()
    ]
    if not tokens:
        return descricao_normalizada.lower()[:120]
    # Prioriza tokens mais longos (geralmente nome do estabelecimento)
    tokens.sort(key=len, reverse=True)
    principais = tokens[:3]
    principais.sort(key=lambda t: descricao_normalizada.find(t))
    return " ".join(principais).lower()[:120]


def normalizar_padrao_regra(padrao: str) -> str:
    return normalizar_texto(padrao).lower()


def preparar_descricao(descricao: str) -> tuple[str, str]:
    norm = normalizar_texto(descricao)
    merchant = extrair_merchant_key(norm)
    return norm, merchant
