from django.db import migrations

def criar_categorias_padroes(apps, schema_editor):
    Categoria = apps.get_model('categorias', 'Categoria')

    categorias_padroes = [
        "Alimentação", "Assinaturas e serviços", "Bares e restaurantes", "Casa",
        "Compras", "Cuidados pessoais", "Dívidas e empréstimos", "Educação",
        "Família e filhos", "Impostos e Taxas", "Investimentos", "Lazer e hobbies",
        "Mercado", "Outros", "Pets", "Presentes e doações", "Roupas", "Saúde",
        "Trabalho", "Transporte", "Viagem"
    ]

    for nome in categorias_padroes:
        Categoria.objects.get_or_create(nome=nome, usuario=None, defaults={"padrao": True})

def remover_categorias_padroes(apps, schema_editor):
    Categoria = apps.get_model('categorias', 'Categoria')
    Categoria.objects.filter(padrao=True, usuario=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('categorias', '0002_categoria_padrao_alter_categoria_nome_and_more'),
    ]

    operations = [
        migrations.RunPython(criar_categorias_padroes, remover_categorias_padroes)
    ]
