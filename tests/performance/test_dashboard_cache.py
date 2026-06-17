"""Testes do cache cross-request do dashboard (gated)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.test import override_settings

from relatorios.services.dashboard_cache import (
    get_cached_patrimonio,
    invalidate_dashboard_user,
)
from tests.performance.helpers.seed import seed_perf_user

pytestmark = pytest.mark.performance_budget


@pytest.mark.django_db
@override_settings(ENABLE_DASHBOARD_AGG_CACHE=True)
def test_dashboard_cache_invalidation_on_transacao(db):
    data = seed_perf_user("perf-cache@test.local")
    user = data["user"]
    cache.clear()

    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return {"patrimonio_total": Decimal("1000"), "contas": []}

    get_cached_patrimonio(user.pk, factory)
    get_cached_patrimonio(user.pk, factory)
    assert calls["n"] == 1

    invalidate_dashboard_user(user.pk)
    get_cached_patrimonio(user.pk, factory)
    assert calls["n"] == 2
