"""Camada central de orçamentos por categoria."""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Case, F, Q, QuerySet, Sum, When
from django.db.models.functions import ExtractMonth, ExtractYear

from relatorios.models import OrcamentoCategoria
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import aplicar_filtros_relatorio
from relatorios.services.filtros import RelatorioFiltros
from relatorios.services.request_cache import RelatorioRequestCache
from transacoes.models import Transacao

LIMITE_ATENCAO = 85
LIMITE_ESTOURO = 100

MESES_PT = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


@dataclass
class LinhaOrcamento:
    orcamento_id: int | None
    categoria_id: int
    nome: str
    cor: str
    icone: str
    planejado: Decimal
    realizado: Decimal
    disponivel: Decimal
    percentual: float | None
    status: str
    status_label: str
    percentual_exibicao: float
    ativo: bool = True
    historico: list[dict[str, Any]] = field(default_factory=list)
    orcamento_obj: Any = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "orcamento_id": self.orcamento_id,
            "categoria_id": self.categoria_id,
            "nome": self.nome,
            "cor": self.cor,
            "icone": self.icone,
            "planejado": self.planejado,
            "realizado": self.realizado,
            "disponivel": self.disponivel,
            "percentual": self.percentual,
            "status": self.status,
            "status_label": self.status_label,
            "percentual_exibicao": self.percentual_exibicao,
            "ativo": self.ativo,
        }


def classificar_status(percentual: float | None) -> tuple[str, str]:
    if percentual is None:
        return "ok", "Saudável"
    if percentual >= LIMITE_ESTOURO:
        return "excedido", "Estourado"
    if percentual >= LIMITE_ATENCAO:
        return "risco", "Atenção"
    return "ok", "Saudável"


def montar_linha_orcamento(
    *,
    orcamento_id: int | None,
    categoria_id: int,
    nome: str,
    cor: str,
    icone: str,
    planejado: Decimal,
    realizado: Decimal,
    ativo: bool = True,
) -> LinhaOrcamento:
    disponivel = planejado - realizado
    if planejado > 0:
        percentual = float(realizado / planejado * 100)
    else:
        percentual = None
    status, status_label = classificar_status(percentual)
    pct_exib = min(percentual, 100.0) if percentual is not None else 0.0
    return LinhaOrcamento(
        orcamento_id=orcamento_id,
        categoria_id=categoria_id,
        nome=nome,
        cor=cor or "#6B7280",
        icone=icone or "fa-ellipsis-h",
        planejado=planejado,
        realizado=realizado,
        disponivel=disponivel,
        percentual=percentual,
        status=status,
        status_label=status_label,
        percentual_exibicao=pct_exib,
        ativo=ativo,
    )


def filtros_mes(ano: int, mes: int) -> RelatorioFiltros:
    """Mesmo critério de calendário do histórico: cartão por data_competencia, demais por data."""
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, calendar.monthrange(ano, mes)[1])
    return RelatorioFiltros(
        data_inicio=inicio,
        data_fim=fim,
        preset="custom",
        modo_data="competencia_cartao",
    )


def _filtros_orcamento_despesas(filtros: RelatorioFiltros) -> RelatorioFiltros:
    """Período e dimensões do drawer; despesas sempre em competência de cartão."""
    return RelatorioFiltros(
        data_inicio=filtros.data_inicio,
        data_fim=filtros.data_fim,
        conta_ids=filtros.conta_ids,
        categoria_ids=filtros.categoria_ids,
        tipos=(),
        preset=filtros.preset,
        meio_pagamento=filtros.meio_pagamento,
        modo_data="competencia_cartao",
    )


def periodo_orcamento_multi_mes(filtros: RelatorioFiltros) -> bool:
    return (filtros.data_inicio.year, filtros.data_inicio.month) != (
        filtros.data_fim.year,
        filtros.data_fim.month,
    )


