# Generated migration — evolução OrcamentoCategoria para vigência recorrente

from collections import defaultdict

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def consolidar_orcamentos_mensais(apps, schema_editor):
    OrcamentoCategoria = apps.get_model("relatorios", "OrcamentoCategoria")
    grupos: dict[tuple[int, int], list] = defaultdict(list)
    for o in OrcamentoCategoria.objects.all().order_by("ano", "mes"):
        grupos[(o.usuario_id, o.categoria_id)].append(o)

    for items in grupos.values():
        primeiro = items[0]
        ultimo = items[-1]
        inicio_ano = primeiro.ano
        inicio_mes = primeiro.mes
        for o in items[:-1]:
            o.delete()
        ultimo.inicio_ano = inicio_ano
        ultimo.inicio_mes = inicio_mes
        ultimo.ativo = True
        ultimo.save(update_fields=["inicio_ano", "inicio_mes", "ativo"])


class Migration(migrations.Migration):

    dependencies = [
        ("relatorios", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="orcamentocategoria",
            name="relatorios_orcamento_unico_usuario_categoria_ano_mes",
        ),
        migrations.AddField(
            model_name="orcamentocategoria",
            name="ativo",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="orcamentocategoria",
            name="inicio_ano",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="orcamentocategoria",
            name="inicio_mes",
            field=models.PositiveSmallIntegerField(null=True),
        ),
        migrations.AddField(
            model_name="orcamentocategoria",
            name="fim_ano",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orcamentocategoria",
            name="fim_mes",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orcamentocategoria",
            name="criado_em",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="orcamentocategoria",
            name="atualizado_em",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(consolidar_orcamentos_mensais, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="orcamentocategoria",
            name="ano",
        ),
        migrations.RemoveField(
            model_name="orcamentocategoria",
            name="mes",
        ),
        migrations.AlterField(
            model_name="orcamentocategoria",
            name="inicio_ano",
            field=models.PositiveIntegerField(),
        ),
        migrations.AlterField(
            model_name="orcamentocategoria",
            name="inicio_mes",
            field=models.PositiveSmallIntegerField(),
        ),
        migrations.AddConstraint(
            model_name="orcamentocategoria",
            constraint=models.UniqueConstraint(
                fields=("usuario", "categoria"),
                name="relatorios_orcamento_unico_usuario_categoria",
            ),
        ),
        migrations.AlterModelOptions(
            name="orcamentocategoria",
            options={
                "ordering": ["categoria__nome"],
                "verbose_name": "Orçamento por categoria",
                "verbose_name_plural": "Orçamentos por categoria",
            },
        ),
    ]
