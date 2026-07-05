"""Integração opcional de observabilidade (Sentry, Silk, Debug Toolbar)."""

from __future__ import annotations

import os
import re

from decouple import config

_SCRUB_PATTERNS = (
    re.compile(r"(?i)(descricao|linhas|payload|password|senha|token|secret|api[_-]?key)[\"']?\s*[:=]\s*[\"']?[^\"'\s,}]+"),
    re.compile(r"key=[A-Za-z0-9_-]{10,}"),
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
)


def _scrub_sentry_event(event, hint):
    """Remove dados financeiros/PII de eventos Sentry."""
    message = event.get("message")
    if isinstance(message, str):
        for pattern in _SCRUB_PATTERNS:
            message = pattern.sub("[redacted]", message)
        event["message"] = message

    if "exception" in event:
        for exc in event.get("exception", {}).get("values") or []:
            val = exc.get("value")
            if isinstance(val, str):
                for pattern in _SCRUB_PATTERNS:
                    val = pattern.sub("[redacted]", val)
                exc["value"] = val

    req = event.get("request") or {}
    if req.get("data"):
        req["data"] = "[redacted]"
        event["request"] = req
    return event


def init_sentry() -> None:
    dsn = config("SENTRY_DSN", default="").strip()
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    integrations = [DjangoIntegration()]
    try:
        integrations.append(CeleryIntegration(monitor_beat_tasks=True))
    except Exception:
        pass

    traces_sample_rate = config(
        "SENTRY_TRACES_SAMPLE_RATE",
        default=0.2 if not config("DEBUG", default=True, cast=bool) else 1.0,
        cast=float,
    )

    sentry_sdk.init(
        dsn=dsn,
        integrations=integrations,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        environment=config("SENTRY_ENVIRONMENT", default=os.environ.get("RENDER", "development")),
        before_send=_scrub_sentry_event,
    )


def silk_enabled() -> bool:
    if not config("DEBUG", default=True, cast=bool):
        return False
    return config("ENABLE_SILK", default=False, cast=bool)


def debug_toolbar_enabled() -> bool:
    if not config("DEBUG", default=True, cast=bool):
        return False
    return config("ENABLE_DEBUG_TOOLBAR", default=False, cast=bool)


def perf_span(op: str, description: str):
    """Context manager para spans Sentry em agregações."""
    try:
        import sentry_sdk

        return sentry_sdk.start_span(op=op, name=description)
    except Exception:
        from contextlib import nullcontext

        return nullcontext()
