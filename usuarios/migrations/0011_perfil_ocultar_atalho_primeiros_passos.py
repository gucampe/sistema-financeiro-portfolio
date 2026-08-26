from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0010_cadastro_primeiros_donos"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="ocultar_atalho_primeiros_passos",
            field=models.BooleanField(
                default=False,
                help_text="Não mostra o atalho flutuante no dashboard, em qualquer dispositivo.",
                verbose_name="Ocultar atalho de primeiros passos",
            ),
        ),
    ]
