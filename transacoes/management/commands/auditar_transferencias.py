"""
Audita integridade de transferências entre contas.

Uso:
  python manage.py auditar_transferencias
  python manage.py auditar_transferencias --email user@example.com
  python manage.py auditar_transferencias --fail-on-error
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from transacoes.audit_transferencias import auditar_integridade_transferencias

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Valida transferências: 2 pernas (origem+destino), sem órfãos/duplicidades "
        "e patrimônio/saldos consistentes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="",
            help="Limita a auditoria a um usuário (e-mail).",
        )
        parser.add_argument(
            "--fail-on-error",
            action="store_true",
            help="Exit code 1 se houver problemas.",
        )
        parser.add_argument(
            "--sem-patrimonio",
            action="store_true",
            help="Não verifica saldos/patrimônio (só estrutura dos pares).",
        )

    def handle(self, *args, **options):
        usuario = None
        email = (options.get("email") or "").strip()
        if email:
            usuario = User.objects.filter(email__iexact=email).first()
            if usuario is None:
                raise CommandError(f"Usuário não encontrado: {email}")

        resultado = auditar_integridade_transferencias(
            usuario=usuario,
            verificar_patrimonio=not options["sem_patrimonio"],
        )

        self.stdout.write(
            f"Usuários auditados: {resultado.usuarios_auditados} | "
            f"pares OK: {resultado.transfer_ids_ok} | "
            f"problemas: {len(resultado.problemas)}"
        )

        for p in resultado.problemas:
            self.stdout.write(
                self.style.ERROR(
                    f"[{p.codigo}] user={p.usuario_id} transfer_id={p.transfer_id} — {p.detalhe}"
                )
            )

        if resultado.ok:
            self.stdout.write(self.style.SUCCESS("Auditoria OK — nenhuma inconsistência."))
            return

        self.stdout.write(
            self.style.WARNING(f"Auditoria encontrou {len(resultado.problemas)} problema(s).")
        )
        if options["fail_on_error"]:
            raise CommandError("Integridade de transferências comprometida.")
