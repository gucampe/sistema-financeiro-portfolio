from __future__ import annotations

import logging
from typing import Callable

from relatorios.export.base import ExportContext, ExportDataset, ExportResult
from relatorios.export.domains import (
  cartoes,
  contas,
  investimentos,
  orcamentos,
  relatorio_pdf,
  titular,
  transacoes,
)
from relatorios.export.writers.csv_writer import write_csv_dataset
from relatorios.export.writers.xlsx_writer import write_xlsx_dataset
from relatorios.models import ExportJob

logger = logging.getLogger(__name__)

DatasetBuilder = Callable[[ExportContext], ExportDataset]
CountFn = Callable[[ExportContext], int]
PdfBuilder = Callable[[ExportContext], ExportResult]

_DATASET_BUILDERS: dict[str, DatasetBuilder] = {
  ExportJob.DOMINIO_TRANSACOES: transacoes.build_transacoes_dataset,
  ExportJob.DOMINIO_CONTAS: contas.build_contas_dataset,
  ExportJob.DOMINIO_ORCAMENTOS: orcamentos.build_orcamentos_dataset,
  ExportJob.DOMINIO_CARTOES: cartoes.build_cartoes_dataset,
  ExportJob.DOMINIO_INVESTIMENTOS: investimentos.build_investimentos_dataset,
}

_COUNT_FNS: dict[str, CountFn] = {
  ExportJob.DOMINIO_TRANSACOES: transacoes.count_transacoes_linhas,
  ExportJob.DOMINIO_CONTAS: contas.count_contas_linhas,
  ExportJob.DOMINIO_ORCAMENTOS: orcamentos.count_orcamentos_linhas,
  ExportJob.DOMINIO_CARTOES: cartoes.count_cartoes_linhas,
  ExportJob.DOMINIO_INVESTIMENTOS: investimentos.count_investimentos_linhas,
  ExportJob.DOMINIO_TITULAR_LGPD: titular.count_lgpd_linhas,
}


def estimate_linhas(ctx: ExportContext) -> int:
  fn = _COUNT_FNS.get(ctx.dominio)
  if not fn:
    return 0
  return fn(ctx)


def run_export(ctx: ExportContext) -> ExportResult:
  if ctx.dominio == ExportJob.DOMINIO_TITULAR_LGPD and ctx.formato == ExportJob.FORMATO_ZIP:
    return titular.build_lgpd_pacote(ctx)

  if ctx.formato == ExportJob.FORMATO_PDF or ctx.dominio == ExportJob.DOMINIO_RELATORIO_PDF:
    return relatorio_pdf.build_relatorio_pdf(ctx)

  builder = _DATASET_BUILDERS.get(ctx.dominio)
  if not builder:
    raise ValueError(f"Domínio de exportação não suportado: {ctx.dominio}")

  dataset = builder(ctx)
  if ctx.formato == ExportJob.FORMATO_CSV:
    return write_csv_dataset(dataset)
  if ctx.formato == ExportJob.FORMATO_XLSX:
    return write_xlsx_dataset(dataset)
  raise ValueError(f"Formato não suportado: {ctx.formato}")