def rotulo_periodo_orcamento(filtros: RelatorioFiltros) -> str:
    if periodo_orcamento_multi_mes(filtros):
        return (
            f"{filtros.data_inicio.strftime('%d/%m/%Y')} – "
            f"{filtros.data_fim.strftime('%d/%m/%Y')}"
        )
    return f"{MESES_PT[filtros.data_inicio.month - 1]} de {filtros.data_inicio.year}"


def referencia_mes_orcamento(filtros: RelatorioFiltros) -> tuple[int, int]:
    """Mês de referência para vigência na UI e histórico (último mês do intervalo)."""
    if not periodo_orcamento_multi_mes(filtros):
        return filtros.data_inicio.year, filtros.data_inicio.month
    return filtros.data_fim.year, filtros.data_fim.month


def queryset_despesas_orcamento(usuario, filtros: RelatorioFiltros) -> QuerySet[Transacao]:
    qs = transacoes_base_qs(usuario).filter(tipo="despesa", categoria__tipo="despesa")
    qs = qs.exclude(pagamento_de_fatura__isnull=False)
    return aplicar_filtros_relatorio(qs, filtros)


def _nome_para_ids_map(usuario, *, cache: RelatorioRequestCache | None = None) -> dict[str, list[int]]:
    """Mapa nome → ids de categorias despesa (1 query, reutilizável no request)."""
    from categorias.models import Categoria

    def _load() -> dict[str, list[int]]:
        out: dict[str, list[int]] = {}
        for pk, nome in Categoria.objects.filter(
            Q(usuario=usuario) | Q(padrao=True),
            tipo="despesa",
        ).values_list("pk", "nome"):
            out.setdefault(nome, []).append(pk)
        return out

    if cache is not None:
        return cache.nome_ids_map(_load)
    return _load()


def _realizado_map_por_nome_categoria(
    usuario,
    por_id: dict[int, Decimal],
    *,
    nome_ids_map: dict[str, list[int]] | None = None,
) -> dict[int, Decimal]:
    """Alinha gastos entre categoria do usuário e global padrão com o mesmo nome."""
    if not por_id:
        return por_id
    from categorias.models import Categoria

    if nome_ids_map is None:
        nome_ids_map = _nome_para_ids_map(usuario)

    por_nome: dict[str, Decimal] = {}
    for cat in Categoria.objects.filter(pk__in=por_id).only("id", "nome"):
        por_nome[cat.nome] = por_nome.get(cat.nome, Decimal("0")) + por_id[cat.id]

    out = dict(por_id)
    for nome, total in por_nome.items():
        for cid in nome_ids_map.get(nome, []):
            out[cid] = total
    return out


def _filtros_orcamento_cache_key(filtros: RelatorioFiltros) -> str:
    return (
        f"{filtros.data_inicio}|{filtros.data_fim}|{filtros.modo_data}|"
        f"{filtros.conta_ids}|{filtros.categoria_ids}|{filtros.tipos}"
    )


def realizado_por_categoria_filtros(
    usuario,
    filtros: RelatorioFiltros,
    *,
    cache: RelatorioRequestCache | None = None,
) -> dict[int, Decimal]:
    fo = _filtros_orcamento_despesas(filtros)
    key = _filtros_orcamento_cache_key(fo)

    def _compute() -> dict[int, Decimal]:
        qs = queryset_despesas_orcamento(usuario, fo)
        rows = qs.values("categoria_id").annotate(gasto=Sum("valor"))
        por_id = {r["categoria_id"]: r["gasto"] or Decimal("0") for r in rows if r["categoria_id"]}
        nome_map = _nome_para_ids_map(usuario, cache=cache)
        return _realizado_map_por_nome_categoria(usuario, por_id, nome_ids_map=nome_map)

    if cache is not None:
        return cache.realizado_por_categoria_filtros(key, _compute)
    return _compute()


def realizado_por_categoria(usuario, ano: int, mes: int) -> dict[int, Decimal]:
    return realizado_por_categoria_filtros(usuario, filtros_mes(ano, mes))


def planejado_mes(usuario, ano: int, mes: int, *, incluir_inativos: bool = False) -> dict[int, OrcamentoCategoria]:
    bulk = planejado_por_mes_bulk(usuario, [(ano, mes)], incluir_inativos=incluir_inativos)
    return bulk.get((ano, mes), {})


