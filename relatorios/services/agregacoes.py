from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Case, Count, DecimalField, F, Q, QuerySet, Sum, When
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek

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
    qs = qs.filter(data__gte=filtros.data_inicio, data__lte=filtros.data_fim)
    if filtros.conta_ids:
        qs = qs.filter(conta_id__in=filtros.conta_ids)
    if filtros.categoria_ids:
        qs = qs.filter(categoria_id__in=filtros.categoria_ids)
    if filtros.tipos:
        qs = qs.filter(tipo__in=filtros.tipos)
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


def serie_receitas_despesas(
    qs: QuerySet[Transacao],
    filtros: RelatorioFiltros,
    granularidade: str | None = None,
) -> dict[str, Any]:
    g = granularidade or _granularidade_auto(filtros)
    if g == "day":
        trunc = TruncDate("data")
        fmt = "%d/%m"
    elif g == "week":
        trunc = TruncWeek("data")
        fmt = "%d/%m"
    else:
        trunc = TruncMonth("data")
        fmt = "%b/%y"

    buckets: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {"receita": Decimal("0"), "despesa": Decimal("0"), "ajuste": Decimal("0")}
    )

    annotated = (
        qs.annotate(bucket=trunc).values("bucket", "tipo").annotate(total=Sum("valor")).order_by("bucket")
    )

    for row in annotated:
        b = _as_date(row["bucket"])
        if g == "month":
            b = date(b.year, b.month, 1)
        elif g == "week":
            b = b - timedelta(days=b.weekday())
        tipo = row["tipo"]
        total = row["total"] or Decimal("0")
        buckets[b][tipo] += total

    labels: list[str] = []
    receitas: list[float] = []
    despesas: list[float] = []
    ajustes: list[float] = []

    def push(d: date, data: dict[str, Decimal]):
        labels.append(d.strftime(fmt))
        receitas.append(float(data["receita"]))
        despesas.append(float(data["despesa"]))
        ajustes.append(float(data["ajuste"]))

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
    """Entradas/saídas líquidas por dia + saldo acumulado no período (fluxo)."""
    expr_dia = Sum(
        Case(
            When(tipo="receita", then=F("valor")),
            When(tipo="despesa", then=-F("valor")),
            When(tipo="ajuste", then=F("valor")),
            default=Decimal("0"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
    )
    rows = qs.annotate(d=TruncDate("data")).values("d").annotate(liquido=expr_dia).order_by("d")
    by_day: dict[date, Decimal] = {}
    for row in rows:
        d = _as_date(row["d"])
        by_day[d] = row["liquido"] or Decimal("0")

    labels: list[str] = []
    liquidos: list[float] = []
    acumulado: list[float] = []
    cur = filtros.data_inicio
    acc = Decimal("0")
    while cur <= filtros.data_fim:
        liq = by_day.get(cur, Decimal("0"))
        acc += liq
        labels.append(cur.strftime("%d/%m"))
        liquidos.append(float(liq))
        acumulado.append(float(acc))
        cur += timedelta(days=1)
    return {"labels": labels, "liquido": liquidos, "acumulado": acumulado}


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
    from categorias.models import Categoria
    from relatorios.models import OrcamentoCategoria

    qs = aplicar_filtros_relatorio(
        Transacao.objects.filter(usuario=usuario).select_related("categoria"),
        filtros,
    ).filter(tipo="despesa", categoria__tipo="despesa")

    realizado_rows = (
        qs.values("categoria_id", "categoria__nome", "categoria__cor").annotate(gasto=Sum("valor")).order_by("-gasto")
    )
    real_map: dict[int, dict[str, Any]] = {
        r["categoria_id"]: r for r in realizado_rows if r["categoria_id"] is not None
    }

    planejado_por_cat: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for y, m in _meses_no_intervalo(filtros.data_inicio, filtros.data_fim):
        for o in OrcamentoCategoria.objects.filter(usuario=usuario, ano=y, mes=m).select_related("categoria"):
            planejado_por_cat[o.categoria_id] += o.valor_planejado

    categoria_ids = set(planejado_por_cat) | set(real_map.keys())
    out: list[dict[str, Any]] = []
    for cid in categoria_ids:
        r = real_map.get(cid, {})
        gasto = r.get("gasto") or Decimal("0")
        planejado = planejado_por_cat.get(cid, Decimal("0"))
        nome = r.get("categoria__nome")
        cor = r.get("categoria__cor")
        if nome is None:
            cat = OrcamentoCategoria.objects.filter(usuario=usuario, categoria_id=cid).first()
            if cat:
                nome = cat.categoria.nome
                cor = cat.categoria.cor
            else:
                c = Categoria.objects.filter(pk=cid).first()
                nome = c.nome if c else "?"
                cor = c.cor if c else "#6B7280"
        pct = (gasto / planejado * 100) if planejado else None
        out.append(
            {
                "categoria_id": cid,
                "nome": nome,
                "cor": cor or "#6B7280",
                "planejado": planejado,
                "realizado": gasto,
                "percentual": pct,
            }
        )
    out.sort(key=lambda x: x["realizado"], reverse=True)
    return out
