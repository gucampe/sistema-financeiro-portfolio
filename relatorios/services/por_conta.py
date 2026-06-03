"""
Análise patrimonial por conta — hero, alocação, movimentação e insights.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Case, Count, DecimalField, F, Q, Sum, When

from contas.models import Conta
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import aplicar_filtros_relatorio, saldos_por_conta_totais
from relatorios.services.despesas_categoria import filtros_periodo_anterior
from relatorios.services.filtros import RelatorioFiltros

TIPO_CORES: dict[str, str] = {
    "corrente": "#6366f1",
    "poupanca": "#14b8a6",
    "carteira": "#f59e0b",
    "investimento": "#8b5cf6",
}


def _delta_pct(atual: Decimal, anterior: Decimal) -> Decimal | None:
    if anterior == 0:
        return None
    return (atual - anterior) / abs(anterior) * 100


def _direcao_variacao(atual: Decimal, anterior: Decimal) -> str:
    if anterior == 0:
        return "novo" if atual != 0 else "sem_base"
    if atual > anterior:
        return "up"
    if atual < anterior:
        return "down"
    return "flat"


def _stats_periodo_por_conta(qs) -> dict[int, dict[str, Any]]:
    expr_mov = Sum(
        Case(
            When(tipo="receita", then=F("valor")),
            When(tipo="despesa", then=-F("valor")),
            When(tipo="ajuste", then=F("valor")),
            default=Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    rows = (
        qs.values("conta_id")
        .annotate(
            movimento=expr_mov,
            receitas=Sum("valor", filter=Q(tipo="receita")),
            despesas=Sum("valor", filter=Q(tipo="despesa")),
            ajustes=Sum("valor", filter=Q(tipo="ajuste")),
            quantidade=Count("id"),
        )
    )
    out: dict[int, dict[str, Any]] = {}
    for row in rows:
        cid = row["conta_id"]
        if cid is None:
            continue
        out[cid] = {
            "movimento": row["movimento"] or Decimal("0"),
            "receitas": row["receitas"] or Decimal("0"),
            "despesas": row["despesas"] or Decimal("0"),
            "ajustes": row["ajustes"] or Decimal("0"),
            "quantidade": row["quantidade"] or 0,
        }
    return out


def _tendencia_diaria_conta(qs, filtros: RelatorioFiltros, conta_id: int) -> dict[str, Any]:
    expr = Sum(
        Case(
            When(tipo="receita", then=F("valor")),
            When(tipo="despesa", then=-F("valor")),
            When(tipo="ajuste", then=F("valor")),
            default=Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    by_day: dict[date, Decimal] = {}
    rows = (
        qs.filter(conta_id=conta_id)
        .values("data")
        .annotate(liquido=expr)
        .order_by("data")
    )
    for row in rows:
        d = row["data"]
        if hasattr(d, "date"):
            d = d.date()
        by_day[d] = row["liquido"] or Decimal("0")

    labels: list[str] = []
    valores: list[float] = []
    cur = filtros.data_inicio
    while cur <= filtros.data_fim:
        labels.append(cur.strftime("%d/%m"))
        valores.append(float(by_day.get(cur, Decimal("0"))))
        cur += timedelta(days=1)
    max_valor = max((abs(v) for v in valores), default=0.0)
    escala = max_valor if max_valor > 0 else 1.0
    barras_pct = [int(round(abs(v) / escala * 100)) for v in valores]
    return {"labels": labels, "valores": valores, "max_valor": escala, "barras_pct": barras_pct}


def _detalhe_conta(qs, filtros: RelatorioFiltros, conta_id: int) -> dict[str, Any]:
    qs_conta = qs.filter(conta_id=conta_id)

    recentes = list(
        qs_conta.select_related("categoria")
        .order_by("-data", "-id")[:5]
        .values("descricao", "valor", "data", "tipo", "categoria__nome")
    )
    transacoes = [
        {
            "descricao": t["descricao"],
            "valor": t["valor"],
            "data": t["data"],
            "tipo": t["tipo"],
            "categoria": t["categoria__nome"] or "—",
        }
        for t in recentes
    ]

    maiores = list(
        qs_conta.order_by("-valor", "-data")[:5].values("descricao", "valor", "data", "tipo", "categoria__nome")
    )
    maiores_movimentacoes = [
        {
            "descricao": t["descricao"],
            "valor": t["valor"],
            "data": t["data"],
            "tipo": t["tipo"],
            "categoria": t["categoria__nome"] or "—",
        }
        for t in maiores
    ]

    cat_rows = (
        qs_conta.filter(tipo="despesa")
        .values("categoria__nome")
        .annotate(total=Sum("valor"), n=Count("id"))
        .order_by("-total")[:5]
    )
    total_desp = qs_conta.filter(tipo="despesa").aggregate(s=Sum("valor"))["s"] or Decimal("0")
    categorias = []
    for row in cat_rows:
        t = row["total"] or Decimal("0")
        pct = (t / total_desp * 100) if total_desp else Decimal("0")
        categorias.append(
            {
                "nome": row["categoria__nome"] or "Sem categoria",
                "total": t,
                "percentual": pct,
                "quantidade": row["n"],
            }
        )

    n_ajustes = qs_conta.filter(tipo="ajuste").count()

    return {
        "transacoes": transacoes,
        "maiores_movimentacoes": maiores_movimentacoes,
        "categorias": categorias,
        "n_ajustes": n_ajustes,
        "tendencia": _tendencia_diaria_conta(qs, filtros, conta_id),
    }


def _insight_items(
    contas: list[dict[str, Any]],
    *,
    patrimonio_total: Decimal,
    movimento_total: Decimal,
    rotulo_periodo_anterior: str,
) -> list[dict[str, str]]:
    itens: list[dict[str, str]] = []
    if not contas:
        return [
            {
                "nivel": "info",
                "titulo": "Sem contas ativas",
                "mensagem": "Cadastre uma conta para acompanhar onde está seu patrimônio.",
            }
        ]

    com_saldo = [c for c in contas if c["saldo"] != 0]
    if not com_saldo and patrimonio_total == 0:
        return [
            {
                "nivel": "info",
                "titulo": "Patrimônio zerado",
                "mensagem": "Suas contas ainda não registram saldo acumulado. Lance receitas ou ajustes para começar.",
            }
        ]

    maior = max(contas, key=lambda c: c["saldo"])
    if patrimonio_total > 0 and maior["percentual_patrimonio"] >= 40:
        itens.append(
            {
                "nivel": "destaque",
                "titulo": "Concentração patrimonial",
                "mensagem": f"“{maior['nome']}” concentra {maior['percentual_patrimonio']:.0f}% do seu saldo total.",
            }
        )

    com_mov = [c for c in contas if c["quantidade_transacoes"] > 0]
    if com_mov:
        mais_mov = max(com_mov, key=lambda c: c["quantidade_transacoes"])
        if mais_mov["percentual_movimentacao"] >= 30:
            itens.append(
                {
                    "nivel": "info",
                    "titulo": "Conta mais utilizada",
                    "mensagem": f"“{mais_mov['nome']}” concentrou {mais_mov['percentual_movimentacao']:.0f}% das movimentações do período.",
                }
            )

    entradas = [c for c in contas if c["receitas"] > 0]
    if entradas:
        top_ent = max(entradas, key=lambda c: c["receitas"])
        pct_ent = (top_ent["receitas"] / sum(c["receitas"] for c in entradas) * 100) if entradas else Decimal("0")
        if pct_ent >= 50:
            itens.append(
                {
                    "nivel": "info",
                    "titulo": "Entradas concentradas",
                    "mensagem": f"“{top_ent['nome']}” recebeu {pct_ent:.0f}% das entradas no período.",
                }
            )

    crescimentos = [c for c in contas if c["movimento"] > 0 and c["quantidade_transacoes"] > 0]
    if crescimentos:
        top_c = max(crescimentos, key=lambda c: c["movimento"])
        itens.append(
            {
                "nivel": "info",
                "titulo": "Saldo em expansão",
                "mensagem": f"“{top_c['nome']}” teve variação líquida positiva no período.",
            }
        )

    baixa_ativ = [c for c in contas if c["tipo"] == "investimento" and c["quantidade_transacoes"] <= 1]
    if baixa_ativ:
        c = baixa_ativ[0]
        itens.append(
            {
                "nivel": "info",
                "titulo": "Conta parada",
                "mensagem": f"“{c['nome']}” teve pouca movimentação — patrimônio estável ou ocioso.",
            }
        )

    ajustes_total = sum(c.get("n_ajustes_periodo", 0) for c in contas)
    if ajustes_total >= 2:
        itens.append(
            {
                "nivel": "aviso",
                "titulo": "Transferências e ajustes",
                "mensagem": "Houve ajustes entre contas no período — confira se o fluxo entre elas está coerente.",
            }
        )

    quedas = [c for c in contas if c.get("delta_pct") is not None and c["direcao"] == "down" and c["delta_pct"] <= -20]
    if quedas:
        c = min(quedas, key=lambda x: x["delta_pct"])
        itens.append(
            {
                "nivel": "aviso",
                "titulo": "Movimento em queda",
                "mensagem": f"“{c['nome']}” reduziu o ritmo de movimentação vs {rotulo_periodo_anterior}.",
            }
        )

    if len(itens) < 2 and len(contas) >= 2:
        segundo = sorted(contas, key=lambda c: c["saldo"], reverse=True)[1]
        itens.append(
            {
                "nivel": "info",
                "titulo": "Segunda maior reserva",
                "mensagem": f"“{segundo['nome']}” responde por {segundo['percentual_patrimonio']:.0f}% do patrimônio.",
            }
        )

    if not itens:
        itens.append(
            {
                "nivel": "info",
                "titulo": "Patrimônio distribuído",
                "mensagem": "Seu saldo está espalhado entre as contas sem concentração extrema.",
            }
        )

    return itens[:5]


@dataclass(frozen=True)
class HeroPorConta:
    maior_saldo_nome: str
    maior_saldo_valor: Decimal
    maior_saldo_pct: Decimal
    mais_movimentada_nome: str | None
    mais_movimentada_pct: Decimal | None
    patrimonio_total: Decimal
    movimento_total: Decimal
    delta_movimento_pct: Decimal | None
    rotulo_periodo_anterior: str


def montar_analise_por_conta(
    usuario,
    filtros: RelatorioFiltros,
    *,
    limite_grafico: int = 8,
    limite_lista: int = 20,
) -> dict[str, Any]:
    """Payload completo para a tela Por conta."""
    qs = aplicar_filtros_relatorio(transacoes_base_qs(usuario), filtros)
    filtros_ant = filtros_periodo_anterior(filtros)
    qs_ant = aplicar_filtros_relatorio(transacoes_base_qs(usuario), filtros_ant)

    stats = _stats_periodo_por_conta(qs)
    stats_ant = _stats_periodo_por_conta(qs_ant)
    saldos_lista, patrimonio_total = saldos_por_conta_totais(usuario)

    contas_map = {c.id: c for c in Conta.objects.filter(usuario=usuario, ativa=True)}
    total_tx = sum(s["quantidade"] for s in stats.values()) or 1

    contas: list[dict[str, Any]] = []
    for saldo_row in saldos_lista:
        cid = saldo_row["conta_id"]
        conta = contas_map.get(cid)
        st = stats.get(cid, {})
        st_ant = stats_ant.get(cid, {})
        saldo = saldo_row["saldo"]
        mov = st.get("movimento", Decimal("0"))
        mov_ant = st_ant.get("movimento", Decimal("0"))
        n_tx = st.get("quantidade", 0)
        pct_pat = (saldo / patrimonio_total * 100) if patrimonio_total else Decimal("0")
        pct_mov = (Decimal(n_tx) / Decimal(total_tx) * 100) if total_tx else Decimal("0")
        delta_pct = _delta_pct(mov, mov_ant)
        n_ajustes = qs.filter(conta_id=cid, tipo="ajuste").count() if n_tx else 0

        contas.append(
            {
                "conta_id": cid,
                "nome": saldo_row["nome"],
                "icone": saldo_row["icone"],
                "tipo": conta.tipo if conta else "corrente",
                "tipo_label": conta.get_tipo_display() if conta else "Corrente",
                "cor": TIPO_CORES.get(conta.tipo if conta else "corrente", "#94a3b8"),
                "saldo": saldo,
                "percentual_patrimonio": pct_pat,
                "movimento": mov,
                "receitas": st.get("receitas", Decimal("0")),
                "despesas": st.get("despesas", Decimal("0")),
                "ajustes": st.get("ajustes", Decimal("0")),
                "quantidade_transacoes": n_tx,
                "percentual_movimentacao": pct_mov,
                "movimento_anterior": mov_ant,
                "delta_valor": mov - mov_ant,
                "delta_pct": delta_pct,
                "delta_pct_abs": abs(float(delta_pct)) if delta_pct is not None else None,
                "direcao": _direcao_variacao(mov, mov_ant),
                "n_ajustes_periodo": n_ajustes,
                "drill_qs": filtros.to_drill_transacoes_periodo_e_conta(cid),
                "detalhe": _detalhe_conta(qs, filtros, cid) if n_tx else _detalhe_conta_vazio(),
            }
        )

    # Contas com movimento no período mas fora da lista de saldos (conta inativa no saldo? shouldn't happen)
    for cid, st in stats.items():
        if any(c["conta_id"] == cid for c in contas):
            continue
        conta = contas_map.get(cid)
        if not conta:
            continue
        n_tx = st.get("quantidade", 0)
        mov = st.get("movimento", Decimal("0"))
        mov_ant = stats_ant.get(cid, {}).get("movimento", Decimal("0"))
        contas.append(
            {
                "conta_id": cid,
                "nome": conta.nome,
                "icone": conta.icone,
                "tipo": conta.tipo,
                "tipo_label": conta.get_tipo_display(),
                "cor": TIPO_CORES.get(conta.tipo, "#94a3b8"),
                "saldo": Decimal("0"),
                "percentual_patrimonio": Decimal("0"),
                "movimento": mov,
                "receitas": st.get("receitas", Decimal("0")),
                "despesas": st.get("despesas", Decimal("0")),
                "ajustes": st.get("ajustes", Decimal("0")),
                "quantidade_transacoes": n_tx,
                "percentual_movimentacao": (Decimal(n_tx) / Decimal(total_tx) * 100) if total_tx else Decimal("0"),
                "movimento_anterior": mov_ant,
                "delta_valor": mov - mov_ant,
                "delta_pct": _delta_pct(mov, mov_ant),
                "delta_pct_abs": None,
                "direcao": _direcao_variacao(mov, mov_ant),
                "n_ajustes_periodo": qs.filter(conta_id=cid, tipo="ajuste").count(),
                "drill_qs": filtros.to_drill_transacoes_periodo_e_conta(cid),
                "detalhe": _detalhe_conta(qs, filtros, cid),
            }
        )

    contas.sort(key=lambda c: c["saldo"], reverse=True)

    movimento_total = sum(c["movimento"] for c in contas)
    movimento_total_ant = sum(st.get("movimento", Decimal("0")) for st in stats_ant.values())

    maior_saldo = contas[0] if contas else None
    com_mov = [c for c in contas if c["quantidade_transacoes"] > 0]
    mais_mov = max(com_mov, key=lambda c: c["quantidade_transacoes"]) if com_mov else None

    rotulo_ant = f"{filtros_ant.data_inicio.strftime('%d/%m')} — {filtros_ant.data_fim.strftime('%d/%m')}"

    hero = HeroPorConta(
        maior_saldo_nome=maior_saldo["nome"] if maior_saldo else "—",
        maior_saldo_valor=maior_saldo["saldo"] if maior_saldo else Decimal("0"),
        maior_saldo_pct=maior_saldo["percentual_patrimonio"] if maior_saldo else Decimal("0"),
        mais_movimentada_nome=mais_mov["nome"] if mais_mov else None,
        mais_movimentada_pct=mais_mov["percentual_movimentacao"] if mais_mov else None,
        patrimonio_total=patrimonio_total,
        movimento_total=movimento_total,
        delta_movimento_pct=_delta_pct(movimento_total, movimento_total_ant),
        rotulo_periodo_anterior=rotulo_ant,
    )

    grafico = [c for c in contas if c["saldo"] > 0][:limite_grafico]
    if not grafico:
        grafico = contas[:limite_grafico]

    insights = _insight_items(
        contas,
        patrimonio_total=patrimonio_total,
        movimento_total=movimento_total,
        rotulo_periodo_anterior=rotulo_ant,
    )

    return {
        "hero": hero,
        "contas": contas[:limite_lista],
        "grafico": grafico,
        "insights": insights,
        "patrimonio_total": patrimonio_total,
        "movimento_total": movimento_total,
        "tem_dados": bool(contas),
        "tem_patrimonio": patrimonio_total != 0 or any(c["quantidade_transacoes"] > 0 for c in contas),
    }


def _detalhe_conta_vazio() -> dict[str, Any]:
    return {
        "transacoes": [],
        "maiores_movimentacoes": [],
        "categorias": [],
        "n_ajustes": 0,
        "tendencia": {"labels": [], "valores": [], "max_valor": 1.0, "barras_pct": []},
    }
