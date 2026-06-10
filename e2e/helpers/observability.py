"""Artefatos e categorização de falhas E2E."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext, Page

ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts"
TRACES_DIR = ARTIFACTS_DIR / "traces"
HAR_DIR = ARTIFACTS_DIR / "har"
LOGS_DIR = ARTIFACTS_DIR / "console"


def safe_test_name(test_name: str) -> str:
    return (
        test_name.replace("/", "_")
        .replace("::", "_")
        .replace("[", "_")
        .replace("]", "")
    )


def is_e2e_item(nodeid: str) -> bool:
    return "e2e" in nodeid.replace("\\", "/")


def attach_console_listener(page: Page) -> list[dict[str, str]]:
    logs: list[dict[str, str]] = []

    def _on_console(msg) -> None:
        logs.append({"type": msg.type, "text": msg.text})

    page.on("console", _on_console)
    return logs


def start_tracing(context: BrowserContext) -> None:
    context.tracing.start(screenshots=True, snapshots=True, sources=True)


def stop_tracing(context: BrowserContext, test_name: str, *, failed: bool) -> None:
    try:
        if failed:
            TRACES_DIR.mkdir(parents=True, exist_ok=True)
            path = TRACES_DIR / f"{safe_test_name(test_name)}.zip"
            context.tracing.stop(path=str(path))
        else:
            context.tracing.stop()
    except Exception:
        pass


def save_console_logs(logs: list[dict[str, str]], test_name: str) -> None:
    if not logs:
        return
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    path = LOGS_DIR / f"{safe_test_name(test_name)}.json"
    path.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")


def har_path_for(test_name: str) -> Path:
    HAR_DIR.mkdir(parents=True, exist_ok=True)
    return HAR_DIR / f"{safe_test_name(test_name)}.har"


def on_test_failed(
    page: Page,
    test_name: str,
    *,
    context: BrowserContext | None = None,
    console_logs: list[dict[str, str]] | None = None,
) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    safe = safe_test_name(test_name)
    try:
        page.screenshot(path=str(ARTIFACTS_DIR / f"{safe}.png"), full_page=True)
    except Exception:
        pass
    try:
        html_path = ARTIFACTS_DIR / f"{safe}.html"
        html_path.write_text(page.content(), encoding="utf-8")
    except Exception:
        pass
    if console_logs:
        save_console_logs(console_logs, test_name)
    if context is not None:
        stop_tracing(context, test_name, failed=True)


def classify_failure(message: str) -> str:
    upper = message.upper()
    if "CON-" in upper or "SALDO" in upper or "FATURA" in upper:
        return "CALC"
    if "RACE" in upper or "RC-" in upper:
        return "RACE"
    if "TIMEOUT" in upper or "FLAKY" in upper:
        return "FLAKY"
    if "AJAX" in upper or "FETCH" in upper or "HTTP" in upper:
        return "AJAX"
    return "TEST"


def failure_summary(test_name: str) -> dict[str, Any]:
    safe = safe_test_name(test_name)
    artifacts: dict[str, str] = {}
    for label, directory, suffix in (
        ("screenshot", ARTIFACTS_DIR, ".png"),
        ("html", ARTIFACTS_DIR, ".html"),
        ("trace", TRACES_DIR, ".zip"),
        ("har", HAR_DIR, ".har"),
        ("console", LOGS_DIR, ".json"),
    ):
        path = directory / f"{safe}{suffix}"
        if path.exists():
            artifacts[label] = str(path)
    return {
        "test": test_name,
        "classification": classify_failure(test_name),
        "artifacts": artifacts,
    }
