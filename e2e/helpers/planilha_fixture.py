"""Gera fixture .xlsx padronizada para E2E."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

from openpyxl import Workbook

from transacoes.tests.helpers.import_fixtures import build_xlsx_bytes
from transacoes.xlsx_parse import PLANILHA_CABECALHOS

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "files"
SAMPLE_XLSX = FIXTURES_DIR / "sample.xlsx"


def build_sample_xlsx_bytes(
    *,
    data: date | None = None,
    descricao: str = "E2E planilha import",
    valor: float = -45.75,
    n_linhas: int = 1,
) -> bytes:
    d = data or date.today()
    if n_linhas <= 1:
        wb = Workbook()
        ws = wb.active
        ws.append(list(PLANILHA_CABECALHOS))
        ws.append([d, descricao, valor])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
    return build_xlsx_bytes(
        n_linhas,
        data_inicio=d,
        descricao=descricao,
        valor=valor,
    )


def ensure_sample_xlsx() -> Path:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    if not SAMPLE_XLSX.exists():
        SAMPLE_XLSX.write_bytes(build_sample_xlsx_bytes())
    return SAMPLE_XLSX
