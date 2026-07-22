from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.parse import urlencode

from django.db.models import Q
from django.http import QueryDict

from categorias.models import Categoria
from contas.models import Conta

# Limite anti-abuso para intervalos customizados (dias).
MAX_INTERVALO_DIAS = 800

TIPOS_VALIDOS = frozenset({"receita", "despesa", "ajuste", "transferencia"})


@dataclass(frozen=True)
class RelatorioFiltros:
    """Filtros canônicos para dashboards e APIs (derivados de GET)."""

    data_inicio: date
    data_fim: date
    conta_ids: tuple[int, ...] = ()
    categoria_ids: tuple[int, ...] = ()
    tipos: tuple[str, ...] = ()  # vazio = todos (receita, despesa, ajuste)
    preset: str = "custom"  # rótulo do preset usado (para UI)
    meio_pagamento: str = "todos"  # todos | debito | credito
    modo_data: str = "fluxo"  # fluxo | competencia_cartao

    def to_query_dict(self) -> dict[str, list[str]]:
        """Parâmetros GET equivalentes (listas para urlencode multi-value)."""
        d: dict[str, list[str]] = {
            "inicio": [self.data_inicio.isoformat()],
            "fim": [self.data_fim.isoformat()],
        }
        if self.preset and self.preset != "custom":
            d["preset"] = [self.preset]
        for cid in self.conta_ids:
            d.setdefault("conta", []).append(str(cid))
        for cat in self.categoria_ids:
            d.setdefault("categoria", []).append(str(cat))
        for t in self.tipos:
            d.setdefault("tipo", []).append(t)
        if self.meio_pagamento and self.meio_pagamento != "todos":
            d.setdefault("meio_pagamento", []).append(self.meio_pagamento)
        if self.modo_data and self.modo_data != "fluxo":
            d.setdefault("modo_data", []).append(self.modo_data)
        return d

    def to_query_string(self) -> str:
        return urlencode(self.to_query_dict(), doseq=True)

    def to_drill_transacoes_query_string(self) -> str:
        """Query string mínima para lista de transações (período + contas), sem categoria/tipo."""
        d: dict[str, list[str]] = {
            "inicio": [self.data_inicio.isoformat()],
            "fim": [self.data_fim.isoformat()],
        }
        for cid in self.conta_ids:
            d.setdefault("conta", []).append(str(cid))
        return urlencode(d, doseq=True)

    def to_drill_transacoes_periodo_e_conta(self, conta_id: int) -> str:
        """Histórico só desta conta no mesmo intervalo (evita múltiplos `conta=` na URL)."""
        d: dict[str, list[str]] = {
            "inicio": [self.data_inicio.isoformat()],
            "fim": [self.data_fim.isoformat()],
            "conta": [str(conta_id)],
        }
        return urlencode(d, doseq=True)

    def contagem_filtros_ativos(self, *, preset_padrao: str = "este_mes") -> int:
        """Quantidade de dimensões de filtro diferentes do padrão (para badge na UI)."""
        n = 0
        if self.preset != preset_padrao:
            n += 1
        if self.conta_ids:
            n += 1
        if self.categoria_ids:
            n += 1
        if self.tipos:
            n += 1
        if self.meio_pagamento != "todos":
            n += 1
        if self.modo_data != "fluxo":
            n += 1
        return n


def _last_day_of_month(d: date) -> date:
    _, last = calendar.monthrange(d.year, d.month)
    return date(d.year, d.month, last)


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        y, m, day = s.strip().split("-")
        return date(int(y), int(m), int(day))
    except (ValueError, TypeError):
        return None


def _parse_int_list(values: list[str]) -> list[int]:
    out: list[int] = []
    for v in values:
        try:
            out.append(int(v))
        except (TypeError, ValueError):
            continue
    return out


def _intervalo_valido(inicio: date, fim: date) -> tuple[date, date]:
    if fim < inicio:
        inicio, fim = fim, inicio
    if (fim - inicio).days > MAX_INTERVALO_DIAS:
        fim = inicio + timedelta(days=MAX_INTERVALO_DIAS)
    return inicio, fim


PRESETS_CONHECIDOS = frozenset(
    {"este_mes", "mes_anterior", "ultimos_30d", "ultimos_90d", "este_ano"}
)


