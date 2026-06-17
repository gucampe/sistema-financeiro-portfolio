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

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="teste4@teste.com",
            help="E-mail do usuário que receberá as transações de teste",
        )
        parser.add_argument(
            "--quantidade",
            type=int,
            default=100,
            help="Número de transações a criar (padrão: 100)",
        )

    def handle(self, *args, **kwargs):
        email = kwargs["email"]
        quantidade = kwargs["quantidade"]

        usuario = Usuario.objects.filter(email=email).first()
        if not usuario:
            usuario = Usuario.objects.last()
        conta = Conta.objects.filter(usuario=usuario, ativa=True).first()

        categorias = list(Categoria.objects.filter(usuario=usuario))

        if not usuario or not conta or not categorias:
            self.stdout.write(self.style.ERROR(
                f"É necessário existir pelo menos: usuário ({email}), conta e categorias."
            ))
            return

        for i in range(quantidade):

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

        self.stdout.write(self.style.SUCCESS(
            f"{quantidade} transações de teste criadas com sucesso para {usuario.email}."
        ))
        