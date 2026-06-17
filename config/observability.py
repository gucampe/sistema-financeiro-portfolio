"""Integração opcional de observabilidade (Sentry, Silk, Debug Toolbar)."""

from __future__ import annotations

import os

from decouple import config


def init_sentry() -> None:
    dsn = config("SENTRY_DSN", default="").strip()
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    traces_sample_rate = config(
        "SENTRY_TRACES_SAMPLE_RATE",
        default=0.2 if not config("DEBUG", default=True, cast=bool) else 1.0,
        cast=float,
    )

    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        environment=config("SENTRY_ENVIRONMENT", default=os.environ.get("RENDER", "development")),
    )


def silk_enabled() -> bool:
    return config("ENABLE_SILK", default=False, cast=bool)


def debug_toolbar_enabled() -> bool:
    return config("ENABLE_DEBUG_TOOLBAR", default=False, cast=bool)
