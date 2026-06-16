from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_export_backend() -> str:
  backend = getattr(settings, "EXPORT_JOB_BACKEND", "thread").lower()
  if not settings.DEBUG and backend == "thread":
    logger.error(
      "EXPORT_JOB_BACKEND=thread não é permitido em produção; jobs ficarão pending até worker."
    )
    return "pending"
  return backend


def dispatch_export_job(job_id: int) -> None:
  backend = get_export_backend()
  if backend == "sync":
    from relatorios.services.export.backends.sync import dispatch
    dispatch(job_id)
  elif backend == "celery":
    from relatorios.services.export.backends.celery import dispatch
    dispatch(job_id)
  elif backend == "thread":
    from relatorios.services.export.backends.thread import dispatch
    dispatch(job_id)
  else:
    # pending / db_poll — job aguarda worker externo
    logger.info("export.job.pending_dispatch job_id=%s backend=%s", job_id, backend)
