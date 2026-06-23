from __future__ import annotations

from categorizacao.services.llm.orchestrator import classificar_com_llm
from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao


def classificar_llm(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    """Camada fina — delega ao orchestrator (fase 2)."""
    return classificar_com_llm(ctx)