def planejado_por_mes_bulk(
    usuario,
    meses: list[tuple[int, int]],
    *,
    incluir_inativos: bool = False,
) -> dict[tuple[int, int], dict[int, OrcamentoCategoria]]:
    """Planejado vigente para vários meses com 1 query de orçamentos."""
    if not meses:
        return {}
    qs = OrcamentoCategoria.objects.filter(usuario=usuario).select_related("categoria")
    if not incluir_inativos:
        qs = qs.filter(ativo=True)
    orcamentos = list(qs)
    out: dict[tuple[int, int], dict[int, OrcamentoCategoria]] = {}
    for ano, mes in meses:
        mes_map: dict[int, OrcamentoCategoria] = {}
        for o in orcamentos:
            if o.vigente_em(ano, mes):
                mes_map[o.categoria_id] = o
        out[(ano, mes)] = mes_map
    return out


def planejado_por_categoria_periodo(
    usuario,
    filtros: RelatorioFiltros,
    *,
    incluir_inativos: bool = False,
    cache: RelatorioRequestCache | None = None,
) -> dict[int, Decimal]:
    from relatorios.services.agregacoes import _meses_no_intervalo

    fo = _filtros_orcamento_despesas(filtros)
    key = f"{_filtros_orcamento_cache_key(fo)}:inativos={incluir_inativos}"

    def _compute() -> dict[int, Decimal]:
        meses = list(_meses_no_intervalo(fo.data_inicio, fo.data_fim))
        bulk = planejado_por_mes_bulk(usuario, meses, incluir_inativos=incluir_inativos)
        out: dict[int, Decimal] = {}
        for y, m in meses:
            for cid, o in bulk.get((y, m), {}).items():
                out[cid] = out.get(cid, Decimal("0")) + o.valor_planejado
        return out

    if cache is not None:
        return cache.get_or_set(f"planejado_periodo:{key}", _compute)
    return _compute()


def realizado_por_categoria_meses_bulk(
    usuario,
    meses_ref: list[tuple[int, int]],
    *,
    cache: RelatorioRequestCache | None = None,
) -> dict[tuple[int, int], dict[int, Decimal]]:
    """Realizado por categoria para vários meses com 1 agregação + mapa por nome."""
    if not meses_ref:
        return {}
    meses_set = set(meses_ref)
    inicio = date(meses_ref[0][0], meses_ref[0][1], 1)
    last_y, last_m = meses_ref[-1]
    fim = date(last_y, last_m, calendar.monthrange(last_y, last_m)[1])
    filtros = RelatorioFiltros(
        data_inicio=inicio,
        data_fim=fim,
        preset="custom",
        modo_data="competencia_cartao",
    )
    qs = queryset_despesas_orcamento(usuario, filtros)
    qs = qs.annotate(
        eff_date=Case(
            When(
                Q(cartao__isnull=False) & Q(data_competencia__isnull=False),
                then=F("data_competencia"),
            ),
            default=F("data"),
        ),
        ref_ano=ExtractYear("eff_date"),
        ref_mes=ExtractMonth("eff_date"),
    )
    rows = qs.values("categoria_id", "ref_ano", "ref_mes").annotate(gasto=Sum("valor"))

    por_mes: dict[tuple[int, int], dict[int, Decimal]] = {key: {} for key in meses_ref}
    for row in rows:
        key = (row["ref_ano"], row["ref_mes"])
        if key not in meses_set:
            continue
        cid = row["categoria_id"]
        if not cid:
            continue
        por_mes[key][cid] = por_mes[key].get(cid, Decimal("0")) + (row["gasto"] or Decimal("0"))

    nome_map = _nome_para_ids_map(usuario, cache=cache)
    for key in por_mes:
        por_mes[key] = _realizado_map_por_nome_categoria(usuario, por_mes[key], nome_ids_map=nome_map)
    return por_mes


