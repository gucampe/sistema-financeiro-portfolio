"""Decomposição de TTFB por request (ENABLE_PERF_MIDDLEWARE=1)."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from django.conf import settings
from django.db import connection, reset_queries

logger = logging.getLogger("perf.request")


class PerfTimingMiddleware:
    """Mede db_ms, context_ms, render_ms e total_ms por rota."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "ENABLE_PERF_MIDDLEWARE", False):
            return self.get_response(request)

        request._perf_t0 = time.perf_counter()
        request._perf_view_end = None
        request._perf_render_ms = 0.0
        request._perf_context_ms = 0.0

        reset_queries()
        connection.force_debug_cursor = True
        try:
            response = self.get_response(request)
        finally:
            connection.force_debug_cursor = False

        total_ms = (time.perf_counter() - request._perf_t0) * 1000
        db_ms = sum(float(q.get("time", 0)) for q in connection.queries) * 1000
        render_ms = float(getattr(request, "_perf_render_ms", 0))
        context_ms = float(getattr(request, "_perf_context_ms", 0))
        minify_ms = float(getattr(response, "_perf_minify_ms", 0))
        query_count = len(connection.queries)

        payload: dict[str, Any] = {
            "route": request.path,
            "method": request.method,
            "htmx": bool(request.headers.get("HX-Request")),
            "total_ms": round(total_ms, 2),
            "db_ms": round(db_ms, 2),
            "context_ms": round(context_ms, 2),
            "render_ms": round(render_ms, 2),
            "minify_ms": round(minify_ms, 2),
            "query_count": query_count,
            "html_bytes": len(getattr(response, "content", b"") or b""),
        }

        response["X-Perf-Timing"] = json.dumps(payload, separators=(",", ":"))
        logger.info("perf.route %s", json.dumps(payload, separators=(",", ":")))

        try:
            import sentry_sdk

            with sentry_sdk.configure_scope() as scope:
                scope.set_context("perf", payload)
        except Exception:
            pass

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(settings, "ENABLE_PERF_MIDDLEWARE", False):
            request._perf_view_start = time.perf_counter()
        return None

    def process_template_response(self, request, response):
        if not getattr(settings, "ENABLE_PERF_MIDDLEWARE", False):
            return response
        if hasattr(request, "_perf_view_start"):
            request._perf_context_ms = (time.perf_counter() - request._perf_view_start) * 1000
        if hasattr(response, "render") and not response.is_rendered:
            original_render = response.render

            def timed_render():
                t0 = time.perf_counter()
                result = original_render()
                request._perf_render_ms = (time.perf_counter() - t0) * 1000
                return result

            response.render = timed_render
        return response
