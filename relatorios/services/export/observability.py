from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def log_export_event(event: str, job, *, extra: dict | None = None) -> None:
  payload = {
    "event": f"export.job.{event}",
    "job_id": job.pk,
    "user_id": job.usuario_id,
    "dominio": job.dominio,
    "formato": job.formato,
    "status": job.status,
    "tentativas": job.tentativas,
  }
  if extra:
    payload.update(extra)
  logger.info("export event", extra=payload)
