from django.db import migrations, models
import django.db.models.deletion


def preencher_conta_nula(apps, schema_editor):
    """Atribui a primeira conta do usuário às transações que estão com conta NULL."""
    Transacao = apps.get_model("transacoes", "Transacao")
    Conta = apps.get_model("contas", "Conta")
    for transacao in Transacao.objects.filter(conta__isnull=True).select_related("usuario"):
        primeira_conta = Conta.objects.filter(usuario=transacao.usuario).order_by("id").first()
        if primeira_conta:
            transacao.conta = primeira_conta
            transacao.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("contas", "0001_initial"),
        ("transacoes", "0003_conta_ajuste"),
    ]

    operations = [
        migrations.RunPython(preencher_conta_nula, noop),
        migrations.AlterField(
            model_name="transacao",
            name="conta",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transacoes",
                to="contas.conta",
            ),
        ),
    ]