def listar_orcamentos(
    usuario,
    filtros: RelatorioFiltros,
    *,
    ano_ref: int,
    mes_ref: int,
    incluir_inativos: bool = False,
    exibir_inativos: bool = False,
    incluir_gasto_sem_orcamento: bool = False,
    cache: RelatorioRequestCache | None = None,
) -> list[LinhaOrcamento]:
    """Lista orçamentos cadastrados; gastos no intervalo de filtros.

    ``incluir_inativos``: inativos entram no planejado agregado.
    ``exibir_inativos``: inativos aparecem na lista (planejado=0, badge Pausado).
    """
    fo = _filtros_orcamento_despesas(filtros)
    real_map = realizado_por_categoria_filtros(usuario, fo, cache=cache)
    planejado_map = planejado_por_categoria_periodo(
        usuario, fo, incluir_inativos=incluir_inativos, cache=cache
    )

    qs = OrcamentoCategoria.objects.filter(usuario=usuario).select_related("categoria")
    if not exibir_inativos:
        qs = qs.filter(ativo=True)

    linhas: list[LinhaOrcamento] = []
    nomes_cadastrados: set[str] = set()
    for o in qs.order_by("categoria__nome"):
        if o.ativo:
            if not o.vigente_em(ano_ref, mes_ref):
                continue
        elif not o.cadastrado_ate_mes(ano_ref, mes_ref):
            continue
        nomes_cadastrados.add(o.categoria.nome)
        planejado = planejado_map.get(o.categoria_id, Decimal("0"))
        realizado = real_map.get(o.categoria_id, Decimal("0"))
        linhas.append(
            montar_linha_orcamento(
                orcamento_id=o.pk,
                categoria_id=o.categoria_id,
                nome=o.categoria.nome,
                cor=o.categoria.cor,
                icone=o.categoria.icone,
                planejado=planejado,
                realizado=realizado,
                ativo=o.ativo,
            )
        )

    if incluir_gasto_sem_orcamento:
        from categorias.models import Categoria

        for cid, gasto in real_map.items():
            if gasto <= 0 or any(l.categoria_id == cid for l in linhas):
                continue
            cat = Categoria.objects.filter(pk=cid).first()
            if not cat or cat.nome in nomes_cadastrados:
                continue
            nomes_cadastrados.add(cat.nome)
            linhas.append(
                montar_linha_orcamento(
                    orcamento_id=None,
                    categoria_id=cid,
                    nome=cat.nome,
                    cor=cat.cor,
                    icone=cat.icone,
                    planejado=Decimal("0"),
                    realizado=gasto,
                    ativo=True,
                )
            )

    linhas.sort(key=lambda x: (-x.planejado, x.nome))
    return linhas


def listar_orcamentos_mes(
    usuario,
    ano: int,
    mes: int,
    *,
    incluir_inativos: bool = False,
    exibir_inativos: bool = False,
) -> list[LinhaOrcamento]:
    filtros = filtros_mes(ano, mes)
    return listar_orcamentos(
        usuario,
        filtros,
        ano_ref=ano,
        mes_ref=mes,
        incluir_inativos=incluir_inativos,
        exibir_inativos=exibir_inativos,
    )


def resumo_linhas_orcamento(linhas: list[LinhaOrcamento]) -> dict[str, Decimal]:
    """Totais do mês para linhas com planejado vigente."""
    vigentes = [l for l in linhas if l.planejado > 0]
    planejado = sum((l.planejado for l in vigentes), Decimal("0"))
    realizado = sum((l.realizado for l in vigentes), Decimal("0"))
    return {
        "planejado": planejado,
        "realizado": realizado,
        "disponivel": planejado - realizado,
    }


