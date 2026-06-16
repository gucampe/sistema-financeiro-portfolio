from __future__ import annotations

import json
import logging
import traceback
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from relatorios.export.base import ExportContext
from relatorios.export.registry import estimate_linhas, run_export
from relatorios.models import ExportJob
from relatorios.services.export.observability import log_export_event

logger = logging.getLogger(__name__)

RATE_LIMIT_KEY = "export_rate:{user_id}"
CONCURRENT_STATUSES = (
  ExportJob.STATUS_PENDING,
  ExportJob.STATUS_PROCESSING,
)


def _ttl_hours() -> int:
  return int(getattr(settings, "EXPORT_FILE_TTL_HOURS", 72))


def _max_rows_csv() -> int:
  return int(getattr(settings, "EXPORT_MAX_ROWS_CSV", 100_000))


def _max_rows_xlsx() -> int:
  return int(getattr(settings, "EXPORT_MAX_ROWS_XLSX", 15_000))


def _rate_limit_per_hour() -> int:
  return int(getattr(settings, "EXPORT_RATE_LIMIT_PER_HOUR", 10))


def _max_concurrent() -> int:
  return int(getattr(settings, "EXPORT_MAX_CONCURRENT_JOBS", 2))


def _reconciliar_jobs_pendentes(usuario) -> None:
  """Finaliza ou re-despacha jobs pending órfãos (retry sem dispatch ou nunca processados)."""
  from relatorios.services.export.dispatch import dispatch_export_job

  now = timezone.now()
  pendentes = ExportJob.objects.filter(usuario=usuario, status=ExportJob.STATUS_PENDING)
  for job in pendentes:
    if job.tentativas >= job.max_tentativas:
      job.status = ExportJob.STATUS_ERROR
      job.mensagem_erro = job.mensagem_erro or "Falha ao gerar exportação."
      job.finalizado_em = now
      job.save(update_fields=["status", "mensagem_erro", "finalizado_em", "atualizado_em"])
      log_export_event("orphan_failed", job)
      continue
    if job.tentativas > 0 and job.erro_interno:
      job.status = ExportJob.STATUS_ERROR
      job.mensagem_erro = job.mensagem_erro or "Falha ao gerar exportação."
      job.finalizado_em = now
      job.save(update_fields=["status", "mensagem_erro", "finalizado_em", "atualizado_em"])
      log_export_event("orphan_failed", job)
      continue
    if job.tentativas == 0 and job.criado_em < now - timedelta(minutes=5):
      dispatch_export_job(job.pk)
      log_export_event("orphan_redispatched", job)


def pode_criar_job(usuario) -> tuple[bool, str]:
  _reconciliar_jobs_pendentes(usuario)
  concurrent = ExportJob.objects.filter(
    usuario=usuario,
    status__in=CONCURRENT_STATUSES,
  ).count()
  if concurrent >= _max_concurrent():
    return False, "Você já tem exportações em andamento. Aguarde a conclusão."

  key = RATE_LIMIT_KEY.format(user_id=usuario.pk)
  count = cache.get(key, 0)
  if count >= _rate_limit_per_hour():
    return False, "Limite de exportações por hora atingido. Tente mais tarde."

  return True, ""


def _bump_rate_limit(usuario) -> None:
  key = RATE_LIMIT_KEY.format(user_id=usuario.pk)
  count = cache.get(key, 0)
  cache.set(key, count + 1, timeout=3600)


def validar_volume(dominio: str, formato: str, usuario, filtros_json: str) -> tuple[bool, str, int]:
  raw = json.loads(filtros_json or "{}")
  ctx = ExportContext(
    usuario=usuario,
    dominio=dominio,
    formato=formato,
    filtros_raw=raw,
  )
  if dominio == ExportJob.DOMINIO_RELATORIO_PDF or formato == ExportJob.FORMATO_PDF:
    return True, "", 0

  try:
    linhas = estimate_linhas(ctx)
  except Exception:
    logger.exception("export.estimate_failed dominio=%s", dominio)
    linhas = 0

  if linhas > _max_rows_csv():
    return False, "Volume muito grande. Reduza o período ou filtros.", linhas

  if formato == ExportJob.FORMATO_XLSX and linhas > _max_rows_xlsx():
    return (
      False,
      f"Para mais de {_max_rows_xlsx():,} linhas, use CSV.".replace(",", "."),
      linhas,
    )

  return True, "", linhas


