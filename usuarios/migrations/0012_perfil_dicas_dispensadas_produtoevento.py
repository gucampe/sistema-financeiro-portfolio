from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0011_perfil_ocultar_atalho_primeiros_passos"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="dicas_dispensadas",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Mapa id → última versão dispensada. Ex.: {"cartao": 1}.',
                verbose_name="Dicas de primeiro uso dispensadas",
            ),
        ),
        migrations.CreateModel(
            name="ProdutoEvento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("evento", models.CharField(db_index=True, max_length=48)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="produto_eventos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Evento de produto",
                "verbose_name_plural": "Eventos de produto",
                "ordering": ["-criado_em"],
            },
        ),
        migrations.AddIndex(
            model_name="produtoevento",
            index=models.Index(fields=["evento", "criado_em"], name="usuarios_prod_evt_dt"),
        ),
        migrations.AddConstraint(
            model_name="produtoevento",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    evento__in=(
                        "onboarding_started",
                        "first_account_created",
                        "first_transaction_created",
                        "first_import_started",
                        "first_import_failed",
                        "first_import_completed",
                        "first_dashboard_view_with_data",
                        "first_card_created",
                    )
                ),
                fields=("usuario", "evento"),
                name="usuarios_produtoevento_first_uniq",
            ),
        ),
    ]
