from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0003_backfill_perfil"),
    ]

    operations = [
        migrations.AlterField(
            model_name="perfil",
            name="ocultar_valores_dashboard",
            field=models.BooleanField(
                default=False,
                help_text="Mascara valores sensíveis na tela inicial.",
                verbose_name="Ocultar valores nos relatórios",
            ),
        ),
    ]
