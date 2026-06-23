from __future__ import annotations

import time

_FAILURE_THRESHOLD = 5
_COOLDOWN_S = 60
_state = {"failures": 0, "open_until": 0.0}


def record_success() -> None:
    _state["failures"] = 0
    _state["open_until"] = 0.0


def record_failure() -> None:
    _state["failures"] = _state.get("failures", 0) + 1
    if _state["failures"] >= _FAILURE_THRESHOLD:
        _state["open_until"] = time.time() + _COOLDOWN_S


def is_circuit_open() -> bool:
    if time.time() < _state.get("open_until", 0):
        return True
    if _state.get("open_until", 0) and time.time() >= _state["open_until"]:
        _state["failures"] = 0
        _state["open_until"] = 0.0
    return False
