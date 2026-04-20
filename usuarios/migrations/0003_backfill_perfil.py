from django.db import migrations


def forwards(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    Perfil = apps.get_model("usuarios", "Perfil")
    for u in Usuario.objects.all():
        Perfil.objects.get_or_create(usuario=u)


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0002_perfil"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
