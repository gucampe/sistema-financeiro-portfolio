from __future__ import annotations

import hashlib
import logging

from config.logging_utils import sanitize_log_field

logger = logging.getLogger("categorizacao.obs")


def _hash_key(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def _log(event: str, **fields) -> None:
    safe = {}
    for k, v in fields.items():
        if v is None or v == "":
            continue
        if k in ("merchant_key", "query_key", "matched_key", "keys"):
            safe[k] = _hash_key(str(v)) if k != "keys" else _hash_key(str(v))
        elif k == "match":
            safe[k] = sanitize_log_field(str(v), max_len=40)
        else:
            safe[k] = v
    parts = [f"{k}={v}" for k, v in safe.items()]
    logger.info("%s | %s", event, " ".join(parts))


def log_llm_blocked_by_memory(user_id: int, reason: str, merchant_key: str = "") -> None:
    _log("llm_blocked_by_memory", user_id=user_id, reason=reason, merchant_key=merchant_key)


def log_llm_blocked_by_human_memory(user_id: int, merchant_key: str, match: str) -> None:
    _log(
        "llm_blocked_by_human_memory",
        user_id=user_id,
        merchant_key=merchant_key,
        match=match,
    )


def log_merge_prevented_by_human_priority(
    user_id: int | None,
    hybrid_fonte: str,
    hybrid_conf: float,
) -> None:
    _log(
        "merge_prevented_by_human_priority",
        user_id=user_id,
        hybrid_fonte=hybrid_fonte,
        hybrid_conf=round(hybrid_conf, 4),
    )


def log_merge_llm_won(hybrid_fonte: str | None, hybrid_conf: float, llm_conf: float) -> None:
    _log(
        "llm_won_merge",
        hybrid_fonte=hybrid_fonte or "none",
        hybrid_conf=round(hybrid_conf, 4) if hybrid_conf else 0,
        llm_conf=round(llm_conf, 4),
    )


def log_merge_llm_lost(hybrid_fonte: str, hybrid_conf: float, llm_conf: float) -> None:
    _log(
        "llm_lost_merge",
        hybrid_fonte=hybrid_fonte,
        hybrid_conf=round(hybrid_conf, 4),
        llm_conf=round(llm_conf, 4),
    )


def log_human_memory_used(user_id: int, key: str, match_type: str) -> None:
    _log("human_memory_used", user_id=user_id, merchant_key=key, match=match_type)


def log_pix_similarity_match(user_id: int, query_key: str, matched_key: str) -> None:
    _log(
        "pix_similarity_match",
        user_id=user_id,
        query_key=query_key,
        matched_key=matched_key,
    )


def log_merchant_key_fragmentation(
    user_id: int,
    keys: list[str],
    descricao: str = "",
) -> None:
    _log(
        "merchant_key_fragmentation",
        user_id=user_id,
        keys="|".join(_hash_key(k) for k in keys[:5]),
    )


def log_learning_source(
    user_id: int,
    source: str,
    acao: str,
    merchant_key: str = "",
    fonte_sugestao: str = "",
) -> None:
    _log(
        "learning_source",
        user_id=user_id,
        source=source,
        acao=acao,
        merchant_key=merchant_key,
        fonte_sugestao=fonte_sugestao,
    )


def log_gate_decision(user_id: int | None, invoke: bool, reason: str) -> None:
    _log("gate_decision", user_id=user_id, invoke=invoke, reason=reason)
