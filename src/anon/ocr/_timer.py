"""Thread-local OCR call timer.

Worker wraps each job with reset() → anonymize → snapshot() to attribute
elapsed OCR time to the engine that was used for that job. Thread-local so
Celery's prefork model (one worker per process) records cleanly.
"""
import threading

_state = threading.local()


def _store() -> dict:
    s = getattr(_state, "s", None)
    if s is None:
        s = {"ms": 0.0, "calls": 0}
        _state.s = s
    return s


def reset() -> None:
    _state.s = {"ms": 0.0, "calls": 0}


def add(ms: float) -> None:
    s = _store()
    s["ms"] += ms
    s["calls"] += 1


def snapshot() -> dict:
    s = _store()
    return {"ms": round(s["ms"], 2), "calls": s["calls"]}
