from __future__ import annotations

import logging
from datetime import date

from django.conf import settings

logger = logging.getLogger("categorizacao.llm")

# Preços aproximados USD por 1M tokens (planejamento)
_PRICE_IN_PER_M = {
    "gemini-2.5-flash-lite": 0.10,
    "gemini-2.5-flash": 0.15,
    "gemini-2.0-flash": 0.10,
    "gemini-2.0-flash-lite": 0.05,
    "gemini-1.5-pro": 1.25,
    "mock-llm": 0.0,
}
_PRICE_OUT_PER_M = {
    "gemini-2.5-flash-lite": 0.40,
    "gemini-2.5-flash": 0.60,
    "gemini-2.0-flash": 0.40,
    "gemini-2.0-flash-lite": 0.20,
    "gemini-1.5-pro": 5.00,
    "mock-llm": 0.0,
}

_daily_usd: float = 0.0
_daily_date: date | None = None


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin = _PRICE_IN_PER_M.get(model, 0.15)
    pout = _PRICE_OUT_PER_M.get(model, 0.50)
    return (input_tokens * pin + output_tokens * pout) / 1_000_000


def record_usage(model: str, input_tokens: int, output_tokens: int) -> float:
    global _daily_usd, _daily_date
    today = date.today()
    if _daily_date != today:
        _daily_date = today
        _daily_usd = 0.0
    cost = estimate_cost_usd(model, input_tokens, output_tokens)
    _daily_usd += cost
    return cost


def is_budget_exceeded() -> bool:
    budget = float(getattr(settings, "CATEGORIZACAO_LLM_DAILY_BUDGET_USD", 0) or 0)
    if budget <= 0:
        return False
    return _daily_usd >= budget


def get_daily_spend() -> float:
    return _daily_usd
