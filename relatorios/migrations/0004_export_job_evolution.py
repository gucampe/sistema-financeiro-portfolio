# Evolução ExportRelatorioJob → ExportJob (preserva dados existentes)

import uuid

import django.db.models.deletion
import relatorios.models
from django.conf import settings
from django.db import migrations, models


def popular_campos_export_job(apps, schema_editor):
    ExportJob = apps.get_model("relatorios", "ExportJob")
    for job in ExportJob.objects.all():
        if not job.token_download:
            job.token_download = uuid.uuid4()
        if not job.dominio:
            job.dominio = "transacoes"
        if not job.formato:
            job.formato = "csv"
        job.save(update_fields=["token_download", "dominio", "formato"])


class Migration(migrations.Migration):

    dependencies = [
        ("relatorios", "0003_remove_orcamento_vigencia"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="ExportRelatorioJob",
            new_name="ExportJob",
        ),
        migrations.AlterField(
            model_name="exportjob",
            name="usuario",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="export_jobs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="dominio",
            field=models.CharField(
                choices=[
                    ("transacoes", "Transações"),
                    ("contas", "Contas"),
                    ("cartoes", "Cartões"),
                    ("orcamentos", "Orçamentos"),
                    ("investimentos", "Investimentos"),
                    ("relatorio_pdf", "Relatório PDF"),
                ],
                default="transacoes",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="formato",
            field=models.CharField(
                choices=[("csv", "CSV"), ("xlsx", "Excel"), ("pdf", "PDF")],
                default="csv",
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="origem",
            field=models.CharField(
                choices=[("manual", "Manual"), ("scheduled", "Agendado")],
                default="manual",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="nome_arquivo",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="tamanho_bytes",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="linhas_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="tentativas",
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="max_tentativas",
            field=models.SmallIntegerField(default=3),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="task_id",
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="idempotency_key",
            field=models.UUIDField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="erro_interno",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="cancelado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="iniciado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="finalizado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="expira_em",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="exportjob",
            name="token_download",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        migrations.AlterField(
            model_name="exportjob",
            name="arquivo",
            field=models.FileField(
                blank=True,
                null=True,
                upload_to=relatorios.models.export_arquivo_upload_to,
            ),
        ),
        migrations.AlterField(
            model_name="exportjob",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendente"),
                    ("processing", "Processando"),
                    ("ready", "Pronto"),
                    ("error", "Erro"),
                    ("cancelled", "Cancelado"),
                    ("expired", "Expirado"),
                ],
                db_index=True,
                default="pending",
                max_length=16,
            ),
        ),
        migrations.RunPython(popular_campos_export_job, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="exportjob",
            name="token_download",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AddIndex(
            model_name="exportjob",
            index=models.Index(fields=["usuario", "status"], name="relatorios__usuario_50bb73_idx"),
        ),
        migrations.AddIndex(
            model_name="exportjob",
            index=models.Index(fields=["status", "iniciado_em"], name="relatorios__status_326931_idx"),
        ),
    ]
