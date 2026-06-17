"""Budgets de payload HTMX — partials não devem ser gigantes."""

from __future__ import annotations

import gzip

import pytest
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from tests.performance.helpers.seed import seed_perf_user

pytestmark = pytest.mark.performance_budget

DOM_TAGS = (b"<div", b"<tr", b"<li", b"<span", b"<button", b"<a ", b"<td")


@pytest.fixture
def perf_client(db):
    data = seed_perf_user("perf-htmx@test.local")
    client = Client(enforce_csrf_checks=False)
    client.force_login(data["user"])
    data["client"] = client
    return data


@pytest.mark.django_db
def test_htmx_orcamentos_partial_queries_budget(perf_client):
    full_url = reverse("relatorios:orcamentos")
    client = perf_client["client"]
    with CaptureQueriesContext(connection) as full_ctx:
        full = client.get(full_url)
    with CaptureQueriesContext(connection) as htmx_ctx:
        partial = client.get(full_url, HTTP_HX_REQUEST="true")
    assert full.status_code == 200
    assert partial.status_code == 200
    assert len(htmx_ctx) <= max(18, len(full_ctx) // 2 + 2), (
        f"partial HTMX com muitas queries: {len(htmx_ctx)} vs full {len(full_ctx)}"
    )
    assert len(partial.content) <= len(full.content) * 0.6


@pytest.mark.django_db
def test_htmx_historico_pagination_dom_budget(perf_client):
    url = reverse("transacoes:historico")
    client = perf_client["client"]
    full = client.get(url)
    partial = client.get(url, {"page": 2}, HTTP_HX_REQUEST="true")
    assert full.status_code == 200
    assert partial.status_code == 200
    dom_partial = sum(partial.content.count(t) for t in DOM_TAGS)
    assert dom_partial <= 250, f"DOM partial alto: ~{dom_partial} nós"
    gzip_partial = len(gzip.compress(partial.content, compresslevel=6))
    assert gzip_partial <= 40 * 1024, f"partial gzip alto: {gzip_partial} bytes"
