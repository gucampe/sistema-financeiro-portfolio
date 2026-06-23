from __future__ import annotations

import json
import logging
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from categorizacao.forms import RegraCategorizacaoForm
from categorizacao.models import RegraCategorizacao
from categorizacao.services.cache import invalidar_cache_usuario
from categorizacao.services.pipeline import sugerir
from categorizacao.services.recategorizacao import recategorizar_transacoes

logger = logging.getLogger(__name__)


@login_required
@require_GET
def sugerir_categoria(request):
    descricao = (request.GET.get("descricao") or "").strip()
    tipo = (request.GET.get("tipo") or "despesa").strip()
    valor = request.GET.get("valor")

    if not descricao:
        return JsonResponse({"status": "ok", "sugestao": None})

    valor_dec = None
    if valor:
        try:
            from decimal import Decimal
            valor_dec = Decimal(str(valor).replace(",", "."))
        except Exception:
            valor_dec = None

    sugestao = sugerir(request.user, descricao, tipo, valor_dec)
    return JsonResponse({
        "status": "ok",
        "sugestao": sugestao.to_dict() if sugestao else None,
    })


@login_required
@require_http_methods(["GET", "POST"])
def minhas_regras(request):
    regras = RegraCategorizacao.objects.filter(
        usuario=request.user,
        ativa=True,
    ).select_related("categoria").order_by("-prioridade", "padrao")

    if request.method == "POST":
        form = RegraCategorizacaoForm(request.POST, usuario=request.user)
        if form.is_valid():
            form.save()
            invalidar_cache_usuario(request.user.pk)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"status": "ok", "message": "Regra criada."})
            return render(
                request,
                "categorizacao/minhas_regras.html",
                {"regras": regras, "form": RegraCategorizacaoForm(usuario=request.user)},
            )
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "errors": form.errors}, status=400)

    form = RegraCategorizacaoForm(usuario=request.user)
    return render(
        request,
        "categorizacao/minhas_regras.html",
        {"regras": regras, "form": form},
    )


@login_required
@require_POST
def excluir_regra(request, pk):
    regra = get_object_or_404(RegraCategorizacao, pk=pk, usuario=request.user)
    regra.ativa = False
    regra.save(update_fields=["ativa"])
    invalidar_cache_usuario(request.user.pk)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "ok"})
    return render(
        request,
        "categorizacao/minhas_regras.html",
        {
            "regras": RegraCategorizacao.objects.filter(
                usuario=request.user, ativa=True
            ).select_related("categoria"),
            "form": RegraCategorizacaoForm(usuario=request.user),
        },
    )


@login_required
@require_POST
def revisar_diversos(request):
    data = {}
    if request.content_type and "json" in request.content_type:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            pass
    dry_run = bool(data.get("dry_run", False))
    limite = int(data.get("limite", 200))

    def _run():
        try:
            recategorizar_transacoes(
                usuario=request.user,
                categoria_nome="Diversos",
                dry_run=dry_run,
                limite=limite,
            )
        except Exception:
            logger.exception("recategorizacao async falhou usuario=%s", request.user.pk)

    threading.Thread(target=_run, daemon=True).start()
    return JsonResponse({
        "status": "ok",
        "message": "Recategorização iniciada em segundo plano.",
    })
