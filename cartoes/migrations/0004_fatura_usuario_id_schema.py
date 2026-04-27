"""Corrige DBs onde cartoes_fatura existe sem usuario_id (tabela legada ou migração parcial)."""

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
    Fatura = apps.get_model("cartoes", "Fatura")
    Cartao = apps.get_model("cartoes", "Cartao")
    Usuario = apps.get_model("usuarios", "Usuario")

    table = Fatura._meta.db_table
    cols = _column_names(schema_editor, table)
    if "usuario_id" in cols:
        return

    q = schema_editor.quote_name
    user_table = q(Usuario._meta.db_table)
    cartao_table = q(Cartao._meta.db_table)
    qt = q(table)
    conn = schema_editor.connection

    with conn.cursor() as cursor:
        if conn.vendor == "sqlite":
            cursor.execute(
                f"ALTER TABLE {qt} ADD COLUMN usuario_id bigint NULL REFERENCES {user_table} (id)"
            )
            cursor.execute(
                f"""
                UPDATE {qt}
                SET usuario_id = (
                    SELECT c.usuario_id FROM {cartao_table} AS c WHERE c.id = {qt}.cartao_id
                )
                """
            )
        else:
            cursor.execute(
                f"ALTER TABLE {qt} ADD COLUMN usuario_id bigint NULL REFERENCES {user_table} (id) DEFERRABLE INITIALLY DEFERRED"
            )
            cursor.execute(
                f"""
                UPDATE {qt} AS f
                SET usuario_id = c.usuario_id
                FROM {cartao_table} AS c
                WHERE c.id = f.cartao_id
                """
            )

    index_name = "cartoes_fatura_user_venc_idx"
    with conn.cursor() as cursor:
        if conn.vendor == "sqlite":
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {q(index_name)} ON {qt} (usuario_id, data_vencimento)"
            )
        else:
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS {q(index_name)}
                ON {qt} (usuario_id, data_vencimento)
                """
            )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cartoes", "0003_fatura"),
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
