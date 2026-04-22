from __future__ import annotations

import csv
import io
import json
import threading
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.http import FileResponse, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View

from relatorios.models import ExportRelatorioJob
from relatorios.selectors import transacoes_base_qs
from relatorios.services.agregacoes import aplicar_filtros_relatorio, serie_receitas_despesas, top_categorias
from relatorios.services.filtros import parse_relatorio_filtros


class ApiSerieTendenciaView(LoginRequiredMixin, View):
    """Receitas/despesas/ajustes por bucket temporal — mesmos filtros GET da página."""

    def get(self, request):
        filtros = parse_relatorio_filtros(request.GET, usuario=request.user)
        qs = aplicar_filtros_relatorio(transacoes_base_qs(request.user), filtros)
        serie = serie_receitas_despesas(qs, filtros)
        return JsonResponse(serie)


class ApiTopCategoriasView(LoginRequiredMixin, View):
    """Top categorias por tipo (receita ou despesa)."""

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


def _executar_export_job(job_id: int):
    from datetime import datetime

    from django.db import connections

    from relatorios.services.filtros import RelatorioFiltros

    connections.close_all()

    job = ExportRelatorioJob.objects.select_related("usuario").filter(pk=job_id).first()
    if not job:
        return
    try:
        raw = json.loads(job.filtros_json or "{}")
        filtros = RelatorioFiltros(
            data_inicio=datetime.strptime(raw["inicio"], "%Y-%m-%d").date(),
            data_fim=datetime.strptime(raw["fim"], "%Y-%m-%d").date(),
            conta_ids=tuple(raw.get("conta_ids", [])),
            categoria_ids=tuple(raw.get("categoria_ids", [])),
            tipos=tuple(raw.get("tipos", [])),
            preset=raw.get("preset", "custom"),
        )
    except Exception as exc:  # noqa: BLE001
        job.status = ExportRelatorioJob.STATUS_ERROR
        job.mensagem_erro = str(exc)
        job.save(update_fields=["status", "mensagem_erro", "atualizado_em"])
        return

    qs = aplicar_filtros_relatorio(transacoes_base_qs(job.usuario), filtros).order_by("data", "id")
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["data", "tipo", "valor", "descricao", "conta", "categoria"])
    for t in qs.iterator(chunk_size=500):
        w.writerow(
            [
                t.data.isoformat(),
                t.tipo,
                str(t.valor),
                t.descricao,
                t.conta.nome,
                t.categoria.nome,
            ]
        )
    data = buf.getvalue().encode("utf-8")
    nome = f"relatorio_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    job.arquivo.save(nome, ContentFile(data), save=False)
    job.status = ExportRelatorioJob.STATUS_READY
    job.mensagem_erro = ""
    job.save(update_fields=["arquivo", "status", "mensagem_erro", "atualizado_em"])


class ApiExportCsvCreateView(LoginRequiredMixin, View):
    """Cria job de exportação e dispara processamento em thread (sem fila externa)."""

    def post(self, request):
        filtros = parse_relatorio_filtros(request.GET, usuario=request.user)
        payload = {
            "inicio": filtros.data_inicio.isoformat(),
            "fim": filtros.data_fim.isoformat(),
            "conta_ids": list(filtros.conta_ids),
            "categoria_ids": list(filtros.categoria_ids),
            "tipos": list(filtros.tipos),
            "preset": filtros.preset,
        }
        job = ExportRelatorioJob.objects.create(
            usuario=request.user,
            status=ExportRelatorioJob.STATUS_PENDING,
            filtros_json=json.dumps(payload),
        )
        t = threading.Thread(target=_executar_export_job, args=(job.pk,), daemon=True)
        t.start()
        return JsonResponse({"job_id": job.pk, "status": job.status}, status=202)


class ApiExportJobDetailView(LoginRequiredMixin, View):
    def get(self, request, pk: int):
        job = ExportRelatorioJob.objects.filter(pk=pk, usuario=request.user).first()
        if not job:
            return JsonResponse({"detail": "Não encontrado."}, status=404)
        out = {"id": job.pk, "status": job.status}
        if job.status == ExportRelatorioJob.STATUS_READY and job.arquivo:
            out["download_url"] = request.build_absolute_uri(
                reverse("relatorios:api_export_job_download", args=[job.pk])
            )
        if job.status == ExportRelatorioJob.STATUS_ERROR:
            out["erro"] = job.mensagem_erro
        return JsonResponse(out)


class ApiExportJobDownloadView(LoginRequiredMixin, View):
    def get(self, request, pk: int):
        job = ExportRelatorioJob.objects.filter(pk=pk, usuario=request.user).first()
        if not job or job.status != ExportRelatorioJob.STATUS_READY or not job.arquivo:
            return HttpResponse("Arquivo indisponível.", status=404)
        return FileResponse(job.arquivo.open("rb"), as_attachment=True, filename=job.arquivo.name.split("/")[-1])
