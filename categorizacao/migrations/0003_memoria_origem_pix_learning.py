# Generated manually for PIX learning architecture

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("categorizacao", "0002_llm_request_log_and_perfil_optin"),
    ]

    operations = [
        migrations.AddField(
            model_name="memoriamerchantusuario",
            name="origem",
            field=models.CharField(
                choices=[
                    ("human", "Humano confirmado"),
                    ("llm_pending", "Pendente LLM"),
                    ("import_passive", "Import passivo"),
                ],
                default="human",
                max_length=20,
            ),
        ),
    ]
