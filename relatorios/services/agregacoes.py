from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Case, Count, DecimalField, F, Q, QuerySet, Sum, When

from contas.models import Conta
from relatorios.services.filtros import RelatorioFiltros
from transacoes.models import Transacao


def _as_date(val) -> date:
    if val is None:
        raise ValueError("data nula")
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if hasattr(val, "date"):
        return val.date()
    raise TypeError(val)


def aplicar_filtros_relatorio(qs: QuerySet[Transacao], filtros: RelatorioFiltros) -> QuerySet[Transacao]:
    modo = getattr(filtros, "modo_data", "fluxo") or "fluxo"
    if modo == "competencia_cartao":
        qs = qs.filter(
            Q(
                cartao__isnull=False,
                data_competencia__gte=filtros.data_inicio,
                data_competencia__lte=filtros.data_fim,
            )
            | Q(
                cartao__isnull=False,
                data_competencia__isnull=True,
                data__gte=filtros.data_inicio,
                data__lte=filtros.data_fim,
            )
            | Q(
                cartao__isnull=True,
                data__gte=filtros.data_inicio,
                data__lte=filtros.data_fim,
            )
        )
    else:
        qs = qs.filter(data__gte=filtros.data_inicio, data__lte=filtros.data_fim)
    if filtros.conta_ids:
        qs = qs.filter(conta_id__in=filtros.conta_ids)
    if filtros.categoria_ids:
        qs = qs.filter(categoria_id__in=filtros.categoria_ids)
    if filtros.tipos:
        qs = qs.filter(tipo__in=filtros.tipos)
    meio = getattr(filtros, "meio_pagamento", "todos") or "todos"
    if meio == "debito":
        qs = qs.filter(cartao__isnull=True)
    elif meio == "credito":
        qs = qs.filter(cartao__isnull=False)
    return qs


def totais_por_tipo(qs: QuerySet[Transacao]) -> dict[str, Decimal]:
    agg = qs.aggregate(
        receitas=Sum("valor", filter=Q(tipo="receita")),
        despesas=Sum("valor", filter=Q(tipo="despesa")),
        ajustes=Sum("valor", filter=Q(tipo="ajuste")),
    )
    return {
        "receitas": agg["receitas"] or Decimal("0"),
        "despesas": agg["despesas"] or Decimal("0"),
        "ajustes": agg["ajustes"] or Decimal("0"),
    }


def resultado_fluxo(totais: dict[str, Decimal]) -> Decimal:
    """Receitas − despesas (ajustes ficam de fora do 'resultado' principal)."""
    return totais["receitas"] - totais["despesas"]


def contagem_por_tipo(qs: QuerySet[Transacao]) -> dict[str, int]:
    rows = qs.values("tipo").annotate(n=Count("id"))
    out = {"receita": 0, "despesa": 0, "ajuste": 0}
    for row in rows:
        out[row["tipo"]] = row["n"]
    return out


