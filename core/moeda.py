"""Parsing de valores monetários no formato brasileiro (pt-BR)."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


def parse_decimal_moeda_br(raw) -> Decimal:
    """
    Converte string monetária BR para Decimal.
    Aceita: "1234.56", "1.234,56", "R$ 1.234,56", "1234,56".
    Vazio retorna Decimal("0").
    """
    s = ("" if raw is None else str(raw)).strip()
    if not s:
        return Decimal("0")

    s = re.sub(r"[R$r$\s]", "", s, flags=re.IGNORECASE)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")

    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError("Valor monetário inválido.") from exc
