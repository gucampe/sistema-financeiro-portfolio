"""Fallback LLM para categorização (Gemini)."""

from categorizacao.services.llm.orchestrator import classificar_com_llm

__all__ = ["classificar_com_llm"]
