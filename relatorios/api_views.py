from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from relatorios.models import ExportJob
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import aplicar_filtros_relatorio, serie_receitas_despesas, top_categorias
from relatorios.services.export.dispatch import dispatch_export_job
from relatorios.services.export.jobs import cancelar_job, criar_export_job
from relatorios.services.export.serializers import serialize_job_filtros
from relatorios.services.filtros import parse_relatorio_filtros
from usuarios.audit import registrar_audit
from usuarios.models import AuditLog

import logging

logger = logging.getLogger(__name__)


class ApiSerieTendenciaView(LoginRequiredMixin, View):
  def get(self, request):
    try:
      filtros = parse_relatorio_filtros(request.GET, usuario=request.user)
      qs = aplicar_filtros_relatorio(transacoes_base_qs(request.user), filtros)
      serie = serie_receitas_despesas(qs, filtros)
      return JsonResponse(serie)
    except Exception:
      logger.exception("api_serie_tendencia falhou")
      return JsonResponse({"detail": "Erro ao calcular a série.", "erro": "serie_tendencia"}, status=500)


class ApiTopCategoriasView(LoginRequiredMixin, View):
  def get(self, request):
    tipo = request.GET.get("tipo", "despesa")
    if tipo not in ("receita", "despesa"):
      tipo = "despesa"
    filtros = parse_relatorio_filtros(request.GET, usuario=request.user)
    qs = aplicar_filtros_relatorio(transacoes_base_qs(request.user), filtros)
    top = top_categorias(qs, tipo, limit=12)
    return JsonResponse(
      {
        "tipo": tipo,
        "itens": [
          {
            "categoria_id": x["categoria_id"],
            "nome": x["nome"],
            "cor": x["cor"],
            "total": str(x["total"]),
            "percentual": str(x["percentual"]),
          }
          for x in top
        ],
      }
    )


def _job_to_json(job: ExportJob, request) -> dict:
  out = {
    "id": job.pk,
    "status": job.status,
    "dominio": job.dominio,
    "formato": job.formato,
    "linhas_count": job.linhas_count,
    "criado_em": job.criado_em.isoformat() if job.criado_em else None,
  }
  if job.status == ExportJob.STATUS_READY and job.arquivo:
    out["download_url"] = request.build_absolute_uri(
      reverse("relatorios:api_export_job_download", args=[job.pk])
    )
    out["nome_arquivo"] = job.download_filename
  if job.status == ExportJob.STATUS_ERROR:
    out["erro"] = job.mensagem_erro or "Falha ao gerar exportação."
  if job.status == ExportJob.STATUS_PROCESSING and job.iniciado_em:
    out["processando_desde"] = job.iniciado_em.isoformat()
  return out


def _parse_dominio_formato(request) -> tuple[str | None, str | None, str | None]:
  dominio = (request.POST.get("dominio") or request.GET.get("dominio") or ExportJob.DOMINIO_TRANSACOES).strip()
  formato = (request.POST.get("formato") or request.GET.get("formato") or ExportJob.FORMATO_CSV).strip().lower()

  valid_dominios = {c[0] for c in ExportJob.DOMINIO_CHOICES}
  valid_formatos = {c[0] for c in ExportJob.FORMATO_CHOICES}

  if dominio not in valid_dominios:
    return None, None, "Domínio inválido."
  if formato not in valid_formatos:
    return None, None, "Formato inválido."

  features = getattr(settings, "FEATURES", {})
  if formato == ExportJob.FORMATO_PDF and not features.get("export_pdf", True):
    return None, None, "Exportação PDF temporariamente indisponível."
  if formato == ExportJob.FORMATO_XLSX and not features.get("export_xlsx", True):
    return None, None, "Exportação Excel temporariamente indisponível."
  if dominio == ExportJob.DOMINIO_RELATORIO_PDF:
    formato = ExportJob.FORMATO_PDF
  if dominio == ExportJob.DOMINIO_TITULAR_LGPD:
    formato = ExportJob.FORMATO_ZIP

  return dominio, formato, None


