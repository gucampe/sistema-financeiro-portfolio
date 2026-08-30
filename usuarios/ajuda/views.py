"""Endpoints da Ajuda e eventos de produto."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from usuarios.ajuda.dicas import DICAS, marcar_dica_dispensada
from usuarios.models import Perfil
from usuarios.services.produto_eventos import EVENTOS_PERMITIDOS, registrar_evento_seguro


@login_required
@require_POST
def produto_evento(request):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"status": "error"}, status=400)
    evento = str(body.get("evento") or "").strip()
    if evento not in EVENTOS_PERMITIDOS:
        return JsonResponse({"status": "error", "message": "evento inválido"}, status=400)
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    registrar_evento_seguro(request.user, evento, payload)
    return JsonResponse({"status": "ok"})


@login_required
@require_POST
def dica_dispensar(request):
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"status": "error"}, status=400)
    dica_id = str(body.get("dica_id") or "").strip()
    if dica_id not in DICAS:
        return JsonResponse({"status": "error", "message": "dica inválida"}, status=400)
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    dica = marcar_dica_dispensada(perfil, dica_id)
    registrar_evento_seguro(
        request.user,
        "context_tip_dismissed",
        {"dica_id": dica_id, "versao": dica.versao if dica else 0},
    )
    return JsonResponse({"status": "ok"})
