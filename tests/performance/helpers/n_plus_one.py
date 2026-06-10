"""
Detecção estrutural de N+1 — padrão de SQL repetido por entidade do hotspot.

Não usa contagem total, thresholds, ratio ou tempo.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

# Tabelas de infraestrutura Django — ignoradas na detecção.
_IGNORE_TABLES = frozenset(
    {
        "DJANGO_SESSION",
        "DJANGO_CONTENT_TYPE",
        "AUTH_",
        "SQLITE_",
    }
)


def _is_select(sql: str) -> bool:
    return sql.strip().upper().startswith("SELECT")


def _should_ignore(normalized: str) -> bool:
    upper = normalized.upper()
    return any(token in upper for token in _IGNORE_TABLES)


def normalize_sql(sql: str) -> str:
    """Normaliza SQL para comparação estrutural (literais → placeholder)."""
    s = re.sub(r"\s+", " ", sql.strip())
    s = re.sub(r"'[^']*'", "?", s)
    s = re.sub(r"\b\d+\b", "?", s)
    return s.upper()


def detect_repeated_selects(
    queries: Iterable[str],
    *,
    min_repeats: int = 2,
    table_hints: tuple[str, ...] = (),
) -> list[tuple[str, int]]:
    """
    Retorna pares (sql_normalizado, contagem) de SELECTs estruturalmente iguais
    que se repetem >= min_repeats vezes.
    """
    counter: Counter[str] = Counter()
    hints = tuple(h.upper() for h in table_hints)

    for raw in queries:
        if not _is_select(raw):
            continue
        norm = normalize_sql(raw)
        if _should_ignore(norm):
            continue
        if hints and not any(h in norm for h in hints):
            continue
        counter[norm] += 1

    return sorted(
        [(sql, count) for sql, count in counter.items() if count >= min_repeats],
        key=lambda item: -item[1],
    )


def assert_no_entity_loop_queries(
    captured_queries,
    *,
    entity_count: int,
    table_hints: tuple[str, ...],
    min_repeats: int = 2,
    context: str = "",
) -> None:
    """
    FAIL se existir SELECT repetido por entidade do hotspot (padrão N+1).

    Requer entity_count >= min_repeats para detecção significativa.
    """
    if entity_count < min_repeats:
        return

    sqls = [q["sql"] for q in captured_queries.captured_queries]
    offenders = detect_repeated_selects(
        sqls,
        min_repeats=min_repeats,
        table_hints=table_hints,
    )
    # N+1 = mesma query repetida por item do queryset principal (contagem ≈ entidades).
    loop_offenders = [
        (pattern, count)
        for pattern, count in offenders
        if count >= entity_count and count >= min_repeats
    ]
    if not loop_offenders:
        return

    label = f" ({context})" if context else ""
    lines = "\n".join(f"  [{count}x] {pattern[:240]}" for pattern, count in loop_offenders)
    raise AssertionError(
        f"N+1 detectado{label}: mesma query executada repetidamente por entidade do hotspot:\n{lines}"
    )
