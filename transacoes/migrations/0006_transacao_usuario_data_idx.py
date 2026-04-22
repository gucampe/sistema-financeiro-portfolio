from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("transacoes", "0005_add_ofx_fitid"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="transacao",
            index=models.Index(fields=["usuario", "data"], name="transacao_usuario_data_idx"),
        ),
    ]