@method_decorator(require_POST, name="dispatch")
class ApiExportJobCreateView(LoginRequiredMixin, View):
  def post(self, request):
    dominio, formato, err = _parse_dominio_formato(request)
    if err:
      return JsonResponse({"detail": err}, status=400)

    idem_raw = request.headers.get("X-Idempotency-Key") or request.POST.get("idempotency_key")
    idempotency_key = None
    if idem_raw:
      try:
        idempotency_key = uuid.UUID(str(idem_raw))
      except ValueError:
        return JsonResponse({"detail": "Chave de idempotência inválida."}, status=400)

    filtros_json = serialize_job_filtros(request.GET, usuario=request.user)
    job, msg, linhas = criar_export_job(
      usuario=request.user,
      dominio=dominio,
      formato=formato,
      filtros_json=filtros_json,
      idempotency_key=idempotency_key,
    )
    if not job:
      return JsonResponse({"detail": msg, "linhas_estimadas": linhas}, status=429 if "hora" in msg else 400)

    registrar_audit(
      acao=AuditLog.ACAO_EXPORT_REQUESTED,
      usuario=request.user,
      request=request,
      metadata={"job_id": job.pk, "dominio": dominio, "formato": formato},
    )
    dispatch_export_job(job.pk)
    return JsonResponse(
      {
        "job_id": job.pk,
        "status": job.status,
        "linhas_estimadas": linhas,
        **_job_to_json(job, request),
      },
      status=202,
    )


@method_decorator(require_GET, name="dispatch")
class ApiExportJobListView(LoginRequiredMixin, View):
  def get(self, request):
    jobs = ExportJob.objects.filter(usuario=request.user).order_by("-criado_em")[:10]
    return JsonResponse({"jobs": [_job_to_json(j, request) for j in jobs]})


class ApiExportJobDetailView(LoginRequiredMixin, View):
  def get(self, request, pk: int):
    job = ExportJob.objects.filter(pk=pk, usuario=request.user).first()
    if not job:
      return JsonResponse({"detail": "Não encontrado."}, status=404)
    return JsonResponse(_job_to_json(job, request))


@method_decorator(require_POST, name="dispatch")
class ApiExportJobCancelView(LoginRequiredMixin, View):
  def post(self, request, pk: int):
    job = ExportJob.objects.filter(pk=pk, usuario=request.user).first()
    if not job:
      return JsonResponse({"detail": "Não encontrado."}, status=404)
    if not cancelar_job(job):
      return JsonResponse({"detail": "Não é possível cancelar este job."}, status=400)
    return JsonResponse({"id": job.pk, "status": job.status})


class ApiExportJobDownloadView(LoginRequiredMixin, View):
  def get(self, request, pk: int):
    job = ExportJob.objects.filter(pk=pk, usuario=request.user).first()
    if not job or job.status != ExportJob.STATUS_READY or not job.arquivo:
      return HttpResponse("Arquivo indisponível.", status=404)
    if job.expira_em and job.expira_em < timezone.now():
      return HttpResponse("Arquivo expirado.", status=410)
    return FileResponse(
      job.arquivo.open("rb"),
      as_attachment=True,
      filename=job.download_filename,
    )


@method_decorator(require_POST, name="dispatch")
class ApiExportCsvCreateView(LoginRequiredMixin, View):
  """Deprecated — compatibilidade com endpoint legado."""

  def post(self, request):
    filtros_json = serialize_job_filtros(request.GET, usuario=request.user)
    job, msg, linhas = criar_export_job(
      usuario=request.user,
      dominio=ExportJob.DOMINIO_TRANSACOES,
      formato=ExportJob.FORMATO_CSV,
      filtros_json=filtros_json,
    )
    if not job:
      return JsonResponse({"detail": msg}, status=429 if msg and "hora" in msg else 400)
    dispatch_export_job(job.pk)
    return JsonResponse({"job_id": job.pk, "status": job.status}, status=202)


class ApiExportJobShareDownloadView(LoginRequiredMixin, View):
  """Download por token (base para compartilhamento futuro — requer auth no MVP)."""

  def get(self, request, token: uuid.UUID):
    job = ExportJob.objects.filter(token_download=token, usuario=request.user).first()
    if not job or job.status != ExportJob.STATUS_READY or not job.arquivo:
      return HttpResponse("Arquivo indisponível.", status=404)
    return FileResponse(
      job.arquivo.open("rb"),
      as_attachment=True,
      filename=job.download_filename,
    )
