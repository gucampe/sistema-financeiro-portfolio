from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0011_perfil_ocultar_atalho_primeiros_passos"),
    ]

    operations = [
        migrations.AddField(
            model_name="perfil",
            name="tema",
            field=models.CharField(
                choices=[("claro", "Claro"), ("escuro", "Escuro")],
                default="claro",
                help_text="Aparência do aplicativo. O modo escuro só entra se você escolher.",
                max_length=8,
                verbose_name="Tema",
            ),
        ),
    ]
