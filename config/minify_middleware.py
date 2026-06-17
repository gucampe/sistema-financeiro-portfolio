"""Minify HTML com medição de custo (ENABLE_MINIFY_HTML)."""

from __future__ import annotations

import time

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django_minify_html.middleware import MinifyHtmlMiddleware
from minify_html import minify as minify_html_minify


class ProjectMinifyHtmlMiddleware(MinifyHtmlMiddleware):
    """Registra minify_ms quando perf middleware ou logging ativo."""

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        if not getattr(settings, "ENABLE_MINIFY_HTML", True):
            return self.get_response(request)
        return super().__call__(request)

    def maybe_minify(self, request: HttpRequest, response: HttpResponseBase) -> None:
        if not self.should_minify(request, response):
            return
        assert isinstance(response, HttpResponse)
        before = len(response.content)
        t0 = time.perf_counter()
        content = response.content.decode(response.charset)
        minified_content = minify_html_minify(content, **self.minify_args)
        response.content = minified_content
        if "Content-Length" in response:
            response["Content-Length"] = len(minified_content)
        response._perf_minify_ms = (time.perf_counter() - t0) * 1000
        response._perf_minify_bytes_before = before
        response._perf_minify_bytes_after = len(minified_content)
