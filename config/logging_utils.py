"""Helpers para sanitização de logs e tracebacks (LGPD)."""

from __future__ import annotations

import re

_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(password|senha|token|secret|api[_-]?key)\s*[=:]\s*\S+"),
    re.compile(r"(?i)(descricao|description|linhas|payload)\s*[=:]\s*.+"),
    re.compile(r"key=[A-Za-z0-9_-]{10,}"),
    re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
)


def sanitize_log_field(value: str, *, max_len: int = 120) -> str:
    if not value:
        return ""
    text = str(value)
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub("[redacted]", text)
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def sanitize_traceback(tb: str, *, max_len: int = 500) -> str:
    if not tb:
        return ""
    lines = []
    for line in tb.splitlines():
        lower = line.lower()
        if any(k in lower for k in ("insert into", "update ", "select ", "post=", "get=", "password")):
            lines.append("[redacted sql/request line]")
        else:
            lines.append(line)
    out = "\n".join(lines)
    if len(out) > max_len:
        out = out[:max_len] + "…"
    return out
