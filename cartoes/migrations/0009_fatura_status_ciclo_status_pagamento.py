from django.db import migrations, models


def preencher_status_iniciais(apps, schema_editor):
    Fatura = apps.get_model("cartoes", "Fatura")
    for fatura in Fatura.objects.all().only("id", "status"):
        status_legado = fatura.status or "aberta"
        fatura.status_ciclo = status_legado
        fatura.status_pagamento = "pendente"
        fatura.save(update_fields=["status_ciclo", "status_pagamento"])


class Migration(migrations.Migration):
    dependencies = [
        ("cartoes", "0008_sqlite_fatura_valor_total_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="fatura",
            name="status_ciclo",
            field=models.CharField(
                choices=[("aberta", "Aberta"), ("fechada", "Fechada")],
                default="aberta",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="fatura",
            name="status_pagamento",
            field=models.CharField(
                choices=[
                    ("pendente", "Pendente"),
                    ("parcial", "Parcial"),
                    ("pago", "Pago"),
                    ("atrasado", "Atrasado"),
                ],
                default="pendente",
                max_length=10,
            ),
        ),
        migrations.RunPython(preencher_status_iniciais, migrations.RunPython.noop),
    ]
