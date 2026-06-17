"""
Orçamentos de queries por rota — baseline para validação de performance.
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from tests.performance.helpers.seed import seed_perf_user

pytestmark = pytest.mark.performance_budget


@pytest.fixture
def perf_client(db):
    data = seed_perf_user("perf-budget@test.local")
    client = Client(enforce_csrf_checks=False)
    client.force_login(data["user"])
    data["client"] = client
    return data


@pytest.mark.django_db
def test_query_budget_relatorios_home(perf_client):
    url = reverse("relatorios:home")
    with CaptureQueriesContext(connection) as ctx:
        response = perf_client["client"].get(url)
    assert response.status_code == 200
    assert len(ctx) <= 45, f"home excedeu budget: {len(ctx)} queries"


@pytest.mark.django_db
def test_query_budget_transacoes_historico(perf_client):
    url = reverse("transacoes:historico")
    with CaptureQueriesContext(connection) as ctx:
        response = perf_client["client"].get(url)
    assert response.status_code == 200
    assert len(ctx) <= 35, f"histórico excedeu budget: {len(ctx)} queries"


@pytest.mark.django_db
def test_query_budget_login_page(db):
    client = Client()
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(reverse("usuarios:login"))
    assert response.status_code == 200
    assert len(ctx) <= 5, f"login excedeu budget: {len(ctx)} queries"
