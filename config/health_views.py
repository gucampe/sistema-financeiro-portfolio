"""Health check para monitoramento (nginx up vs Django/DB/Redis)."""

from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def health(request):
    checks: dict[str, str] = {}
    ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"
        ok = False

    redis_url = getattr(settings, "CACHES", {}).get("default", {}).get("LOCATION", "")
    if redis_url:
        try:
            from django.core.cache import cache

            cache.set("_health_ping", "1", timeout=5)
            if cache.get("_health_ping") != "1":
                raise RuntimeError("cache read failed")
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {type(exc).__name__}"
            ok = False
    else:
        checks["redis"] = "skipped"

    payload = {"status": "ok" if ok else "degraded", "checks": checks}
    return JsonResponse(payload, status=200 if ok else 503)
