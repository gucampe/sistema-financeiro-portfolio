from __future__ import annotations

from datetime import datetime

from cartoes.models import Cartao, Fatura
from cartoes.services.gestao_faturas import total_fatura
from relatorios.export.base import ExportColumn, ExportContext, ExportDataset


def build_cartoes_dataset(ctx: ExportContext) -> ExportDataset:
  cartoes = Cartao.objects.filter(usuario=ctx.usuario, ativa=True).select_related("conta_padrao")
  faturas = (
    Fatura.objects.filter(usuario=ctx.usuario)
    .select_related("cartao")
    .order_by("-competencia", "-id")[:500]
  )

  colunas = [
    ExportColumn("cartao", "Cartão"),
    ExportColumn("competencia", "Competência"),
    ExportColumn("vencimento", "Vencimento"),
    ExportColumn("total_despesas", "Total despesas", formatter=str),
    ExportColumn("status_pagamento", "Status pagamento"),
  ]

  rows = []
  for fatura in faturas:
    total = total_fatura(fatura)
    rows.append({
      "cartao": fatura.cartao.nome,
      "competencia": fatura.competencia.strftime("%Y-%m") if fatura.competencia else "",
      "vencimento": fatura.data_vencimento.isoformat() if fatura.data_vencimento else "",
      "total_despesas": total,
      "status_pagamento": fatura.status_pagamento or "",
    })

  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  return ExportDataset(
    titulo="Cartões e faturas",
    colunas=colunas,
    linhas=rows,
    metadados={
      "cartoes_ativos": cartoes.count(),
      "nome_arquivo": f"granago_cartoes_{ts}",
      "dominio": "cartoes",
    },
  )


def count_cartoes_linhas(ctx: ExportContext) -> int:
  return Fatura.objects.filter(usuario=ctx.usuario).count()