def painel_mes_orcamento(linhas: list[LinhaOrcamento], resumo: dict[str, Decimal]) -> dict[str, Any]:
    """Métricas agregadas do topo da tela de orçamentos (sem novas regras de negócio)."""
    planejado = resumo["planejado"]
    realizado = resumo["realizado"]
    disponivel = resumo["disponivel"]
    if planejado > 0:
        percentual = float(realizado / planejado * 100)
    else:
        percentual = None
    status, status_label = classificar_status(percentual)
    pct_exib = min(percentual, 100.0) if percentual is not None else 0.0

    vigentes = [l for l in linhas if l.planejado > 0]
    contagem = {"ok": 0, "risco": 0, "excedido": 0}
    for linha in vigentes:
        if linha.status in contagem:
            contagem[linha.status] += 1

    return {
        "planejado": planejado,
        "realizado": realizado,
        "disponivel": disponivel,
        "percentual": percentual,
        "percentual_exibicao": pct_exib,
        "status": status,
        "status_label": status_label,
        "contagem_saude": contagem,
        "total_categorias_vigentes": len(vigentes),
        "tem_vigentes": planejado > 0,
    }


def navegacao_mes_context(
    ano: int,
    mes: int,
    *,
    nav_qs_extra: str = "",
    meses_dropdown_count: int = 24,
) -> dict[str, Any]:
    """Contexto para partial navegacao_mes_periodo (padrão histórico de transações)."""
    hoje = date.today()
    data_mes = date(ano, mes, 1)
    if mes == 1:
        mes_anterior, ano_anterior = 12, ano - 1
    else:
        mes_anterior, ano_anterior = mes - 1, ano
    if mes == 12:
        mes_proximo, ano_proximo = 1, ano + 1
    else:
        mes_proximo, ano_proximo = mes + 1, ano

    meses_dropdown: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    y, m = hoje.year, hoje.month
    for _ in range(meses_dropdown_count):
        seen.add((y, m))
        meses_dropdown.append({"ano": y, "mes": m, "data_mes": date(y, m, 1)})
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
    if (ano, mes) not in seen:
        meses_dropdown.append({"ano": ano, "mes": mes, "data_mes": data_mes})
    meses_dropdown.sort(key=lambda x: (x["ano"], x["mes"]), reverse=True)

    return {
        "data_mes": data_mes,
        "ano_anterior": ano_anterior,
        "mes_anterior": mes_anterior,
        "ano_proximo": ano_proximo,
        "mes_proximo": mes_proximo,
        "ano_hoje": hoje.year,
        "mes_hoje": hoje.month,
        "meses_dropdown": meses_dropdown,
        "nav_qs_extra": nav_qs_extra,
    }


def listar_orcamentos_dashboard(
    usuario,
    filtros: RelatorioFiltros | None = None,
    *,
    limite: int = 3,
    cache: RelatorioRequestCache | None = None,
) -> list[LinhaOrcamento]:
    if filtros is None:
        hoje = date.today()
        linhas = listar_orcamentos_mes(usuario, hoje.year, hoje.month)
    else:
        ano_ref, mes_ref = referencia_mes_orcamento(filtros)
        linhas = listar_orcamentos(
            usuario,
            filtros,
            ano_ref=ano_ref,
            mes_ref=mes_ref,
            cache=cache,
        )
    linhas = [l for l in linhas if l.planejado > 0]
    linhas.sort(key=lambda x: x.percentual or 0, reverse=True)
    return linhas[:limite]


