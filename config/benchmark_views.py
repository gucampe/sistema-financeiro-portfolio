"""
Rotas de benchmark para isolar gargalos de infra/pipeline.

Ativas apenas com DEBUG=True e ENABLE_BENCHMARK_ROUTES=1.
"""

from __future__ import annotations

import time

from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse


@login_required
def ping(request):
    """Overhead mínimo com auth."""
    return HttpResponse("pong", content_type="text/plain")


@login_required
def ping_auth(request):
    """Custo de auth + sessão + perfil prefetch, sem template."""
    user = request.user
    return JsonResponse(
        {
            "ok": True,
            "user_id": user.pk,
        }
    )


@login_required
def ping_template(request):
    """Custo de renderização Django, sem banco."""
    return TemplateResponse(
        request,
        "benchmark/ping.html",
        {"timestamp": time.time()},
    )


@login_required
def ping_db(request):
    """Latência round-trip ao banco (query trivial)."""
    t0 = time.perf_counter()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        row = cursor.fetchone()
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return JsonResponse({"ok": row[0] == 1, "db_ms": round(elapsed_ms, 2)})
