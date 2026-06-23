from __future__ import annotations

import threading

from django.db import transaction

from categorizacao.services.learning import processar_feedback_transacao

_sugestoes_pendentes: dict[int, dict] = {}
_lock = threading.Lock()


def registrar_sugestao_pendente(transacao_id: int, dados: dict) -> None:
    with _lock:
        _sugestoes_pendentes[transacao_id] = dados


def consumir_sugestao_pendente(transacao_id: int) -> dict | None:
    with _lock:
        return _sugestoes_pendentes.pop(transacao_id, None)


def registrar_sugestoes_importacao(batch_id: str, sugestoes_por_indice: dict) -> None:
    with _lock:
        _sugestoes_pendentes[f"import:{batch_id}"] = sugestoes_por_indice


def consumir_sugestao_importacao(batch_id: str, indice: int) -> dict | None:
    with _lock:
        key = f"import:{batch_id}"
        batch = _sugestoes_pendentes.get(key, {})
        return batch.get(indice)
