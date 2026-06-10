"""
EXT-03..04 E2E — Observabilidade de tempo de carregamento via browser.

EXT-01, EXT-02, EXT-05 rodam apenas em tests/performance/test_extended.py (unit).
"""

from __future__ import annotations

import time

import pytest
from django.urls import reverse

from e2e.factories.personas import E2E_PASSWORD
from e2e.fixtures.pages.login_page import LoginPage
from tests.performance.helpers.seed import seed_perf_user, seed_transacoes_volume

pytestmark = pytest.mark.performance_extended


@pytest.fixture
def perf_ext_persona(db):
    data = seed_perf_user(f"perf-e2e-ext-{__import__('os').getpid()}@e2e.granago.test")
    data["user"].set_password(E2E_PASSWORD)
    data["user"].save(update_fields=["password"])
    return data


@pytest.fixture
def logged_in_perf_ext(page, app_base_url, perf_ext_persona):
    login = LoginPage(page, app_base_url)
    login.login(perf_ext_persona["user"].email, E2E_PASSWORD)
    login.expect_redirect_dashboard()
    return page, perf_ext_persona


@pytest.mark.django_db(transaction=True)
def test_ext_03_e2e_relatorios_500_tx_elapsed(logged_in_perf_ext, app_base_url):
    """EXT-03 E2E: GET /relatorios/ 500 tx → elapsed <= 15s."""
    page, data = logged_in_perf_ext
    seed_transacoes_volume(
        data["user"],
        data["conta"],
        data["cat_desp"],
        data["cat_rec"],
        n=500,
    )
    url = app_base_url + reverse("relatorios:home")
    t0 = time.monotonic()
    page.goto(url, wait_until="networkidle")
    elapsed = time.monotonic() - t0
    assert elapsed <= 15.0, f"E2E /relatorios/ 500 tx lento: {elapsed:.2f}s"


@pytest.mark.django_db(transaction=True)
def test_ext_04_e2e_transacoes_500_tx_elapsed(logged_in_perf_ext, app_base_url):
    """EXT-04 E2E: GET /transacoes/ 500 tx → elapsed <= 20s."""
    page, data = logged_in_perf_ext
    seed_transacoes_volume(
        data["user"],
        data["conta"],
        data["cat_desp"],
        data["cat_rec"],
        n=500,
    )
    url = app_base_url + reverse("transacoes:historico")
    t0 = time.monotonic()
    page.goto(url, wait_until="networkidle")
    elapsed = time.monotonic() - t0
    assert elapsed <= 20.0, f"E2E /transacoes/ 500 tx lento: {elapsed:.2f}s"
