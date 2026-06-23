from __future__ import annotations

from django.conf import settings

from categorizacao.services.llm.providers.gemini import GeminiProvider, MockLLMProvider

MODEL_REGISTRY = {
    "gemini-2.5-flash-lite": {"tier": "flash", "cost_tier": 1},
    "gemini-2.5-flash": {"tier": "flash", "cost_tier": 1},
    "gemini-2.0-flash": {"tier": "flash", "cost_tier": 1},
    "gemini-2.0-flash-lite": {"tier": "flash", "cost_tier": 1},
    "gemini-1.5-pro": {"tier": "pro", "cost_tier": 3},
    "mock-llm": {"tier": "mock", "cost_tier": 0},
}


def get_llm_provider(model_id: str | None = None):
    model_id = model_id or getattr(settings, "CATEGORIZACAO_LLM_MODEL", "gemini-2.5-flash-lite")
    if model_id == "mock-llm" or getattr(settings, "CATEGORIZACAO_LLM_USE_MOCK", False):
        return MockLLMProvider()
    return GeminiProvider(model_id=model_id)


def resolve_ab_model(user_id: int) -> str:
    """A/B: hash usuário escolhe modelo A ou B."""
    variant = getattr(settings, "CATEGORIZACAO_LLM_AB_VARIANT", "") or ""
    if not variant:
        return getattr(settings, "CATEGORIZACAO_LLM_MODEL", "gemini-2.5-flash-lite")
    bucket = user_id % 100
    rollout = int(getattr(settings, "CATEGORIZACAO_LLM_AB_ROLLOUT_PCT", 50))
    if bucket >= rollout:
        return getattr(settings, "CATEGORIZACAO_LLM_MODEL", "gemini-2.5-flash-lite")
    if variant == "pro":
        return getattr(settings, "CATEGORIZACAO_LLM_MODEL_PRO", "gemini-1.5-pro")
    return getattr(settings, "CATEGORIZACAO_LLM_MODEL_FLASH", "gemini-2.5-flash-lite")
