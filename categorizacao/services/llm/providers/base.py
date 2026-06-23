from __future__ import annotations

from typing import Protocol

from categorizacao.schemas.llm_response import LLMRawResult


class LLMProvider(Protocol):
    model_id: str

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict,
        timeout_s: float,
    ) -> LLMRawResult: ...
