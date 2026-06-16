from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from relatorios.export.base import ExportContext
from relatorios.export.writers.pdf_writer import write_pdf_from_template
from relatorios.export.base import ExportResult
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import aplicar_filtros_relatorio, resultado_fluxo, top_categorias, totais_por_tipo
from relatorios.services.dashboard import contas_dashboard, resumo_cartoes_dashboard
from relatorios.services.export.serializers import filtros_from_payload
from relatorios.services.por_conta import montar_analise_por_conta


def build_relatorio_pdf(ctx: ExportContext) -> ExportResult:
  filtros = filtros_from_payload(ctx.filtros_raw)
  usuario = ctx.usuario
  qs = aplicar_filtros_relatorio(transacoes_base_qs(usuario), filtros)
  totais_raw = totais_por_tipo(qs)
  totais = {
    "receita": totais_raw["receitas"],
    "despesa": totais_raw["despesas"],
    "ajustes": totais_raw["ajustes"],
    "saldo": resultado_fluxo(totais_raw),
  }
  top_desp = top_categorias(qs, "despesa", limit=5)
  analise_contas = montar_analise_por_conta(usuario, filtros)
  cartoes_data = resumo_cartoes_dashboard(usuario)
  contas_data = contas_dashboard(usuario, limit=8)
  contas_resumo = []
  for item in contas_data.get("contas", []):
    nome = item.get("nome") or item.get("instituicao") or f"Conta #{item.get('conta_id', '')}"
    contas_resumo.append({
      "nome": nome,
      "saldo": item.get("saldo"),
    })

  context = {
    "usuario": usuario,
    "filtros": filtros,
    "totais": totais,
    "top_despesas": top_desp,
    "contas_resumo": contas_resumo,
    "patrimonio_total": contas_data.get("patrimonio_total"),
    "analise_contas": analise_contas.get("contas", [])[:8],
    "cartoes": cartoes_data.get("cartoes", []),
    "gerado_em": timezone.localtime().strftime("%d/%m/%Y %H:%M"),
    "periodo_label": f"{filtros.data_inicio.strftime('%d/%m/%Y')} — {filtros.data_fim.strftime('%d/%m/%Y')}",
  }

  ts = datetime.now().strftime("%Y%m%d_%H%M%S")
  return write_pdf_from_template(
    "relatorios/export/pdf/resumo_financeiro.html",
    context,
    f"granago_resumo_{ts}.pdf",
  )
