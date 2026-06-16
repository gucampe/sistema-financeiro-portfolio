from __future__ import annotations

from datetime import datetime

from contas.models import Conta
from contas.views import _contas_queryset_com_saldo
from relatorios.export.base import ExportColumn, ExportContext, ExportDataset
def build_investimentos_dataset(ctx: ExportContext) -> ExportDataset:
  qs = _contas_queryset_com_saldo(ctx.usuario).filter(tipo="investimento")

  colunas = [
    ExportColumn("nome", "Conta investimento"),
    ExportColumn("saldo_atual", "Saldo", formatter=str),
    ExportColumn("ativa", "Ativa", formatter=lambda v: "Sim" if v else "Não"),
  ]

  rows = []
  for conta in qs:
    rows.append({
      "nome": conta.nome,
      "saldo_atual": conta.saldo_atual,
      "ativa": conta.ativa,
    })

  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  return ExportDataset(
    titulo="Investimentos",
    colunas=colunas,
    linhas=rows,
    metadados={"nome_arquivo": f"granago_investimentos_{ts}", "dominio": "investimentos"},
  )


def count_investimentos_linhas(ctx: ExportContext) -> int:
  return Conta.objects.filter(usuario=ctx.usuario, tipo="investimento").count()
