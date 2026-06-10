"""
PERF-PR-01..05 — Detecção estrutural de N+1 em hotspots conhecidos.

Regra única: 1 request + CaptureQueriesContext + padrão de SQL repetido por entidade.
Proibido: contagem total, thresholds, delta, ratio, tempo, loops de medição.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from tests.performance.helpers.n_plus_one import assert_no_entity_loop_queries
from tests.performance.helpers.seed import (
    seed_cartoes_dashboard,
    seed_categorias_despesa,
    seed_perf_user,
    seed_transacoes_mes,
    seed_transacoes_periodo,
)

pytestmark = pytest.mark.performance_pr


@pytest.fixture
def perf_client(db):
    data = seed_perf_user("perf-pr@test.local")
    client = Client(enforce_csrf_checks=False)
    client.force_login(data["user"])
    data["client"] = client
    return data


@pytest.mark.django_db
def test_perf_pr_01_relatorios_home_sem_n_plus_one_cartoes(perf_client):
    """GET /relatorios/ — FAIL se query de cartão/fatura repetida por cartão."""
    user = perf_client["user"]
    n_cartoes = seed_cartoes_dashboard(
        user, perf_client["conta"], perf_client["cat_desp"], n_cartoes=5
    )

    url = reverse("relatorios:home")
    with CaptureQueriesContext(connection) as ctx:
        response = perf_client["client"].get(url)

    assert response.status_code == 200
    assert_no_entity_loop_queries(
        ctx,
        entity_count=n_cartoes,
        table_hints=("CARTOES_CARTAO", "CARTOES_FATURA", "TRANSACOES_TRANSACAO"),
        context="PERF-PR-01 /relatorios/ resumo_cartoes",
    )


@pytest.mark.django_db
def test_perf_pr_02_fluxo_caixa_sem_n_plus_one_dia(perf_client):
    """GET fluxo-caixa?preset=ultimos_90d — FAIL se agregação por dia em loop."""
    user = perf_client["user"]
    n_dias = 30
    seed_transacoes_periodo(
        user, perf_client["conta"], perf_client["cat_desp"], dias=n_dias, por_dia=1
    )

    url = reverse("relatorios:fluxo_caixa") + "?preset=ultimos_90d"
    with CaptureQueriesContext(connection) as ctx:
        response = perf_client["client"].get(url)

    assert response.status_code == 200
    assert_no_entity_loop_queries(
        ctx,
        entity_count=n_dias,
        table_hints=("TRANSACOES_TRANSACAO",),
        context="PERF-PR-02 fluxo-caixa serie diária",
    )


@pytest.mark.django_db
def test_perf_pr_03_api_serie_tendencia_sem_n_plus_one_periodo(perf_client):
    """GET api/serie-tendencia — FAIL se query por período repetida por ponto da série."""
    user = perf_client["user"]
    n_dias = 30
    seed_transacoes_periodo(
        user, perf_client["conta"], perf_client["cat_desp"], dias=n_dias, por_dia=1
    )

    url = reverse("relatorios:api_serie_tendencia") + "?preset=ultimos_90d"
    with CaptureQueriesContext(connection) as ctx:
        response = perf_client["client"].get(url)

    assert response.status_code == 200
    assert_no_entity_loop_queries(
        ctx,
        entity_count=n_dias,
        table_hints=("TRANSACOES_TRANSACAO",),
        context="PERF-PR-03 api/serie-tendencia",
    )


@pytest.mark.django_db
def test_perf_pr_04_despesas_por_categoria_sem_n_plus_one_categoria(perf_client):
    """GET despesas-por-categoria — FAIL se query de categoria repetida no loop."""
    user = perf_client["user"]
    _, n_cats = seed_categorias_despesa(user, perf_client["conta"], n_categorias=8)

    url = reverse("relatorios:despesas_categoria") + "?preset=este_mes"
    with CaptureQueriesContext(connection) as ctx:
        response = perf_client["client"].get(url)

    assert response.status_code == 200
    assert_no_entity_loop_queries(
        ctx,
        entity_count=n_cats,
        table_hints=("TRANSACOES_TRANSACAO", "CATEGORIAS_CATEGORIA"),
        context="PERF-PR-04 despesas-por-categoria",
    )


@pytest.mark.django_db
def test_perf_pr_05_transacoes_sem_n_plus_one_render(perf_client):
    """GET /transacoes/ — FAIL se query por transação/related repetida no loop."""
    user = perf_client["user"]
    n_tx = seed_transacoes_mes(
        user,
        perf_client["conta"],
        perf_client["cat_desp"],
        perf_client["cat_rec"],
        n=12,
    )

    url = reverse("transacoes:historico")
    with CaptureQueriesContext(connection) as ctx:
        response = perf_client["client"].get(url)

    assert response.status_code == 200
    assert_no_entity_loop_queries(
        ctx,
        entity_count=n_tx,
        table_hints=("TRANSACOES_TRANSACAO", "CATEGORIAS_CATEGORIA", "CONTAS_CONTA"),
        context="PERF-PR-05 /transacoes/",
    )
