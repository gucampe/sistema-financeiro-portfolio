"""Memoização intra-request para relatórios (zero stale cross-request)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from django.contrib.auth import get_user_model

User = get_user_model()
T = TypeVar("T")


class RelatorioRequestCache:
    """Cache leve por request — deduplica agregações entre serviços/views."""

    def __init__(self, user: User):
        self.user = user
        self._store: dict[str, Any] = {}

    def get_or_set(self, key: str, factory: Callable[[], T]) -> T:
        if key not in self._store:
            self._store[key] = factory()
        return self._store[key]

    def categorias_despesa(self, factory: Callable[[], T]) -> T:
        return self.get_or_set("categorias_despesa", factory)

    def categorias_receita(self, factory: Callable[[], T]) -> T:
        return self.get_or_set("categorias_receita", factory)

    def comparacao_mensal(self, factory: Callable[[], T]) -> T:
        return self.get_or_set("comparacao_mensal", factory)

    def realizado_por_categoria_filtros(self, filtros_key: str, factory: Callable[[], T]) -> T:
        return self.get_or_set(f"realizado:{filtros_key}", factory)

    def planejado_mes(self, ano: int, mes: int, factory: Callable[[], T]) -> T:
        return self.get_or_set(f"planejado:{ano}-{mes}", factory)

    def planejado_por_mes_bulk(self, meses_key: str, factory: Callable[[], T]) -> T:
        return self.get_or_set(f"planejado_bulk:{meses_key}", factory)

    def listar_orcamentos_mes(self, ano: int, mes: int, factory: Callable[[], T]) -> T:
        return self.get_or_set(f"orcamentos_mes:{ano}-{mes}", factory)

    def nome_ids_map(self, factory: Callable[[], T]) -> T:
        return self.get_or_set("nome_ids_map", factory)
