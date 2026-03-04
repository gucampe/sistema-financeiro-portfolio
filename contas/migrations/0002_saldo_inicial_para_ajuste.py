from decimal import Decimal

from django.db import migrations
from django.utils import timezone


def criar_ajustes_de_saldo(apps, schema_editor):
    Conta = apps.get_model("contas", "Conta")
    Transacao = apps.get_model("transacoes", "Transacao")
    Categoria = apps.get_model("categorias", "Categoria")

    hoje = timezone.now().date()

    contas = Conta.objects.exclude(saldo_inicial=Decimal("0.00"))
    for conta in contas.select_related("usuario"):
        usuario = conta.usuario

        categoria_ajuste, _ = Categoria.objects.get_or_create(
            usuario=None,
            padrao=True,
            tipo="receita",
            nome="Ajustes de saldo",
            defaults={
                "descricao": "Ajustes automáticos de saldo de contas",
                "cor": "#6B7280",
                "icone": "fa-ellipsis-h",
                "ativa": True,
            },
        )

        Transacao.objects.create(
            usuario=usuario,
            conta=conta,
            tipo="ajuste",
            valor=conta.saldo_inicial,
            descricao="Saldo inicial",
            data=hoje,
            categoria=categoria_ajuste,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("contas", "0001_initial"),
        ("transacoes", "0003_conta_ajuste"),
        ("categorias", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(criar_ajustes_de_saldo, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="conta",
            name="saldo_inicial",
        ),
    ]

