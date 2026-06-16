from __future__ import annotations

from celery import shared_task
from django.conf import settings


@shared_task(
  bind=True,
  soft_time_limit=int(getattr(settings, "EXPORT_JOB_TIMEOUT_CSV", 180)),
  time_limit=int(getattr(settings, "EXPORT_JOB_TIMEOUT_PDF", 300)),
  acks_late=True,
  reject_on_worker_lost=True,
)
def export_job_task(self, job_id: int) -> None:
  from relatorios.services.export.jobs import executar_job

  executar_job(job_id, task_id=self.request.id)
