import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Cria ou promove um superusuário (login por e-mail)."

    def add_arguments(self, parser):
        parser.add_argument("--email", type=str, help="E-mail do superusuário.")
        parser.add_argument("--nome", type=str, help="Nome completo do superusuário.")
        parser.add_argument("--password", type=str, help="Senha do superusuário.")
        parser.add_argument(
            "--noinput",
            action="store_true",
            help="Não solicitar dados interativamente (exige --email, --nome e --password).",
        )
        parser.add_argument(
            "--atualizar",
            action="store_true",
            help="Se o e-mail já existir, promove a superusuário e atualiza a senha quando informada.",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = options.get("email")
        nome = options.get("nome")
        password = options.get("password")
        noinput = options["noinput"]
        atualizar = options["atualizar"]

        if noinput and not all([email, nome, password]):
            raise CommandError("Com --noinput, informe --email, --nome e --password.")

        if not email:
            email = input("E-mail: ").strip()
        if not nome:
            nome = input("Nome completo: ").strip()

        if not email:
            raise CommandError("O e-mail é obrigatório.")
        if not nome:
            raise CommandError("O nome é obrigatório.")

        from usuarios.utils import normalizar_email

        email = normalizar_email(email)
        existente = User.objects.filter(email=email).first()
        if existente is None:
            existente = User.objects.filter(email__iexact=email).first()

        if existente:
            if not atualizar:
                raise CommandError(
                    f"Já existe um usuário com o e-mail {email}. "
                    "Use --atualizar para promovê-lo a superusuário."
                )
            return self._promover_existente(existente, nome, password, noinput)

        if not password:
            if noinput:
                raise CommandError("Com --noinput, informe --password.")
            password = self._ler_senha()

        User.objects.create_superuser(email=email, password=password, nome=nome)
        self.stdout.write(self.style.SUCCESS(f"Superusuário criado: {email}"))

    def _promover_existente(self, usuario, nome, password, noinput):
        usuario.nome = nome
        usuario.is_staff = True
        usuario.is_superuser = True
        usuario.is_active = True

        if password:
            usuario.set_password(password)
        elif not noinput:
            if self._confirmar("Atualizar a senha?"):
                usuario.set_password(self._ler_senha())

        usuario.save()
        self.stdout.write(self.style.SUCCESS(f"Superusuário atualizado: {usuario.email}"))

    def _ler_senha(self) -> str:
        while True:
            senha = getpass.getpass("Senha: ")
            confirmacao = getpass.getpass("Confirme a senha: ")
            if senha != confirmacao:
                self.stderr.write("As senhas não coincidem. Tente novamente.")
                continue
            if not senha:
                raise CommandError("A senha não pode ser vazia.")
            return senha

    def _confirmar(self, mensagem: str) -> bool:
        resposta = input(f"{mensagem} [s/N]: ").strip().lower()
        return resposta in ("s", "sim", "y", "yes")
