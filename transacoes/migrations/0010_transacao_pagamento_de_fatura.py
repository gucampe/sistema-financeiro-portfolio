from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cartoes", "0009_fatura_status_ciclo_status_pagamento"),
        ("transacoes", "0009_transacao_legacy_fatura_columns"),
    ]

    operations = [
        migrations.AddField(
            model_name="transacao",
            name="pagamento_de_fatura",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pagamentos",
                to="cartoes.fatura",
            ),
        ),
    ]
