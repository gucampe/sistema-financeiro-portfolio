from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from relatorios.models import ExportJob
from relatorios.services.export.observability import log_export_event


def limpar_exports_expirados() -> dict[str, int]:
  now = timezone.now()
  stats = {"expired": 0, "deleted_files": 0}

  ready_expired = ExportJob.objects.filter(
    status=ExportJob.STATUS_READY,
    expira_em__lt=now,
  )
  for job in ready_expired:
    if job.arquivo:
      job.arquivo.delete(save=False)
      stats["deleted_files"] += 1
    job.status = ExportJob.STATUS_EXPIRED
    job.save(update_fields=["status", "atualizado_em"])
    stats["expired"] += 1
    log_export_event("expired_cleaned", job)

  old_jobs = ExportJob.objects.filter(
    status__in=(
      ExportJob.STATUS_ERROR,
      ExportJob.STATUS_CANCELLED,
      ExportJob.STATUS_EXPIRED,
    ),
    atualizado_em__lt=now - timedelta(days=30),
  )
  for job in old_jobs[:200]:
    if job.arquivo:
      job.arquivo.delete(save=False)
      stats["deleted_files"] += 1
    job.delete()

  return stats
