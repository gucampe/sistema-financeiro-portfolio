"""Envia evento de teste ao Sentry (validar SENTRY_DSN em produção)."""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Envia exceção de teste ao Sentry para validar observabilidade."

    def handle(self, *args, **options):
        from config.observability import init_sentry

        init_sentry()
        try:
            import sentry_sdk

            if not sentry_sdk.Hub.current.client:
                self.stderr.write("SENTRY_DSN não configurado ou inválido.")
                return
            sentry_sdk.capture_message("GranaGo: teste de observabilidade (manage.py test_sentry)")
            self.stdout.write(self.style.SUCCESS("Evento enviado ao Sentry."))
        except ImportError:
            self.stderr.write("sentry-sdk não instalado.")
