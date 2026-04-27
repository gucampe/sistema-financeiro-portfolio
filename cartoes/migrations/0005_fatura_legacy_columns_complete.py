"""
Completa schema de cartoes_fatura quando a tabela foi criada de forma parcial,
adicionando colunas do model Fatura e preenchendo linhas existentes (ciclo “atual” por data de hoje).
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta

from django.db import migrations
from django.utils import timezone


def _date_clamped(year: int, month: int, day_num: int) -> date:
    last = monthrange(year, month)[1]
    return date(year, month, min(day_num, last))


def _intervalo_compras_para_data(dia_fechamento: int, d: date) -> tuple[date, date]:
    df = dia_fechamento
    c_m = _date_clamped(d.year, d.month, df)
    if d <= c_m:
        if d.month == 1:
            py, pm = d.year - 1, 12
        else:
            py, pm = d.year, d.month - 1
        c_prev = _date_clamped(py, pm, df)
        inicio = c_prev + timedelta(days=1)
        fim = c_m
    else:
        inicio = c_m + timedelta(days=1)
        if d.month == 12:
            ny, nm = d.year + 1, 1
        else:
            ny, nm = d.year, d.month + 1
        fim = _date_clamped(ny, nm, df)
    return inicio, fim


def _data_vencimento_para_fechamento(dia_vencimento: int, data_fechamento: date) -> date:
    dv = dia_vencimento
    cand = _date_clamped(data_fechamento.year, data_fechamento.month, dv)
    if cand > data_fechamento:
        return cand
    if data_fechamento.month == 12:
        ny, nm = data_fechamento.year + 1, 1
    else:
        ny, nm = data_fechamento.year, data_fechamento.month + 1
    return _date_clamped(ny, nm, dv)


def _competencia_para_vencimento(data_vencimento: date) -> date:
    return date(data_vencimento.year, data_vencimento.month, 1)


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
    table = Fatura._meta.db_table
    cols = _column_names(schema_editor, table)
    q = schema_editor.quote_name
    qt = q(table)
    conn = schema_editor.connection

    # Tipos SQLite alinhados ao que o Django costuma gerar; PostgreSQL com IF NOT EXISTS.
    if conn.vendor == "sqlite":
        specs = {
            "competencia": "date NULL",
            "data_fechamento": "date NULL",
            "data_vencimento": "date NULL",
            "data_inicio_compras": "date NULL",
            "data_fim_compras": "date NULL",
            "valor_total": "NUMERIC(12, 2) NULL",
            "status": "varchar(10) NOT NULL DEFAULT 'aberta'",
            "criada_em": "datetime NULL",
            "atualizada_em": "datetime NULL",
        }
    else:
        specs = {
            "competencia": "date NULL",
            "data_fechamento": "date NULL",
            "data_vencimento": "date NULL",
            "data_inicio_compras": "date NULL",
            "data_fim_compras": "date NULL",
            "valor_total": "numeric(12, 2) NULL",
            "status": "varchar(10) NOT NULL DEFAULT 'aberta'",
            "criada_em": "timestamp with time zone NULL",
            "atualizada_em": "timestamp with time zone NULL",
        }

    missing = [name for name in specs if name not in cols]
    if not missing:
        return

    with conn.cursor() as cursor:
        if conn.vendor == "sqlite":
            for name in missing:
                cursor.execute(f"ALTER TABLE {qt} ADD COLUMN {name} {specs[name]}")
        else:
            for name in missing:
                cursor.execute(
                    f"ALTER TABLE {qt} ADD COLUMN IF NOT EXISTS {q(name)} {specs[name]}"
                )

    now = timezone.now()
    for f in Fatura.objects.all().iterator():
        if f.competencia is not None:
            continue
        try:
            cartao = Cartao.objects.get(pk=f.cartao_id)
        except Cartao.DoesNotExist:
            continue
        ref = date.today()
        inicio, fim = _intervalo_compras_para_data(cartao.dia_fechamento, ref)
        dv = _data_vencimento_para_fechamento(cartao.dia_vencimento, fim)
        comp = _competencia_para_vencimento(dv)
        criada = getattr(f, "criada_em", None) or now
        atualizada = getattr(f, "atualizada_em", None) or now
        Fatura.objects.filter(pk=f.pk).update(
            competencia=comp,
            data_fechamento=fim,
            data_vencimento=dv,
            data_inicio_compras=inicio,
            data_fim_compras=fim,
            status="aberta",
            criada_em=criada,
            atualizada_em=atualizada,
        )

    # Evita falha ao criar índice único se houver duplicatas (cartao, competencia).
    with conn.cursor() as cursor:
        if conn.vendor == "sqlite":
            cursor.execute(
                f"""
                DELETE FROM {qt}
                WHERE rowid IN (
                    SELECT f1.rowid FROM {qt} AS f1
                    INNER JOIN {qt} AS f2
                      ON f2.cartao_id = f1.cartao_id
                     AND f2.competencia IS NOT DISTINCT FROM f1.competencia
                     AND f2.rowid < f1.rowid
                )
                """
            )
        else:
            cursor.execute(
                f"""
                DELETE FROM {qt} AS f1
                USING {qt} AS f2
                WHERE f1.cartao_id = f2.cartao_id
                  AND f1.competencia IS NOT DISTINCT FROM f2.competencia
                  AND f1.id > f2.id
                """
            )

    with conn.cursor() as cursor:
        if conn.vendor == "sqlite":
            cursor.execute(
                f"CREATE UNIQUE INDEX IF NOT EXISTS cartoes_fatura_uniq_cartao_competencia "
                f"ON {qt} (cartao_id, competencia)"
            )
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS cartoes_fatura_cartao_venc_idx "
                f"ON {qt} (cartao_id, data_vencimento)"
            )
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS cartoes_fatura_user_venc_idx "
                f"ON {qt} (usuario_id, data_vencimento)"
            )
        else:
            cursor.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS cartoes_fatura_uniq_cartao_competencia
                ON {qt} (cartao_id, competencia)
                """
            )
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS cartoes_fatura_cartao_venc_idx
                ON {qt} (cartao_id, data_vencimento)
                """
            )
            cursor.execute(
                f"""
                CREATE INDEX IF NOT EXISTS cartoes_fatura_user_venc_idx
                ON {qt} (usuario_id, data_vencimento)
                """
            )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("cartoes", "0004_fatura_usuario_id_schema"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
