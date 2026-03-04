from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("contas", "0001_initial"),
        ("transacoes", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="transacao",
            name="conta",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transacoes",
                to="contas.conta",
            ),
        ),
        migrations.AlterField(
            model_name="transacao",
            name="tipo",
            field=models.CharField(
                max_length=10,
                choices=(
                    ("receita", "Receita"),
                    ("despesa", "Despesa"),
                    ("ajuste", "Ajuste"),
                ),
            ),
        ),
    ]