def parse_relatorio_filtros(
    get_params: QueryDict,
    *,
    usuario,
    default_preset: str = "este_mes",
) -> RelatorioFiltros:
    """
    Constrói filtros a partir de request.GET.
    Presets: este_mes, mes_anterior, ultimos_30d, ultimos_90d, este_ano, custom (inicio+fim).
    """
    hoje = date.today()
    raw_preset = (get_params.get("preset") or "").strip()
    inicio = _parse_date(get_params.get("inicio"))
    fim = _parse_date(get_params.get("fim"))

    if raw_preset in PRESETS_CONHECIDOS:
        preset = raw_preset
    elif inicio is not None and fim is not None:
        preset = "custom"
    else:
        preset = (raw_preset or default_preset) if (raw_preset or default_preset) in PRESETS_CONHECIDOS else default_preset

    if preset == "este_mes":
        inicio = hoje.replace(day=1)
        fim = _last_day_of_month(hoje)
    elif preset == "mes_anterior":
        primeiro_mes_atual = hoje.replace(day=1)
        ultimo_mes_anterior = primeiro_mes_atual - timedelta(days=1)
        inicio = ultimo_mes_anterior.replace(day=1)
        fim = _last_day_of_month(ultimo_mes_anterior)
    elif preset == "ultimos_30d":
        fim = hoje
        inicio = hoje - timedelta(days=29)
    elif preset == "ultimos_90d":
        fim = hoje
        inicio = hoje - timedelta(days=89)
    elif preset == "este_ano":
        inicio = date(hoje.year, 1, 1)
        fim = date(hoje.year, 12, 31)
    else:
        preset = "custom"
        if inicio is None or fim is None:
            inicio = hoje.replace(day=1)
            fim = _last_day_of_month(hoje)

    assert inicio is not None and fim is not None
    inicio, fim = _intervalo_valido(inicio, fim)

    conta_ids = tuple(
        sorted(
            set(
                cid
                for cid in _parse_int_list(get_params.getlist("conta"))
                if Conta.objects.filter(pk=cid, usuario=usuario, ativa=True).exists()
            )
        )
    )

    cat_qs = Categoria.objects.filter(Q(usuario=usuario) | Q(padrao=True))
    categoria_ids = tuple(
        sorted(
            set(
                cid
                for cid in _parse_int_list(get_params.getlist("categoria"))
                if cat_qs.filter(pk=cid).exists()
            )
        )
    )

    tipos_list = [t for t in get_params.getlist("tipo") if t in TIPOS_VALIDOS]
    tipos = tuple(dict.fromkeys(tipos_list))  # preserva ordem, únicos

    meio = (get_params.get("meio_pagamento") or "todos").strip().lower()
    if meio not in ("todos", "debito", "credito"):
        meio = "todos"
    modo = (get_params.get("modo_data") or "fluxo").strip().lower()
    if modo not in ("fluxo", "competencia_cartao"):
        modo = "fluxo"

    return RelatorioFiltros(
        data_inicio=inicio,
        data_fim=fim,
        conta_ids=conta_ids,
        categoria_ids=categoria_ids,
        tipos=tipos,
        preset=preset,
        meio_pagamento=meio,
        modo_data=modo,
    )


def parse_comparativo_secundario(
    get_params: QueryDict,
    *,
    usuario,
    primario: RelatorioFiltros,
) -> RelatorioFiltros | None:
    """Se `comparar=1` e datas `comp_inicio`/`comp_fim` válidas, retorna segundo período."""
    if get_params.get("comparar") not in ("1", "true", "on", "yes"):
        return None
    ci = _parse_date(get_params.get("comp_inicio"))
    cf = _parse_date(get_params.get("comp_fim"))
    if not ci or not cf:
        # período anterior com mesma duração, encostado antes do primário
        span = (primario.data_fim - primario.data_inicio).days
        cf = primario.data_inicio - timedelta(days=1)
        ci = cf - timedelta(days=span)
    ci, cf = _intervalo_valido(ci, cf)
    return RelatorioFiltros(
        data_inicio=ci,
        data_fim=cf,
        conta_ids=primario.conta_ids,
        categoria_ids=primario.categoria_ids,
        tipos=primario.tipos,
        preset="custom",
        meio_pagamento=primario.meio_pagamento,
        modo_data=primario.modo_data,
    )