def top_categorias(
    qs: QuerySet[Transacao],
    tipo: str,
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows = (
        qs.filter(tipo=tipo)
        .values("categoria_id", "categoria__nome", "categoria__cor", "categoria__icone")
        .annotate(total=Sum("valor"))
        .order_by("-total")[:limit]
    )
    total_tipo = qs.filter(tipo=tipo).aggregate(s=Sum("valor"))["s"] or Decimal("0")
    out: list[dict[str, Any]] = []
    for row in rows:
        t = row["total"] or Decimal("0")
        pct = (t / total_tipo * 100) if total_tipo else Decimal("0")
        out.append(
            {
                "categoria_id": row["categoria_id"],
                "nome": row["categoria__nome"],
                "cor": row["categoria__cor"],
                "icone": row["categoria__icone"],
                "total": t,
                "percentual": pct,
            }
        )
    return out


def _granularidade_auto(filtros: RelatorioFiltros) -> str:
    span = (filtros.data_fim - filtros.data_inicio).days + 1
    if span <= 45:
        return "day"
    if span <= 120:
        return "week"
    return "month"


def _meses_no_intervalo(fi: date, ff: date):
    y, m = fi.year, fi.month
    while date(y, m, 1) <= ff:
        yield y, m
        if m == 12:
            m = 1
            y += 1
        else:
            m += 1


def _float_json_seguro(x: Decimal | float | int | None) -> float:
    """Evita NaN/inf no JSON (Chart.js / navegadores rejeitam)."""
    if x is None:
        return 0.0
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    if v != v or v in (float("inf"), float("-inf")):
        return 0.0
    return v


def _inicio_semana_segunda(d: date) -> date:
    """Segunda-feira da semana ISO (igual ao loop semanal já usado nos relatórios)."""
    return d - timedelta(days=d.weekday())


def serie_receitas_despesas(
    qs: QuerySet[Transacao],
    filtros: RelatorioFiltros,
    granularidade: str | None = None,
) -> dict[str, Any]:
    """
    Agrega por dia na base (campo DateField `data`) e agrupa em dia/semana/mês em Python.
    Evita TruncDate/TruncWeek em SQLite com USE_TZ, que dispara UDFs que podem falhar
    com a mensagem \"user-defined function raised exception\".
    """
    g = granularidade or _granularidade_auto(filtros)
    if g == "day":
        fmt = "%d/%m"
    elif g == "week":
        fmt = "%d/%m"
    else:
        fmt = "%b/%y"

    buckets: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {"receita": Decimal("0"), "despesa": Decimal("0"), "ajuste": Decimal("0")}
    )

    daily = qs.values("data", "tipo").annotate(total=Sum("valor"))
    for row in daily.iterator(chunk_size=2000):
        raw_d = row.get("data")
        try:
            d_dia = raw_d if isinstance(raw_d, date) else _as_date(raw_d)
        except (TypeError, ValueError):
            continue
        tipo = row.get("tipo")
        if tipo not in ("receita", "despesa", "ajuste"):
            continue
        total = row["total"] or Decimal("0")
        if g == "month":
            b = date(d_dia.year, d_dia.month, 1)
        elif g == "week":
            b = _inicio_semana_segunda(d_dia)
        else:
            b = d_dia
        buckets[b][tipo] += total

    labels: list[str] = []
    receitas: list[float] = []
    despesas: list[float] = []
    ajustes: list[float] = []

    def push(d: date, data: dict[str, Decimal]):
        labels.append(d.strftime(fmt))
        receitas.append(_float_json_seguro(data["receita"]))
        despesas.append(_float_json_seguro(data["despesa"]))
        ajustes.append(_float_json_seguro(data["ajuste"]))

    if g == "month":
        for y, m in _meses_no_intervalo(filtros.data_inicio, filtros.data_fim):
            key = date(y, m, 1)
            data = buckets.get(key, {"receita": Decimal("0"), "despesa": Decimal("0"), "ajuste": Decimal("0")})
            push(key, data)
    elif g == "week":
        cur = filtros.data_inicio - timedelta(days=filtros.data_inicio.weekday())
        end = filtros.data_fim
        while cur <= end:
            data = buckets.get(cur, {"receita": Decimal("0"), "despesa": Decimal("0"), "ajuste": Decimal("0")})
            push(cur, data)
            cur += timedelta(days=7)
    else:
        cur = filtros.data_inicio
        while cur <= filtros.data_fim:
            data = buckets.get(cur, {"receita": Decimal("0"), "despesa": Decimal("0"), "ajuste": Decimal("0")})
            push(cur, data)
            cur += timedelta(days=1)

    return {
        "labels": labels,
        "receitas": receitas,
        "despesas": despesas,
        "ajustes": ajustes,
        "granularidade": g,
    }


