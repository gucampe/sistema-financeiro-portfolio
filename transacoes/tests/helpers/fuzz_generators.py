"""Geradores fuzz determinísticos para importação OFX/XLSX (sem hypothesis)."""

from __future__ import annotations

import io
import random
from datetime import date, timedelta
from typing import Iterator

from openpyxl import Workbook

from transacoes.tests.helpers.import_fixtures import (
    _OFX_FOOTER,
    _OFX_HEADER,
    _stmttrn,
    build_ofx_bytes,
    build_ofx_corrupto,
    build_xlsx_bytes,
    build_xlsx_invalid,
)
from transacoes.xlsx_parse import PLANILHA_CABECALHOS

_SPECIAL = "àéí ñ ç  \t\n©® <tag> PADÁRIA"
_AMOUNTS = ["-1.00", "-99.99", "10.00", "0.00", "1000000.00", "abc", ""]
_DATES = ["20240101120000", "invalid", "20241399120000", "  20240601120000  "]


class ImportFuzzGenerator:
    """Gera entradas sintéticas parcialmente válidas/inválidas com seed fixo."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = random.Random(seed)

    def iter_cases(self, n: int) -> Iterator[tuple[str, bytes]]:
        """n casos mistos OFX/XLSX."""
        for i in range(n):
            kind = self.rng.choice(["ofx_valid", "ofx_mut", "ofx_bad", "xlsx_valid", "xlsx_mut", "xlsx_bad"])
            yield kind, self._one(kind, i)

    def _one(self, kind: str, i: int) -> bytes:
        if kind == "ofx_valid":
            return self.ofx_valid(self.rng.randint(1, 8), prefix=f"v{i}")
        if kind == "ofx_mut":
            return self.ofx_mutated(i)
        if kind == "ofx_bad":
            return self.rng.choice(
                [
                    build_ofx_corrupto("lixo"),
                    build_ofx_corrupto("vazio"),
                    build_ofx_corrupto("truncado"),
                    self.rng.randbytes(self.rng.randint(1, 80)),
                ]
            )
        if kind == "xlsx_valid":
            return build_xlsx_bytes(
                self.rng.randint(1, 5),
                data_inicio=date(2024, 1, 1) + timedelta(days=i % 30),
                descricao=f"Fuzz {i} {_SPECIAL}",
            )
        if kind == "xlsx_mut":
            return self.xlsx_mutated(i)
        return self.rng.choice(
            [
                build_xlsx_invalid("vazio"),
                build_xlsx_invalid("cabecalho_errado"),
                build_xlsx_invalid("linha_data_invalida"),
            ]
        )

    def ofx_valid(self, n_tx: int, *, prefix: str = "fuzz") -> bytes:
        txs = []
        for j in range(n_tx):
            txs.append(
                {
                    "fitid": f"{prefix}-{j}-{self.rng.randint(0, 99999)}",
                    "trnamt": self.rng.choice(["-1.00", "-5.50", "12.00", "0.00"]),
                    "name": f"Fuzz {_SPECIAL} {j}",
                    "memo": self.rng.choice(["", "  memo  ", _SPECIAL]),
                    "dtposted": self.rng.choice(_DATES[:2]),
                }
            )
        return build_ofx_bytes(txs)

    def ofx_mutated(self, i: int) -> bytes:
        base = self.ofx_valid(self.rng.randint(1, 4), prefix=f"m{i}")
        mutators = [
            lambda b: b,
            lambda b: b[: max(50, len(b) // 3)],
            lambda b: b + self.rng.randbytes(30),
            lambda b: b.replace(b"STMTTRN", b"stmttrn"),
            lambda b: b.replace(b"<NAME>", b"<NAME>   "),
            lambda b: b.replace(b"</STMTTRN>", b""),
            lambda b: _OFX_HEADER.encode() + b"lixo" + _OFX_FOOTER.encode(),
        ]
        return self.rng.choice(mutators)(base)

    def xlsx_mutated(self, i: int) -> bytes:
        d0 = date(2024, 2, 1)
        wb = Workbook()
        ws = wb.active
        ws.append(list(PLANILHA_CABECALHOS) + ["extra_col"])
        for j in range(self.rng.randint(1, 6)):
            if self.rng.random() < 0.2:
                ws.append([None, None, None])
                continue
            d = d0 + timedelta(days=j)
            desc = f"  {_SPECIAL} linha {i}-{j}  "
            val = self.rng.choice([-10.0, 25.0, 0.0, "texto"])
            ws.append([d, desc, val, "sobra"])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def ofx_with_duplicate_fitids(self, n: int) -> bytes:
        """Várias linhas com FITIDs repetidos aleatoriamente."""
        fitid = f"dup-{self.rng.randint(0, 999)}"
        txs = []
        for j in range(n):
            txs.append(
                {
                    "fitid": fitid if self.rng.random() < 0.5 else f"u-{j}",
                    "trnamt": f"-{1 + j}.00",
                    "name": f"Dup {j}",
                    "dtposted": f"202406{j+1:02d}120000",
                }
            )
        return build_ofx_bytes(txs)
