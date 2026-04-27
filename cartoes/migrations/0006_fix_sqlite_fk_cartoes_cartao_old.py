"""
Corrige SQLite onde o DDL ainda referencia cartoes_cartao_old (tabela temporária
da migração 0002). Isso quebra INSERT em cartoes_fatura / transacoes_transacao.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from django.db import migrations

if TYPE_CHECKING:
    from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=%s LIMIT 1",
        [name],
    )
    return cursor.fetchone() is not None


def _substitute_create_table_name(sql: str, new_table: str) -> str:
    """Substitui apenas o nome da tabela na cláusula CREATE TABLE inicial."""
    return re.sub(
        r"(CREATE TABLE\s+)(?:\"([^\"]+)\"|(\w+))(\s*\()",
        rf'\1"{new_table}"\4',
        sql,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )


def _sqlite_rebuild_table_if_cartao_old(cursor, table: str) -> None:
    if not _table_exists(cursor, table):
        return

    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=%s",
        [table],
    )
    row = cursor.fetchone()
    if not row or not row[0]:
        return
    create_sql = row[0]
    if "cartoes_cartao_old" not in create_sql:
        return

    tmp = f"{table}_djfixtmp"
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=%s LIMIT 1",
        [tmp],
    )
    if cursor.fetchone():
        cursor.execute(f'DROP TABLE "{tmp}"')

    fixed = create_sql.replace("cartoes_cartao_old", "cartoes_cartao")
    fixed = _substitute_create_table_name(fixed, tmp)

    cursor.execute(
        """
        SELECT name, sql FROM sqlite_master
        WHERE type='index' AND tbl_name=%s AND sql IS NOT NULL
        """,
        [table],
    )
    index_ddls = [(n, s) for n, s in cursor.fetchall() if not n.startswith("sqlite_")]

    cursor.execute(fixed)
    cursor.execute(f'INSERT INTO "{tmp}" SELECT * FROM "{table}"')
    cursor.execute(f'DROP TABLE "{table}"')
    cursor.execute(f'ALTER TABLE "{tmp}" RENAME TO "{table}"')

    for _name, idx_sql in index_ddls:
        cursor.execute(idx_sql)


def forwards(apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    connection = schema_editor.connection
    if connection.vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys=OFF")
        try:
            for tbl in ("cartoes_fatura", "transacoes_transacao"):
                _sqlite_rebuild_table_if_cartao_old(cursor, tbl)
        finally:
            cursor.execute("PRAGMA foreign_keys=ON")


def backwards(apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("cartoes", "0005_fatura_legacy_columns_complete"),
        ("transacoes", "0009_transacao_legacy_fatura_columns"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
