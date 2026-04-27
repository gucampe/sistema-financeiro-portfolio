"""
Torna cartoes_fatura.valor_total anulável no SQLite quando o DDL legado (ex.: após
0006) manteve NOT NULL — o model Fatura tem null=True e get_or_create não envia o campo.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import migrations

if TYPE_CHECKING:
    from django.db.backends.base.schema import BaseDatabaseSchemaEditor

_TMP = "valor_total__dj_nullable_tmp"


def forwards(apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    conn = schema_editor.connection
    if conn.vendor != "sqlite":
        return

    q = schema_editor.quote_name
    t = q("cartoes_fatura")
    tmp = q(_TMP)

    with conn.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({t})")
        rows = cursor.fetchall()
        names = [r[1] for r in rows]
        if _TMP in names:
            cursor.execute(f"ALTER TABLE {t} DROP COLUMN {tmp}")
            cursor.execute(f"PRAGMA table_info({t})")
            rows = cursor.fetchall()

        col = next((r for r in rows if r[1] == "valor_total"), None)
        if col is None:
            return
        # (cid, name, type, notnull, dflt_value, pk)
        if col[3] != 1:
            return

        vt = q("valor_total")
        cursor.execute(f"ALTER TABLE {t} ADD COLUMN {tmp} NUMERIC(12, 2) NULL")
        cursor.execute(f"UPDATE {t} SET {tmp} = {vt}")
        cursor.execute(f"ALTER TABLE {t} DROP COLUMN {vt}")
        cursor.execute(f"ALTER TABLE {t} ADD COLUMN {vt} NUMERIC(12, 2) NULL")
        cursor.execute(f"UPDATE {t} SET {vt} = {tmp}")
        cursor.execute(f"ALTER TABLE {t} DROP COLUMN {tmp}")


def backwards(apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("cartoes", "0007_sqlite_fatura_legacy_data_inicio_fim"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
