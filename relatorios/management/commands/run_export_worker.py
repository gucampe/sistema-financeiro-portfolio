from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from relatorios.models import ExportJob
from relatorios.services.export.jobs import executar_job


class Command(BaseCommand):
  help = "Worker DB-polled: processa jobs de exportação pendentes."

  def add_arguments(self, parser):
    parser.add_argument("--once", action="store_true", help="Processa um lote e encerra.")
    parser.add_argument("--sleep", type=int, default=5, help="Intervalo entre ciclos (segundos).")

  def handle(self, *args, **options):
    once = options["once"]
    sleep_s = options["sleep"]
    self.stdout.write("Export worker iniciado (DB-polled).")

    while True:
      job = (
        ExportJob.objects.filter(status=ExportJob.STATUS_PENDING)
        .order_by("criado_em")
        .first()
      )
      if job:
        executar_job(job.pk)
        continue
      if once:
        break
      time.sleep(sleep_s)