def movimento_por_conta(qs: QuerySet[Transacao], usuario) -> list[dict[str, Any]]:
    expr = Sum(
        Case(
            When(tipo="receita", then=F("valor")),
            When(tipo="despesa", then=-F("valor")),
            When(tipo="ajuste", then=F("valor")),
            default=Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    rows = qs.values("conta_id", "conta__nome").annotate(movimento=expr).order_by("-movimento")
    contas_ativas = {c.id: c for c in Conta.objects.filter(usuario=usuario, ativa=True)}
    out = []
    for row in rows:
        cid = row["conta_id"]
        mov = row["movimento"] or Decimal("0")
        nome = row["conta__nome"]
        c = contas_ativas.get(cid)
        out.append(
            {
                "conta_id": cid,
                "nome": nome,
                "movimento": mov,
                "icone": c.icone if c else "bank",
            }
        )
    return out


def saldos_por_conta_totais(usuario) -> tuple[list[dict[str, Any]], Decimal]:
    """Saldo acumulado (todas as transações) por conta ativa."""
    expr = Sum(
        Case(
            When(transacoes__tipo="receita", then=F("transacoes__valor")),
            When(transacoes__tipo="despesa", then=-F("transacoes__valor")),
            When(transacoes__tipo="ajuste", then=F("transacoes__valor")),
            default=Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    rows = Conta.objects.filter(usuario=usuario, ativa=True).annotate(saldo=expr).order_by("-saldo")
    lista = []
    total = Decimal("0")
    for c in rows:
        s = c.saldo or Decimal("0")
        total += s
        lista.append({"conta_id": c.id, "nome": c.nome, "saldo": s, "icone": c.icone})
    return lista, total


def serie_fluxo_diario(qs: QuerySet[Transacao], filtros: RelatorioFiltros) -> dict[str, Any]:
    """Entradas/saídas por dia, líquido diário e saldo acumulado no período."""
    expr_dia = Sum(
        Case(
            When(tipo="receita", then=F("valor")),
            When(tipo="despesa", then=-F("valor")),
            When(tipo="ajuste", then=F("valor")),
            default=Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    rows = qs.values("data").annotate(liquido=expr_dia).order_by("data")
    by_day: dict[date, Decimal] = {}
    for row in rows.iterator(chunk_size=2000):
        raw_d = row["data"]
        d = raw_d if isinstance(raw_d, date) else _as_date(raw_d)
        by_day[d] = row["liquido"] or Decimal("0")

    by_entrada: dict[date, Decimal] = {}
    by_saida: dict[date, Decimal] = {}
    for row in qs.filter(tipo="receita").values("data").annotate(total=Sum("valor")).iterator(chunk_size=2000):
        d = row["data"] if isinstance(row["data"], date) else _as_date(row["data"])
        by_entrada[d] = row["total"] or Decimal("0")
    for row in qs.filter(tipo="despesa").values("data").annotate(total=Sum("valor")).iterator(chunk_size=2000):
        d = row["data"] if isinstance(row["data"], date) else _as_date(row["data"])
        by_saida[d] = row["total"] or Decimal("0")

    labels: list[str] = []
    liquidos: list[float] = []
    acumulado: list[float] = []
    entradas: list[float] = []
    saidas: list[float] = []
    cur = filtros.data_inicio
    acc = Decimal("0")
    while cur <= filtros.data_fim:
        liq = by_day.get(cur, Decimal("0"))
        acc += liq
        labels.append(cur.strftime("%d/%m"))
        liquidos.append(float(liq))
        acumulado.append(float(acc))
        entradas.append(float(by_entrada.get(cur, Decimal("0"))))
        saidas.append(float(by_saida.get(cur, Decimal("0"))))
        cur += timedelta(days=1)
    return {
        "labels": labels,
        "liquido": liquidos,
        "acumulado": acumulado,
        "entradas": entradas,
        "saidas": saidas,
    }


def resumo_comparativo(
    qs_a: QuerySet[Transacao],
    qs_b: QuerySet[Transacao],
) -> dict[str, Any]:
    ta = totais_por_tipo(qs_a)
    tb = totais_por_tipo(qs_b)
    ra, rb = resultado_fluxo(ta), resultado_fluxo(tb)

    def delta_pct(novo: Decimal, antigo: Decimal) -> Decimal | None:
        if antigo == 0:
            return None
        return (novo - antigo) / abs(antigo) * 100

    return {
        "a": {**ta, "resultado": ra},
        "b": {**tb, "resultado": rb},
        "delta": {
            "receitas": ta["receitas"] - tb["receitas"],
            "despesas": ta["despesas"] - tb["despesas"],
            "resultado": ra - rb,
        },
        "delta_pct": {
            "receitas": delta_pct(ta["receitas"], tb["receitas"]),
            "despesas": delta_pct(ta["despesas"], tb["despesas"]),
            "resultado": delta_pct(ra, rb),
        },
    }


def orcamento_vs_realizado(usuario, filtros: RelatorioFiltros) -> list[dict[str, Any]]:
    from relatorios.services.orcamentos import orcamento_vs_realizado as _orcamento_vs_realizado

    return _orcamento_vs_realizado(usuario, filtros)
