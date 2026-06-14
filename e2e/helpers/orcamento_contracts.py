"""Wrappers E2E para contratos ORC-CON-*."""

from __future__ import annotations

from decimal import Decimal

from django.http import QueryDict
from django.utils import timezone

from relatorios.services.filtros import RelatorioFiltros, parse_relatorio_filtros
from relatorios.services.orcamentos import (
    _filtros_orcamento_despesas,
    listar_orcamentos,
    listar_orcamentos_mes,
    painel_mes_orcamento,
    referencia_mes_orcamento,
    resumo_linhas_orcamento,
)


def filtros_mes_atual(user) -> RelatorioFiltros:
    hoje = timezone.localdate()
    q = QueryDict(mutable=True)
    q["preset"] = "este_mes"
    return parse_relatorio_filtros(q, usuario=user)


def linhas_esperadas(user, params: dict | None = None) -> list:
    params = params or {"preset": "este_mes"}
    q = QueryDict(mutable=True)
    for k, v in params.items():
        if isinstance(v, list):
            q.setlist(k, [str(x) for x in v])
        else:
            q[k] = str(v)
    filtros = parse_relatorio_filtros(q, usuario=user)
    fo = _filtros_orcamento_despesas(filtros)
    ano, mes = referencia_mes_orcamento(filtros)
    return listar_orcamentos(
        user, fo, ano_ref=ano, mes_ref=mes, exibir_inativos=True
    )


def linha_por_nome(user, nome: str, params: dict | None = None):
    linhas = linhas_esperadas(user, params)
    return next((l for l in linhas if l.nome == nome), None)


def painel_esperado(user, params: dict | None = None) -> dict:
    linhas = linhas_esperadas(user, params)
    resumo = resumo_linhas_orcamento(linhas)
    return painel_mes_orcamento(linhas, resumo)


def verify_linha_categoria(
    user,
    nome: str,
    *,
    planejado: Decimal | None = None,
    realizado: Decimal | None = None,
    status: str | None = None,
    params: dict | None = None,
) -> None:
    linha = linha_por_nome(user, nome, params)
    assert linha is not None, f"Categoria {nome} não encontrada"
    if planejado is not None:
        assert linha.planejado == planejado, f"planejado {linha.planejado} != {planejado}"
    if realizado is not None:
        assert linha.realizado == realizado, f"realizado {linha.realizado} != {realizado}"
    if status is not None:
        assert linha.status == status, f"status {linha.status} != {status}"


def verify_painel_mes(user, params: dict | None = None) -> dict:
    return painel_esperado(user, params)


def linhas_mes(user, ano: int, mes: int):
    return listar_orcamentos_mes(user, ano, mes)
