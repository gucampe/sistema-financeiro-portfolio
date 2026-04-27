"""
Remove colunas legadas data_inicio / data_fim em cartoes_fatura (SQLite) quando
ainda existem ao lado de data_inicio_compras / data_fim_compras — o ORM só
preenche as *_compras e o NOT NULL em data_inicio quebrava o INSERT.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import migrations

if TYPE_CHECKING:
    from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def forwards(apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    conn = schema_editor.connection
    if conn.vendor != "sqlite":
        return

    q = schema_editor.quote_name
    t = q("cartoes_fatura")

    with conn.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({t})")
        col_names = [row[1] for row in cursor.fetchall()]

        if "data_inicio" in col_names:
            if "data_inicio_compras" not in col_names:
                cursor.execute(
                    f"ALTER TABLE {t} ADD COLUMN {q('data_inicio_compras')} date NULL"
                )
            cursor.execute(
                f"UPDATE {t} SET {q('data_inicio_compras')} = "
                f"COALESCE({q('data_inicio_compras')}, {q('data_inicio')})"
            )
            cursor.execute(f"ALTER TABLE {t} DROP COLUMN {q('data_inicio')}")

        cursor.execute(f"PRAGMA table_info({t})")
        col_names = [row[1] for row in cursor.fetchall()]

        if "data_fim" in col_names:
            if "data_fim_compras" not in col_names:
                cursor.execute(
                    f"ALTER TABLE {t} ADD COLUMN {q('data_fim_compras')} date NULL"
                )
            cursor.execute(
                f"UPDATE {t} SET {q('data_fim_compras')} = "
                f"COALESCE({q('data_fim_compras')}, {q('data_fim')})"
            )
            cursor.execute(f"ALTER TABLE {t} DROP COLUMN {q('data_fim')}")


def backwards(apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("cartoes", "0006_fix_sqlite_fk_cartoes_cartao_old"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
