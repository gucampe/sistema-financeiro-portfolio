"""
Corrige DBs onde transacoes_transacao não tem data_competencia / fatura_id
(migration 0008 faked ou schema parcial).
"""

from django.db import migrations


def _column_names(schema_editor, table: str) -> set:
    conn = schema_editor.connection
    q = schema_editor.quote_name
    with conn.cursor() as cursor:
        if conn.vendor == "sqlite":
            cursor.execute("PRAGMA table_info(%s)" % q(table))
            return {row[1] for row in cursor.fetchall()}
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s
            """,
            [table],
        )
        return {row[0] for row in cursor.fetchall()}


def forwards(apps, schema_editor):
    Transacao = apps.get_model("transacoes", "Transacao")
    Fatura = apps.get_model("cartoes", "Fatura")
    table = Transacao._meta.db_table
    fatura_table = schema_editor.quote_name(Fatura._meta.db_table)
    cols = _column_names(schema_editor, table)
    q = schema_editor.quote_name
    qt = q(table)
    conn = schema_editor.connection

    with conn.cursor() as cursor:
        if "data_competencia" not in cols:
            if conn.vendor == "sqlite":
                cursor.execute(f"ALTER TABLE {qt} ADD COLUMN data_competencia date NULL")
            else:
                cursor.execute(
                    f"ALTER TABLE {qt} ADD COLUMN IF NOT EXISTS data_competencia date NULL"
                )

        if "fatura_id" not in cols:
            if conn.vendor == "sqlite":
                cursor.execute(
                    f"ALTER TABLE {qt} ADD COLUMN fatura_id bigint NULL REFERENCES {fatura_table} (id)"
                )
            else:
                cursor.execute(
                    f"ALTER TABLE {qt} ADD COLUMN IF NOT EXISTS fatura_id bigint NULL "
                    f"REFERENCES {fatura_table} (id) DEFERRABLE INITIALLY DEFERRED"
                )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("transacoes", "0008_transacao_data_competencia_transacao_fatura"),
        ("cartoes", "0003_fatura"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
