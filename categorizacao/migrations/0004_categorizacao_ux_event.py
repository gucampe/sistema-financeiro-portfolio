# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("categorizacao", "0003_memoria_origem_pix_learning"),
    ]

    operations = [
        migrations.CreateModel(
            name="CategorizacaoUXEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "evento",
                    models.CharField(
                        choices=[
                            ("ia_click", "Clique categorizar IA"),
                            ("ia_complete", "Categorização concluída"),
                            ("ia_cancel", "Cancelado"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "contexto",
                    models.CharField(
                        choices=[
                            ("import_ofx", "Import OFX"),
                            ("import_planilha", "Import planilha"),
                            ("manual", "Manual"),
                        ],
                        default="manual",
                        max_length=30,
                    ),
                ),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="categorizacao_ux_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento UX categorização",
                "verbose_name_plural": "Eventos UX categorização",
                "ordering": ["-criado_em"],
                "indexes": [
                    models.Index(fields=["evento", "criado_em"], name="cat_ux_evt_dt_idx"),
                ],
            },
        ),
    ]
