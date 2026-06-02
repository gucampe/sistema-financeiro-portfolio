"""
Análise de despesas por categoria — hero, comparação temporal e insights.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum

from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import aplicar_filtros_relatorio, top_categorias
from relatorios.services.filtros import RelatorioFiltros


def filtros_periodo_anterior(filtros: RelatorioFiltros) -> RelatorioFiltros:
    """Período imediatamente anterior com a mesma duração (base para comparação)."""
    span = (filtros.data_fim - filtros.data_inicio).days + 1
    fim_ant = filtros.data_inicio - timedelta(days=1)
    ini_ant = fim_ant - timedelta(days=span - 1)
    return RelatorioFiltros(
        data_inicio=ini_ant,
        data_fim=fim_ant,
        conta_ids=filtros.conta_ids,
        categoria_ids=filtros.categoria_ids,
        tipos=filtros.tipos,
        preset="custom",
        meio_pagamento=filtros.meio_pagamento,
        modo_data=filtros.modo_data,
    )


def _totais_por_categoria_id(qs) -> dict[int | None, Decimal]:
    rows = (
        qs.filter(tipo="despesa")
        .values("categoria_id")
        .annotate(total=Sum("valor"))
    )
    return {r["categoria_id"]: r["total"] or Decimal("0") for r in rows}


def _delta_pct(atual: Decimal, anterior: Decimal) -> Decimal | None:
    if anterior == 0:
        return None
    return (atual - anterior) / abs(anterior) * 100


def _direcao_variacao(atual: Decimal, anterior: Decimal) -> str:
    if anterior == 0:
        return "novo" if atual > 0 else "sem_base"
    if atual > anterior:
        return "up"
    if atual < anterior:
        return "down"
    return "flat"


def _tendencia_diaria_categoria(qs, filtros: RelatorioFiltros, categoria_id: int) -> dict[str, Any]:
    by_day: dict[date, Decimal] = {}
    rows = (
        qs.filter(tipo="despesa", categoria_id=categoria_id)
        .values("data")
        .annotate(total=Sum("valor"))
        .order_by("data")
    )
    for row in rows:
        d = row["data"]
        if hasattr(d, "date"):
            d = d.date()
        by_day[d] = row["total"] or Decimal("0")

    labels: list[str] = []
    valores: list[float] = []
    cur = filtros.data_inicio
    while cur <= filtros.data_fim:
        labels.append(cur.strftime("%d/%m"))
        valores.append(float(by_day.get(cur, Decimal("0"))))
        cur += timedelta(days=1)
    max_valor = max(valores) if valores else 0.0
    escala = max_valor if max_valor > 0 else 1.0
    barras_pct = [int(round(v / escala * 100)) for v in valores]
    return {"labels": labels, "valores": valores, "max_valor": escala, "barras_pct": barras_pct}


def _detalhe_categoria(qs, filtros: RelatorioFiltros, categoria_id: int, total: Decimal) -> dict[str, Any]:
    qs_cat = qs.filter(tipo="despesa", categoria_id=categoria_id)

    top_tx = list(
        qs_cat.select_related("conta")
        .order_by("-valor", "-data")[:5]
        .values("descricao", "valor", "data", "conta__nome")
    )
    transacoes = [
        {
            "descricao": t["descricao"],
            "valor": t["valor"],
            "data": t["data"],
            "conta": t["conta__nome"] or "—",
        }
        for t in top_tx
    ]

    contas_rows = (
        qs_cat.values("conta__nome")
        .annotate(total=Sum("valor"), n=Count("id"))
        .order_by("-total")[:5]
    )
    contas = []
    for row in contas_rows:
        t = row["total"] or Decimal("0")
        pct = (t / total * 100) if total else Decimal("0")
        contas.append(
            {
                "nome": row["conta__nome"] or "—",
                "total": t,
                "percentual": pct,
                "quantidade": row["n"],
            }
        )

    return {
        "transacoes": transacoes,
        "contas": contas,
        "tendencia": _tendencia_diaria_categoria(qs, filtros, categoria_id),
    }


def _insight_items(
    categorias: list[dict[str, Any]],
    total_despesas: Decimal,
    *,
    rotulo_periodo_anterior: str,
) -> list[dict[str, str]]:
    itens: list[dict[str, str]] = []
    if not categorias or total_despesas <= 0:
        return [
            {
                "nivel": "info",
                "titulo": "Sem despesas",
                "mensagem": "Não há lançamentos de despesa no período selecionado.",
            }
        ]

    maior = categorias[0]
    pct_maior = maior["percentual"]
    if pct_maior >= 33:
        itens.append(
            {
                "nivel": "destaque",
                "titulo": "Concentração",
                "mensagem": f"“{maior['nome']}” representa mais de um terço das suas despesas ({pct_maior:.0f}%).",
            }
        )

    crescimentos = [
        c
        for c in categorias
        if c.get("delta_pct") is not None and c["delta_pct"] > 15 and c["direcao"] == "up"
    ]
    if crescimentos:
        c = max(crescimentos, key=lambda x: x["delta_pct"])
        itens.append(
            {
                "nivel": "aviso",
                "titulo": "Crescimento acentuado",
                "mensagem": f"“{c['nome']}” aumentou {c['delta_pct']:.0f}% em relação a {rotulo_periodo_anterior}.",
            }
        )

    quedas = [c for c in categorias if c.get("delta_pct") is not None and c["delta_pct"] <= -10 and c["direcao"] == "down"]
    if quedas:
        c = min(quedas, key=lambda x: x["delta_pct"])
        itens.append(
            {
                "nivel": "info",
                "titulo": "Alívio no orçamento",
                "mensagem": f"“{c['nome']}” caiu {abs(c['delta_pct']):.0f}% vs {rotulo_periodo_anterior}.",
            }
        )

    recorrentes = [c for c in categorias if c.get("quantidade_transacoes", 0) >= 4 and c["percentual"] >= 8]
    if recorrentes:
        nomes = ", ".join(f"“{c['nome']}”" for c in recorrentes[:2])
        itens.append(
            {
                "nivel": "info",
                "titulo": "Gastos recorrentes",
                "mensagem": f"{nomes} apresentam vários lançamentos no período — vale revisar assinaturas e hábitos.",
            }
        )

    if len(itens) < 2 and len(categorias) >= 2:
        segundo = categorias[1]
        itens.append(
            {
                "nivel": "info",
                "titulo": "Segundo maior impacto",
                "mensagem": f"“{segundo['nome']}” ficou em segundo lugar com {segundo['percentual']:.0f}% das despesas.",
            }
        )

    return itens[:5]


@dataclass(frozen=True)
class HeroDespesasCategoria:
    maior_gasto_nome: str
    maior_gasto_valor: Decimal
    maior_gasto_pct: Decimal
    maior_crescimento_nome: str | None
    maior_crescimento_pct: Decimal | None
    total_despesas: Decimal
    delta_total_pct: Decimal | None
    rotulo_periodo_anterior: str


def montar_analise_despesas_categoria(
    usuario,
    filtros: RelatorioFiltros,
    *,
    limite_grafico: int = 10,
    limite_lista: int = 25,
) -> dict[str, Any]:
    """
    Payload completo para a tela Por categoria.
    Estruturado para suportar comparações temporais futuras (preset, média, etc.).
    """
    qs = aplicar_filtros_relatorio(transacoes_base_qs(usuario), filtros)
    filtros_ant = filtros_periodo_anterior(filtros)
    qs_ant = aplicar_filtros_relatorio(transacoes_base_qs(usuario), filtros_ant)

    totais_ant_map = _totais_por_categoria_id(qs_ant)
    total_despesas = qs.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal("0")
    total_ant = qs_ant.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal("0")

    base_top = top_categorias(qs, "despesa", limit=limite_lista)

    categorias: list[dict[str, Any]] = []
    for row in base_top:
        cid = row["categoria_id"]
        if cid is None:
            continue
        total = row["total"]
        ant = totais_ant_map.get(cid, Decimal("0"))
        delta_pct = _delta_pct(total, ant)
        direcao = _direcao_variacao(total, ant)
        n_tx = qs.filter(tipo="despesa", categoria_id=cid).count()
        detalhe = _detalhe_categoria(qs, filtros, cid, total)
        categorias.append(
            {
                **row,
                "total_anterior": ant,
                "delta_valor": total - ant,
                "delta_pct": delta_pct,
                "delta_pct_abs": abs(float(delta_pct)) if delta_pct is not None else None,
                "direcao": direcao,
                "quantidade_transacoes": n_tx,
                "detalhe": detalhe,
            }
        )

    maior_crescimento = None
    maior_crescimento_pct = None
    candidatos = [c for c in categorias if c["delta_pct"] is not None and c["direcao"] == "up"]
    if candidatos:
        best = max(candidatos, key=lambda c: c["delta_pct"])
        maior_crescimento = best["nome"]
        maior_crescimento_pct = best["delta_pct"]

    rotulo_ant = f"{filtros_ant.data_inicio.strftime('%d/%m')} — {filtros_ant.data_fim.strftime('%d/%m')}"

    hero = HeroDespesasCategoria(
        maior_gasto_nome=categorias[0]["nome"] if categorias else "—",
        maior_gasto_valor=categorias[0]["total"] if categorias else Decimal("0"),
        maior_gasto_pct=categorias[0]["percentual"] if categorias else Decimal("0"),
        maior_crescimento_nome=maior_crescimento,
        maior_crescimento_pct=maior_crescimento_pct,
        total_despesas=total_despesas,
        delta_total_pct=_delta_pct(total_despesas, total_ant),
        rotulo_periodo_anterior=rotulo_ant,
    )

    grafico = categorias[:limite_grafico]
    insights = _insight_items(categorias, total_despesas, rotulo_periodo_anterior=rotulo_ant)

    return {
        "hero": hero,
        "categorias": categorias,
        "grafico": grafico,
        "insights": insights,
        "filtros_anterior": filtros_ant,
        "total_despesas": total_despesas,
        "tem_dados": bool(categorias),
    }
