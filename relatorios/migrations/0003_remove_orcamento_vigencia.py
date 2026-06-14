from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("relatorios", "0002_orcamento_vigencia"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="orcamentocategoria",
            name="fim_ano",
        ),
        migrations.RemoveField(
            model_name="orcamentocategoria",
            name="fim_mes",
        ),
        migrations.RemoveField(
            model_name="orcamentocategoria",
            name="inicio_ano",
        ),
        migrations.RemoveField(
            model_name="orcamentocategoria",
            name="inicio_mes",
        ),
    ]
