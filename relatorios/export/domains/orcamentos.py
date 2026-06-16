from __future__ import annotations

from datetime import datetime

from relatorios.export.base import ExportColumn, ExportContext, ExportDataset
from relatorios.services.export.serializers import filtros_from_payload
from relatorios.services.orcamentos import listar_orcamentos


def build_orcamentos_dataset(ctx: ExportContext) -> ExportDataset:
  filtros = filtros_from_payload(ctx.filtros_raw)
  linhas_orc = listar_orcamentos(
    ctx.usuario,
    filtros,
    ano_ref=filtros.data_fim.year,
    mes_ref=filtros.data_fim.month,
    exibir_inativos=True,
  )

  colunas = [
    ExportColumn("categoria", "Categoria"),
    ExportColumn("planejado", "Planejado", formatter=str),
    ExportColumn("realizado", "Realizado", formatter=str),
    ExportColumn("disponivel", "Disponível", formatter=str),
    ExportColumn("percentual", "Percentual"),
    ExportColumn("status", "Status"),
    ExportColumn("ativo", "Ativo", formatter=lambda v: "Sim" if v else "Não"),
  ]

  rows = []
  for linha in linhas_orc:
    rows.append({
      "categoria": linha.nome,
      "planejado": linha.planejado,
      "realizado": linha.realizado,
      "disponivel": linha.disponivel,
      "percentual": f"{linha.percentual:.1f}%" if linha.percentual is not None else "",
      "status": linha.status_label,
      "ativo": linha.ativo,
    })

  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  return ExportDataset(
    titulo="Orçamentos",
    colunas=colunas,
    linhas=rows,
    metadados={
      "periodo_inicio": filtros.data_inicio.isoformat(),
      "periodo_fim": filtros.data_fim.isoformat(),
      "nome_arquivo": f"granago_orcamentos_{ts}",
      "dominio": "orcamentos",
    },
  )


def count_orcamentos_linhas(ctx: ExportContext) -> int:
  filtros = filtros_from_payload(ctx.filtros_raw)
  return len(
    listar_orcamentos(
      ctx.usuario,
      filtros,
      ano_ref=filtros.data_fim.year,
      mes_ref=filtros.data_fim.month,
      exibir_inativos=True,
    )
  )
