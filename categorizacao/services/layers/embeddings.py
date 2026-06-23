from __future__ import annotations

import logging

from django.conf import settings

from categorizacao.types import ContextoCategorizacao, PredicaoCategorizacao

logger = logging.getLogger(__name__)

_modelo_embeddings = None


def _embeddings_habilitados() -> bool:
    return bool(getattr(settings, "ENABLE_CATEGORIZACAO_EMBEDDINGS", False))


def classificar_embeddings(ctx: ContextoCategorizacao) -> PredicaoCategorizacao | None:
    """Camada opcional (Fase 4): embeddings locais via sentence-transformers."""
    if not _embeddings_habilitados():
        return None
    global _modelo_embeddings
    try:
        if _modelo_embeddings is None:
            from sentence_transformers import SentenceTransformer

            model_name = getattr(
                settings,
                "CATEGORIZACAO_EMBEDDINGS_MODEL",
                "paraphrase-multilingual-MiniLM-L12-v2",
            )
            _modelo_embeddings = SentenceTransformer(model_name)
    except ImportError:
        logger.warning("sentence-transformers não instalado; camada embeddings desabilitada.")
        return None
    except Exception:
        logger.exception("Falha ao carregar modelo de embeddings")
        return None

    # Placeholder: integração completa exige índice vetorial por categorias do usuário.
    return None
