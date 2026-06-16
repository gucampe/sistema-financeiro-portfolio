from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def dispatch(job_id: int) -> None:
  try:
    from relatorios.tasks import export_job_task

    result = export_job_task.delay(job_id)
    from relatorios.models import ExportJob

    ExportJob.objects.filter(pk=job_id).update(task_id=result.id)
  except Exception:
    logger.exception("Falha ao enfileirar job Celery job_id=%s", job_id)
    raise
