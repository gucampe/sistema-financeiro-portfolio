from __future__ import annotations

from dataclasses import dataclass

# USD por 1M tokens (ordem de grandeza — Gemini Flash, jun/2026)
PRICE_PER_MILLION = {
    "gemini-2.5-flash-lite": {"in": 0.10, "out": 0.40},
    "gemini-2.5-flash": {"in": 0.15, "out": 0.60},
    "gemini-2.0-flash": {"in": 0.10, "out": 0.40},
    "gemini-2.0-flash-lite": {"in": 0.075, "out": 0.30},
    "gemini-1.5-pro": {"in": 1.25, "out": 5.00},
    "mock-llm": {"in": 0.0, "out": 0.0},
}


@dataclass
class CostEstimate:
    model: str
    requests: int
    tokens_in: int
    tokens_out: int
    cost_usd: float


def estimate_cost(model: str, tokens_in: int, tokens_out: int, requests: int = 1) -> CostEstimate:
    prices = PRICE_PER_MILLION.get(model, PRICE_PER_MILLION["gemini-2.5-flash-lite"])
    cost = (tokens_in * prices["in"] + tokens_out * prices["out"]) / 1_000_000
    return CostEstimate(
        model=model,
        requests=requests,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=round(cost * requests, 6),
    )


def project_monthly(
    *,
    categorizacoes_dia: int,
    llm_invocation_rate: float,
    avg_tokens_in: int = 450,
    avg_tokens_out: int = 80,
    model: str = "gemini-2.5-flash-lite",
) -> CostEstimate:
    llm_calls_dia = int(categorizacoes_dia * llm_invocation_rate)
    return estimate_cost(
        model,
        avg_tokens_in * llm_calls_dia * 30,
        avg_tokens_out * llm_calls_dia * 30,
        requests=1,
    )
