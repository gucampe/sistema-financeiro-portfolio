from __future__ import annotations

from datetime import datetime
from typing import Iterator

from relatorios.export.base import ExportColumn, ExportContext, ExportDataset
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import aplicar_filtros_relatorio
from relatorios.services.export.serializers import filtros_from_payload


def build_transacoes_dataset(ctx: ExportContext) -> ExportDataset:
  filtros = filtros_from_payload(ctx.filtros_raw)
  qs = aplicar_filtros_relatorio(transacoes_base_qs(ctx.usuario), filtros).order_by("data", "id")

  colunas = [
    ExportColumn("data", "Data"),
    ExportColumn("tipo", "Tipo"),
    ExportColumn("valor", "Valor", formatter=str),
    ExportColumn("descricao", "Descrição"),
    ExportColumn("conta", "Conta"),
    ExportColumn("categoria", "Categoria"),
    ExportColumn("cartao", "Cartão"),
    ExportColumn("data_competencia", "Data competência"),
  ]

  def iter_rows() -> Iterator[dict]:
    for t in qs.iterator(chunk_size=500):
      if ctx.is_cancelled():
        break
      yield {
        "data": t.data.isoformat(),
        "tipo": t.tipo,
        "valor": t.valor,
        "descricao": t.descricao,
        "conta": t.conta.nome if t.conta_id else "",
        "categoria": t.categoria.nome if t.categoria_id else "",
        "cartao": t.cartao.nome if t.cartao_id else "",
        "data_competencia": t.data_competencia.isoformat() if t.data_competencia else "",
      }

  inicio = ctx.filtros_raw.get("inicio", "")
  fim = ctx.filtros_raw.get("fim", "")
  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  return ExportDataset(
    titulo="Transações",
    colunas=colunas,
    linhas=iter_rows(),
    metadados={
      "periodo_inicio": inicio,
      "periodo_fim": fim,
      "nome_arquivo": f"granago_transacoes_{ts}",
      "dominio": "transacoes",
    },
  )


def count_transacoes_linhas(ctx: ExportContext) -> int:
  filtros = filtros_from_payload(ctx.filtros_raw)
  qs = aplicar_filtros_relatorio(transacoes_base_qs(ctx.usuario), filtros)
  return qs.count()
