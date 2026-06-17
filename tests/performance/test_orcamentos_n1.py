"""Testes de performance — orçamentos sem N+1 por nome de categoria."""

from __future__ import annotations

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from categorias.models import Categoria
from relatorios.services.orcamentos import (
    _filtros_orcamento_despesas,
    filtros_mes,
    realizado_por_categoria_filtros,
)
from tests.performance.helpers.seed import seed_perf_user

pytestmark = pytest.mark.performance_budget


@pytest.mark.django_db
def test_realizado_map_sem_n1_por_nome_categoria(db):
    data = seed_perf_user("perf-n1@test.local")
    user = data["user"]
    hoje = timezone.localdate()

    for i in range(5):
        Categoria.objects.get_or_create(
            usuario=user,
            nome=f"Perf N1 Cat {i}",
            defaults={"tipo": "despesa", "ativa": True, "cor": "#6366F1"},
        )

    filtros = _filtros_orcamento_despesas(filtros_mes(hoje.year, hoje.month))
    with CaptureQueriesContext(connection) as ctx:
        realizado_por_categoria_filtros(user, filtros)

    # 1 agregação + mapa nomes + categorias por_id (sem loop por nome)
    assert len(ctx) <= 6, f"N+1 suspeito em realizado_map: {len(ctx)} queries"
