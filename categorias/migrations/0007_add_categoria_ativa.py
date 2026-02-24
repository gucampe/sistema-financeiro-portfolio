# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('categorias', '0006_alter_categoria_cor'),
    ]

    operations = [
        migrations.AddField(
            model_name='categoria',
            name='ativa',
            field=models.BooleanField(db_index=True, default=True),
        ),
    ]
