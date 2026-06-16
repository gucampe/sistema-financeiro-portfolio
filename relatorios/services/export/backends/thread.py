from __future__ import annotations

import threading

from relatorios.services.export.jobs import executar_job


def dispatch(job_id: int) -> None:
  from django.db import connections

  connections.close_all()
  t = threading.Thread(target=executar_job, args=(job_id,), daemon=True)
  t.start()
