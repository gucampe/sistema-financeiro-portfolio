from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from contas.models import Conta
from contas.views import _contas_queryset_com_saldo
from relatorios.export.base import ExportColumn, ExportContext, ExportDataset


def build_contas_dataset(ctx: ExportContext) -> ExportDataset:
  qs = _contas_queryset_com_saldo(ctx.usuario)
  tipo_labels = dict(Conta.TIPO_CHOICES)

  colunas = [
    ExportColumn("nome", "Nome"),
    ExportColumn("tipo", "Tipo"),
    ExportColumn("saldo_atual", "Saldo atual", formatter=str),
    ExportColumn("ativa", "Ativa", formatter=lambda v: "Sim" if v else "Não"),
    ExportColumn("criada_em", "Criada em"),
  ]

  rows = []
  for conta in qs:
    rows.append({
      "nome": conta.nome,
      "tipo": tipo_labels.get(conta.tipo, conta.tipo),
      "saldo_atual": conta.saldo_atual,
      "ativa": conta.ativa,
      "criada_em": conta.criada_em.strftime("%Y-%m-%d %H:%M") if conta.criada_em else "",
    })

  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  return ExportDataset(
    titulo="Contas",
    colunas=colunas,
    linhas=rows,
    metadados={"nome_arquivo": f"granago_contas_{ts}", "dominio": "contas"},
  )


def count_contas_linhas(ctx: ExportContext) -> int:
  return Conta.objects.filter(usuario=ctx.usuario).count()
