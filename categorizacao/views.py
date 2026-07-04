from __future__ import annotations

import json
import logging
import threading
import time

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from categorizacao.forms import RegraCategorizacaoForm
from categorizacao.models import RegraCategorizacao
from categorizacao.services.cache import invalidar_cache_usuario
from categorizacao.services.pipeline import sugerir, sugerir_batch
from categorizacao.services.import_suggestions import aplicar_sugestao_em_linha
from categorizacao.services.recategorizacao import recategorizar_transacoes
from categorizacao.models import CategorizacaoUXEvent

logger = logging.getLogger(__name__)

MAX_LINHAS_BATCH = 500
MAX_DESCRICAO_CHARS = 200
IA_BATCH_RATE_LIMIT = 30
IA_BATCH_RATE_WINDOW = 3600


def _truncate_descricao(descricao: str) -> str:
    return (descricao or "").strip()[:MAX_DESCRICAO_CHARS]


def _check_ia_batch_rate_limit(user) -> bool:
    key = f"ia_batch_rl:{user.pk}"
    count = cache.get(key, 0)
    if count >= IA_BATCH_RATE_LIMIT:
        return False
    cache.set(key, count + 1, timeout=IA_BATCH_RATE_WINDOW)
    return True


@login_required
@require_GET
def sugerir_categoria(request):
    descricao = _truncate_descricao(request.GET.get("descricao") or "")
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


@login_required
@require_POST
def categorizar_import_batch(request):
    """Executa o pipeline híbrido sob demanda para linhas de importação."""
    if getattr(settings, "ENABLE_CATEGORIZACAO_LLM", False) and not _check_ia_batch_rate_limit(request.user):
        return JsonResponse(
            {"status": "error", "message": "Limite de categorizações por hora atingido. Tente mais tarde."},
            status=429,
        )

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "JSON inválido."}, status=400)

    contexto = (data.get("contexto") or "import_ofx").strip()
    if contexto not in ("import_ofx", "import_planilha"):
        contexto = "import_ofx"

    linhas_in = data.get("linhas") or []
    if not linhas_in:
        return JsonResponse({"status": "error", "message": "Nenhuma linha informada."}, status=400)
    if len(linhas_in) > MAX_LINHAS_BATCH:
        return JsonResponse(
            {"status": "error", "message": f"Máximo de {MAX_LINHAS_BATCH} linhas por lote."},
            status=400,
        )

    CategorizacaoUXEvent.objects.create(
        usuario=request.user,
        evento="ia_click",
        contexto=contexto,
        payload={"total_linhas": len(linhas_in)},
    )

    t0 = time.monotonic()
    batch_input = [
        {
            "descricao": _truncate_descricao(l.get("descricao") or ""),
            "tipo": (l.get("tipo") or "despesa").strip(),
            "valor": l.get("valor"),
        }
        for l in linhas_in
    ]
    sugestoes = sugerir_batch(request.user, batch_input)

    por_fonte: dict[str, int] = {}
    linhas_out = []
    categorizadas = 0
    sem_sugestao = 0
    badges_aprendizado = 0

    for linha_in, sug in zip(linhas_in, sugestoes, strict=True):
        item = dict(linha_in)
        if sug:
            aplicar_sugestao_em_linha(item, sug)
            categorizadas += 1
            por_fonte[sug.fonte] = por_fonte.get(sug.fonte, 0) + 1
            if item.get("categoria_sugerida_badge_aprendizado"):
                badges_aprendizado += 1
        else:
            sem_sugestao += 1
            item["categoria_sugerida_nivel_confianca"] = "baixa"
        linhas_out.append(item)

    duracao_ms = int((time.monotonic() - t0) * 1000)

    CategorizacaoUXEvent.objects.create(
        usuario=request.user,
        evento="ia_complete",
        contexto=contexto,
        payload={
            "total_linhas": len(linhas_in),
            "categorizadas": categorizadas,
            "sem_sugestao": sem_sugestao,
            "badges_aprendizado": badges_aprendizado,
            "por_fonte": por_fonte,
            "duracao_ms": duracao_ms,
        },
    )

    return JsonResponse({
        "status": "ok",
        "linhas": linhas_out,
        "resumo": {
            "total": len(linhas_in),
            "categorizadas": categorizadas,
            "sem_sugestao": sem_sugestao,
            "por_fonte": por_fonte,
            "duracao_ms": duracao_ms,
        },
    })


@login_required
@require_POST
def categorizar_import_cancel(request):
    """Registra cancelamento da experiência de categorização IA."""
    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        data = {}
    contexto = (data.get("contexto") or "import_ofx").strip()
    CategorizacaoUXEvent.objects.create(
        usuario=request.user,
        evento="ia_cancel",
        contexto=contexto if contexto in ("import_ofx", "import_planilha") else "import_ofx",
        payload=data.get("payload") or {},
    )
    return JsonResponse({"status": "ok"})
