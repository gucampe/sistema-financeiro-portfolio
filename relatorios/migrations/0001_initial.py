# Generated manually for relatórios (orçamento + export jobs)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("categorias", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportRelatorioJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Pendente"), ("ready", "Pronto"), ("error", "Erro")], db_index=True, default="pending", max_length=16)),
                ("filtros_json", models.TextField(default="{}")),
                ("arquivo", models.FileField(blank=True, null=True, upload_to="exports/relatorios/")),
                ("mensagem_erro", models.TextField(blank=True)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
                ("atualizado_em", models.DateTimeField(auto_now=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="export_relatorio_jobs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-criado_em"],
            },
        ),
        migrations.CreateModel(
            name="OrcamentoCategoria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ano", models.PositiveIntegerField()),
                ("mes", models.PositiveSmallIntegerField()),
                ("valor_planejado", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orcamentos",
                        to="categorias.categoria",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="orcamentos_categoria",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Orçamento por categoria",
                "verbose_name_plural": "Orçamentos por categoria",
                "ordering": ["-ano", "-mes", "categoria__nome"],
            },
        ),
        migrations.AddConstraint(
            model_name="orcamentocategoria",
            constraint=models.UniqueConstraint(
                fields=("usuario", "categoria", "ano", "mes"),
                name="relatorios_orcamento_unico_usuario_categoria_ano_mes",
            ),
        ),
    ]
