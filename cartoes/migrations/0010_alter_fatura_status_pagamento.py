from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cartoes", "0009_fatura_status_ciclo_status_pagamento"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fatura",
            name="status_pagamento",
            field=models.CharField(
                choices=[
                    ("vazia", "Vazia"),
                    ("pendente", "Pendente"),
                    ("parcial", "Parcial"),
                    ("pago", "Pago"),
                    ("atrasado", "Atrasado"),
                ],
                default="pendente",
                max_length=10,
            ),
        ),
    ]
