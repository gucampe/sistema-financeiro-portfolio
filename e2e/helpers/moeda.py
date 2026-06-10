from __future__ import annotations

import re
from decimal import Decimal

_RE_MOEDA = re.compile(r"[^\d,.-]")


def parse_moeda_ptbr(texto: str) -> Decimal:
    limpo = _RE_MOEDA.sub("", texto.strip())
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    return Decimal(limpo)


def format_moeda_input(valor: Decimal) -> str:
    """Formato aceito pelo MoedaInput (digitação simulada)."""
    s = f"{valor:.2f}".replace(".", ",")
    partes = s.split(",")
    inteiros = partes[0]
    if len(inteiros) > 3:
        grupos = []
        while inteiros:
            grupos.insert(0, inteiros[-3:])
            inteiros = inteiros[:-3]
        inteiros = ".".join(grupos)
    return f"{inteiros},{partes[1]}" if len(partes) > 1 else inteiros
