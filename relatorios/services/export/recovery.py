from __future__ import annotations

import logging

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from relatorios.models import ExportJob
from relatorios.services.export.dispatch import dispatch_export_job
from relatorios.services.export.observability import log_export_event

logger = logging.getLogger(__name__)


def _timeout_seconds(job: ExportJob) -> int:
  if job.formato == ExportJob.FORMATO_PDF or job.dominio == ExportJob.DOMINIO_RELATORIO_PDF:
    return int(getattr(settings, "EXPORT_JOB_TIMEOUT_PDF", 300))
  return int(getattr(settings, "EXPORT_JOB_TIMEOUT_CSV", 180))


def recuperar_jobs_travados() -> dict[str, int]:
  now = timezone.now()
  stats = {"requeued": 0, "failed": 0, "redispatched": 0}

  stuck = ExportJob.objects.filter(status=ExportJob.STATUS_PROCESSING)
  for job in stuck:
    if not job.iniciado_em:
      continue
    elapsed = (now - job.iniciado_em).total_seconds()
    if elapsed < _timeout_seconds(job):
      continue
    if job.tentativas < job.max_tentativas:
      job.status = ExportJob.STATUS_PENDING
      job.iniciado_em = None
      job.save(update_fields=["status", "iniciado_em", "atualizado_em"])
      dispatch_export_job(job.pk)
      stats["requeued"] += 1
      log_export_event("stuck_recovered", job)
    else:
      job.status = ExportJob.STATUS_ERROR
      job.mensagem_erro = "Falha ao gerar exportação."
      job.erro_interno = "Timeout na execução."
      job.finalizado_em = now
      job.save(
        update_fields=[
          "status",
          "mensagem_erro",
          "erro_interno",
          "finalizado_em",
          "atualizado_em",
        ]
      )
      stats["failed"] += 1
      log_export_event("stuck_failed", job)

  stale_pending = ExportJob.objects.filter(
    status=ExportJob.STATUS_PENDING,
  ).filter(
    models.Q(criado_em__lt=now - timedelta(hours=1), tentativas=0)
    | models.Q(tentativas__gt=0, erro_interno__gt=""),
  )
  for job in stale_pending[:50]:
    dispatch_export_job(job.pk)
    stats["redispatched"] += 1

  return stats