def criar_export_job(
  *,
  usuario,
  dominio: str,
  formato: str,
  filtros_json: str,
  origem: str = ExportJob.ORIGEM_MANUAL,
  idempotency_key=None,
) -> tuple[ExportJob | None, str, int]:
  if idempotency_key:
    existing = (
      ExportJob.objects.filter(
        usuario=usuario,
        idempotency_key=idempotency_key,
        status__in=CONCURRENT_STATUSES + (ExportJob.STATUS_READY,),
        criado_em__gte=timezone.now() - timedelta(minutes=5),
      )
      .order_by("-criado_em")
      .first()
    )
    if existing:
      return existing, "", existing.linhas_count or 0

  ok, msg = pode_criar_job(usuario)
  if not ok:
    return None, msg, 0

  ok_vol, msg_vol, linhas = validar_volume(dominio, formato, usuario, filtros_json)
  if not ok_vol:
    return None, msg_vol, linhas

  expira = timezone.now() + timedelta(hours=_ttl_hours())
  job = ExportJob.objects.create(
    usuario=usuario,
    dominio=dominio,
    formato=formato,
    origem=origem,
    status=ExportJob.STATUS_PENDING,
    filtros_json=filtros_json,
    expira_em=expira,
    idempotency_key=idempotency_key,
    linhas_count=linhas,
  )
  _bump_rate_limit(usuario)
  log_export_event("created", job)
  return job, "", linhas


def claim_job(job_id: int) -> ExportJob | None:
  with transaction.atomic():
    job = (
      ExportJob.objects.select_for_update(skip_locked=True)
      .filter(pk=job_id, status=ExportJob.STATUS_PENDING)
      .first()
    )
    if not job:
      return None
    if job.cancelado_em:
      job.status = ExportJob.STATUS_CANCELLED
      job.save(update_fields=["status", "atualizado_em"])
      return None
    job.status = ExportJob.STATUS_PROCESSING
    job.iniciado_em = timezone.now()
    job.tentativas += 1
    job.save(update_fields=["status", "iniciado_em", "tentativas", "atualizado_em"])
    log_export_event("claimed", job)
    return job


def cancelar_job(job: ExportJob) -> bool:
  if job.status not in (ExportJob.STATUS_PENDING, ExportJob.STATUS_PROCESSING):
    return False
  job.status = ExportJob.STATUS_CANCELLED
  job.cancelado_em = timezone.now()
  job.save(update_fields=["status", "cancelado_em", "atualizado_em"])
  log_export_event("cancelled", job)
  return True


def _mark_error(job: ExportJob, public_msg: str, internal: str, *, retry: bool = False) -> None:
  if retry and job.tentativas < job.max_tentativas:
    job.status = ExportJob.STATUS_PENDING
    job.mensagem_erro = ""
    job.erro_interno = internal[:2000]
    job.iniciado_em = None
    job.save(update_fields=["status", "mensagem_erro", "erro_interno", "iniciado_em", "atualizado_em"])
    log_export_event("retry_scheduled", job, extra={"erro": internal[:200]})
    from relatorios.services.export.dispatch import dispatch_export_job

    dispatch_export_job(job.pk)
    return
  job.status = ExportJob.STATUS_ERROR
  job.mensagem_erro = public_msg
  job.erro_interno = internal[:2000]
  job.finalizado_em = timezone.now()
  job.save(
    update_fields=[
      "status",
      "mensagem_erro",
      "erro_interno",
      "finalizado_em",
      "atualizado_em",
    ]
  )
  log_export_event("failed", job, extra={"erro": internal[:200]})


def executar_job(job_id: int, *, task_id: str | None = None) -> None:
  job = claim_job(job_id)
  if not job:
    return

  if task_id:
    ExportJob.objects.filter(pk=job.pk).update(task_id=task_id)

  job = ExportJob.objects.select_related("usuario").get(pk=job.pk)
  started = timezone.now()

  try:
    raw = json.loads(job.filtros_json or "{}")
    ctx = ExportContext(
      usuario=job.usuario,
      dominio=job.dominio,
      formato=job.formato,
      filtros_raw=raw,
      job_id=job.pk,
    )
    result = run_export(ctx)

    max_bytes = int(getattr(settings, "EXPORT_MAX_FILE_BYTES", 50 * 1024 * 1024))
    if result.tamanho_bytes > max_bytes:
      raise ValueError("Arquivo gerado excede o tamanho máximo permitido.")

    job.arquivo.save(result.nome_arquivo, ContentFile(result.content), save=False)
    job.nome_arquivo = result.nome_arquivo
    job.tamanho_bytes = result.tamanho_bytes
    job.linhas_count = result.linhas_count
    job.status = ExportJob.STATUS_READY
    job.mensagem_erro = ""
    job.erro_interno = ""
    job.finalizado_em = timezone.now()
    job.save(
      update_fields=[
        "arquivo",
        "nome_arquivo",
        "tamanho_bytes",
        "linhas_count",
        "status",
        "mensagem_erro",
        "erro_interno",
        "finalizado_em",
        "atualizado_em",
      ]
    )
    duration_ms = int((timezone.now() - started).total_seconds() * 1000)
    log_export_event("completed", job, extra={"duration_ms": duration_ms})

  except Exception as exc:
    tb = traceback.format_exc()
    retry = not isinstance(exc, (ValueError, RuntimeError))
    public_msg = "Falha ao gerar exportação."
    if isinstance(exc, RuntimeError) and str(exc):
      public_msg = str(exc)[:200]
    _mark_error(
      job,
      public_msg,
      tb if settings.DEBUG else str(exc),
      retry=retry,
    )
