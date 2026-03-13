import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from usuarios.models import Usuario
from contas.models import Conta
from categorias.models import Categoria
from transacoes.models import Transacao


class Command(BaseCommand):
    help = "Gera transações de teste para desenvolvimento"

    def handle(self, *args, **kwargs):

        usuario = Usuario.objects.last()
        conta = Conta.objects.filter(usuario=usuario).first()

        categorias = list(Categoria.objects.filter(usuario=usuario))

        if not usuario or not conta or not categorias:
            self.stdout.write(self.style.ERROR(
                "É necessário existir pelo menos: usuário, conta e categorias."
            ))
            return

        for i in range(100):

            tipo = random.choice(["receita", "despesa"])

            valor = random.randint(10, 500)

            data = timezone.now().date() - timedelta(days=random.randint(0, 60))

            Transacao.objects.create(
                usuario=usuario,
                conta=conta,
                categoria=random.choice(categorias),
                tipo=tipo,
                valor=valor,
                descricao="Transação de teste",
                data=data
            )

        self.stdout.write(self.style.SUCCESS("100 transações de teste criadas com sucesso."))