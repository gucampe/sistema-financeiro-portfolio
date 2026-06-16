from __future__ import annotations

import csv
import io
from typing import Any

from relatorios.export.base import ExportColumn, ExportDataset, ExportResult


def write_csv_dataset(dataset: ExportDataset) -> ExportResult:
  buf = io.StringIO()
  writer = csv.writer(buf)
  colunas = dataset.colunas
  writer.writerow([c.label for c in colunas])
  linhas_count = 0
  for row in dataset.linhas:
    writer.writerow([_format_cell(c, row.get(c.key)) for c in colunas])
    linhas_count += 1
  content = buf.getvalue().encode("utf-8-sig")
  nome = dataset.metadados.get("nome_arquivo", "export.csv")
  return ExportResult(
    content=content,
    nome_arquivo=nome if nome.endswith(".csv") else f"{nome}.csv",
    linhas_count=linhas_count,
    tamanho_bytes=len(content),
    content_type="text/csv; charset=utf-8",
  )


def _format_cell(col: ExportColumn, value: Any) -> Any:
  if col.formatter and value is not None:
    return col.formatter(value)
  if value is None:
    return ""
  return value
