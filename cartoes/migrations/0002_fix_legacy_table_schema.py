from django.db import migrations


def fix_legacy_cartoes_table(apps, schema_editor):
    connection = schema_editor.connection
    vendor = connection.vendor
    table_name = "cartoes_cartao"

    if vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=%s",
            [table_name],
        )
        if not cursor.fetchone():
            return

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]

        # Se já está no schema novo, não faz nada.
        if "usuario_id" in columns and "conta_padrao_id" in columns:
            return

        cursor.execute("SELECT COUNT(*) FROM usuarios_usuario")
        usuarios_count = cursor.fetchone()[0]

        cursor.execute("ALTER TABLE cartoes_cartao RENAME TO cartoes_cartao_old")
        cursor.execute(
            """
            CREATE TABLE cartoes_cartao (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                nome varchar(100) NOT NULL,
                icone varchar(50) NOT NULL DEFAULT 'bank',
                limite decimal NOT NULL DEFAULT 0,
                dia_fechamento smallint unsigned NOT NULL,
                dia_vencimento smallint unsigned NOT NULL,
                ativa bool NOT NULL DEFAULT 1,
                criada_em datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizada_em datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                conta_padrao_id bigint NOT NULL REFERENCES contas_conta(id) DEFERRABLE INITIALLY DEFERRED,
                usuario_id bigint NOT NULL REFERENCES usuarios_usuario(id) DEFERRABLE INITIALLY DEFERRED
            )
            """
        )

        # Migra dados antigos se existir usuário para vincular.
        if usuarios_count > 0:
            cursor.execute(
                """
                INSERT INTO cartoes_cartao (
                    id, nome, icone, limite, dia_fechamento, dia_vencimento,
                    ativa, criada_em, atualizada_em, conta_padrao_id, usuario_id
                )
                SELECT
                    id,
                    nome,
                    COALESCE(icone, 'bank'),
                    COALESCE(limite, 0),
                    dia_fechamento,
                    dia_vencimento,
                    1,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    conta_pagamento_id,
                    (SELECT id FROM usuarios_usuario ORDER BY id ASC LIMIT 1)
                FROM cartoes_cartao_old
                """
            )

        cursor.execute("DROP TABLE cartoes_cartao_old")
        cursor.execute(
            "CREATE UNIQUE INDEX cartoes_cartao_usuario_id_nome_uniq ON cartoes_cartao (usuario_id, nome)"
        )
        cursor.execute(
            "CREATE INDEX cartoes_cartao_conta_padrao_id_idx ON cartoes_cartao (conta_padrao_id)"
        )
        cursor.execute(
            "CREATE INDEX cartoes_cartao_usuario_id_idx ON cartoes_cartao (usuario_id)"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("cartoes", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fix_legacy_cartoes_table, migrations.RunPython.noop),
    ]
