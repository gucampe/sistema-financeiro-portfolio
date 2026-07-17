"""Health check para monitoramento (nginx up vs Django/DB/Redis)."""

from __future__ import annotations

from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def _run_checks() -> tuple[bool, dict[str, str]]:
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

    return ok, checks


def health(request):
    """Payload mínimo público; detalhes só com X-Health-Token válido."""
    ok, checks = _run_checks()
    status_label = "ok" if ok else "degraded"
    http_status = 200 if ok else 503

    token = getattr(settings, "HEALTH_CHECK_TOKEN", "").strip()
    provided = request.headers.get("X-Health-Token", "")
    detailed = bool(token) and provided == token

    if detailed:
        return JsonResponse(
            {"status": status_label, "checks": checks},
            status=http_status,
        )

    return JsonResponse({"status": status_label}, status=http_status)