def orcamento_vs_realizado(usuario, filtros: RelatorioFiltros) -> list[dict[str, Any]]:
    """Compatível com relatórios multi-mês: agrega planejado e realizado no intervalo."""
    fo = _filtros_orcamento_despesas(filtros)
    real_map = realizado_por_categoria_filtros(usuario, fo)
    planejado_por_cat = planejado_por_categoria_periodo(usuario, fo)

    categoria_ids = set(planejado_por_cat) | set(real_map.keys())
    orcamentos_por_cat = {
        o.categoria_id: o
        for o in OrcamentoCategoria.objects.filter(usuario=usuario, categoria_id__in=categoria_ids).select_related(
            "categoria"
        )
    }
    cats_sem_orc = [cid for cid in categoria_ids if cid not in orcamentos_por_cat]
    categorias_map = {}
    if cats_sem_orc:
        from categorias.models import Categoria

        categorias_map = {c.pk: c for c in Categoria.objects.filter(pk__in=cats_sem_orc)}

    out: list[dict[str, Any]] = []
    for cid in categoria_ids:
        planejado = planejado_por_cat.get(cid, Decimal("0"))
        realizado = real_map.get(cid, Decimal("0"))
        o = orcamentos_por_cat.get(cid)
        if o:
            nome, cor, icone = o.categoria.nome, o.categoria.cor, o.categoria.icone
        else:
            c = categorias_map.get(cid)
            nome = c.nome if c else "?"
            cor = c.cor if c else "#6B7280"
            icone = c.icone if c else "fa-ellipsis-h"
        linha = montar_linha_orcamento(
            orcamento_id=o.pk if o else None,
            categoria_id=cid,
            nome=nome,
            cor=cor,
            icone=icone,
            planejado=planejado,
            realizado=realizado,
            ativo=o.ativo if o else False,
        )
        d = linha.as_dict()
        out.append(d)

    out.sort(key=lambda x: x["realizado"], reverse=True)
    return out


def usuario_tem_orcamentos_cadastrados(usuario) -> bool:
    return OrcamentoCategoria.objects.filter(usuario=usuario).exists()


def usuario_tem_orcamentos_vigentes_mes(usuario, ano: int, mes: int) -> bool:
    return any(planejado_mes(usuario, ano, mes).values())


def historico_utilizacao_categoria(
    usuario,
    categoria_id: int,
    *,
    meses: int = 3,
    referencia: date | None = None,
    cache: RelatorioRequestCache | None = None,
) -> list[dict[str, Any]]:
    """Últimos N meses de percentual consumido (texto, sem gráfico)."""
    bulk = historico_utilizacao_categorias_bulk(
        usuario,
        [categoria_id],
        meses=meses,
        referencia=referencia,
        cache=cache,
    )
    return bulk.get(categoria_id, [])


def historico_utilizacao_categorias_bulk(
    usuario,
    categoria_ids: list[int],
    *,
    meses: int = 3,
    referencia: date | None = None,
    cache: RelatorioRequestCache | None = None,
) -> dict[int, list[dict[str, Any]]]:
    """Histórico de utilização para várias categorias com agregações por mês."""
    ids = list({cid for cid in categoria_ids if cid})
    if not ids:
        return {}

    ref = referencia or date.today()
    y, m = ref.year, ref.month
    meses_ref: list[tuple[int, int]] = []
    for _ in range(meses):
        meses_ref.append((y, m))
        if m == 1:
            y -= 1
            m = 12
        else:
            m -= 1
    meses_ref.reverse()
    meses_key = ",".join(f"{a}-{m}" for a, m in meses_ref)

    def _realizado_bulk():
        return realizado_por_categoria_meses_bulk(usuario, meses_ref, cache=cache)

    def _planejado_bulk():
        return planejado_por_mes_bulk(usuario, meses_ref)

    if cache is not None:
        realizado_por_mes = cache.get_or_set(f"realizado_meses:{meses_key}", _realizado_bulk)
        planejado_por_mes = cache.planejado_por_mes_bulk(meses_key, _planejado_bulk)
    else:
        realizado_por_mes = _realizado_bulk()
        planejado_por_mes = _planejado_bulk()

    resultado: dict[int, list[dict[str, Any]]] = {}
    for cid in ids:
        historico: list[dict[str, Any]] = []
        for ano, mes in meses_ref:
            real_map = realizado_por_mes[(ano, mes)]
            orc = planejado_por_mes[(ano, mes)].get(cid)
            planejado = orc.valor_planejado if orc else Decimal("0")
            realizado = real_map.get(cid, Decimal("0"))
            pct = float(realizado / planejado * 100) if planejado > 0 else None
            historico.append(
                {
                    "ano": ano,
                    "mes": mes,
                    "rotulo": f"{MESES_PT[mes - 1][:3]}/{ano}",
                    "percentual": pct,
                    "planejado": planejado,
                    "realizado": realizado,
                }
            )
        resultado[cid] = historico
    return resultado
