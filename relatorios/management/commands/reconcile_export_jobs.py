"""Reconcilia export jobs pending órfãos (cron ou pós-incidente Celery)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from relatorios.models import ExportJob
from relatorios.services.export.jobs import _reconciliar_jobs_pendentes


class Command(BaseCommand):
    help = "Re-despacha ou finaliza export jobs pending órfãos."

    def handle(self, *args, **options):
        User = get_user_model()
        user_ids = (
            ExportJob.objects.filter(status=ExportJob.STATUS_PENDING)
            .values_list("usuario_id", flat=True)
            .distinct()
        )
        count = 0
        for uid in user_ids:
            user = User.objects.filter(pk=uid).first()
            if user:
                _reconciliar_jobs_pendentes(user)
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Reconciliados jobs de {count} usuário(s)."))
