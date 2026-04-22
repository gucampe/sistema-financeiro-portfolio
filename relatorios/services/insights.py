"""
Regras heurísticas sobre agregados já calculados (sem queries extras pesadas).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any

from relatorios.services.agregacoes import aplicar_filtros_relatorio, resultado_fluxo, totais_por_tipo
from relatorios.services.filtros import RelatorioFiltros
from relatorios.selectors import transacoes_base_qs


@dataclass(frozen=True)
class InsightItem:
    nivel: str  # info, aviso, destaque
    titulo: str
    mensagem: str

    def as_dict(self) -> dict[str, str]:
        return {"nivel": self.nivel, "titulo": self.titulo, "mensagem": self.mensagem}


def gerar_insights_dashboard(
    usuario,
    filtros: RelatorioFiltros,
    *,
    totais_atual: dict[str, Decimal],
    top_despesa: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Lista curta de insights para a home."""
    itens: list[InsightItem] = []

    res = resultado_fluxo(totais_atual)
    if res < 0:
        itens.append(
            InsightItem(
                "aviso",
                "Resultado negativo",
                "No período selecionado, despesas superaram receitas. Revise as maiores categorias de gasto.",
            )
        )
    elif res > 0 and totais_atual["receitas"] > 0:
        pct = (res / totais_atual["receitas"]) * 100
        itens.append(
            InsightItem(
                "info",
                "Taxa de poupança",
                f"Cerca de {pct:.0f}% das receitas ficaram após despesas no período.",
            )
        )

    if top_despesa:
        maior = top_despesa[0]
        total_d = totais_atual["despesas"]
        if total_d > 0:
            p = (maior["total"] / total_d) * 100
            if p >= Decimal("35"):
                itens.append(
                    InsightItem(
                        "destaque",
                        "Concentração de gastos",
                        f"A categoria “{maior['nome']}” responde por cerca de {p:.0f}% das despesas do período.",
                    )
                )

    # Comparativo simples com período imediatamente anterior de mesma duração
    span = (filtros.data_fim - filtros.data_inicio).days + 1
    fim_ant = filtros.data_inicio - timedelta(days=1)
    ini_ant = fim_ant - timedelta(days=span - 1)
    ant = RelatorioFiltros(
        data_inicio=ini_ant,
        data_fim=fim_ant,
        conta_ids=filtros.conta_ids,
        categoria_ids=filtros.categoria_ids,
        tipos=filtros.tipos,
        preset="custom",
    )
    qs_ant = aplicar_filtros_relatorio(transacoes_base_qs(usuario), ant)
    t_ant = totais_por_tipo(qs_ant)
    if t_ant["despesas"] > 0 and totais_atual["despesas"] > 0:
        var = (totais_atual["despesas"] - t_ant["despesas"]) / t_ant["despesas"] * 100
        if var >= Decimal("15"):
            itens.append(
                InsightItem(
                    "aviso",
                    "Despesas em alta",
                    f"Despesas subiram cerca de {var:.0f}% em relação ao bloco anterior de {span} dias.",
                )
            )
        elif var <= Decimal("-15"):
            itens.append(
                InsightItem(
                    "info",
                    "Despesas em queda",
                    f"Despesas caíram cerca de {abs(var):.0f}% vs. o período anterior equivalente.",
                )
            )

    return [i.as_dict() for i in itens[:5]]


def avaliar_alertas_orcamento(orcamento_linhas: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Alertas quando realizado ultrapassa planejado."""
    out: list[dict[str, str]] = []
    for row in orcamento_linhas:
        pl = row.get("planejado") or Decimal("0")
        pct = row.get("percentual")
        if pl > 0 and pct is not None and pct >= 100:
            out.append(
                {
                    "nivel": "aviso",
                    "titulo": f"Orçamento estourado: {row['nome']}",
                    "mensagem": f"Realizado ({pct:.0f}% do planejado).",
                }
            )
        elif pl > 0 and pct is not None and pct >= 85:
            out.append(
                {
                    "nivel": "info",
                    "titulo": f"Próximo do limite: {row['nome']}",
                    "mensagem": f"Já consumiu cerca de {pct:.0f}% do orçamento planejado.",
                }
            )
    return out[:8]
