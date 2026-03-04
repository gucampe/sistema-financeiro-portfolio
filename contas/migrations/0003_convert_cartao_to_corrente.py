# Generated manually - converte contas com tipo "cartao" para "corrente" antes de remover o choice

from django.db import migrations


def cartao_para_corrente(apps, schema_editor):
    Conta = apps.get_model("contas", "Conta")
    Conta.objects.filter(tipo="cartao").update(tipo="corrente")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("contas", "0002_saldo_inicial_para_ajuste"),
    ]

    operations = [
        migrations.RunPython(cartao_para_corrente, noop),
    ]
