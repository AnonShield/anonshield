"""Job state management via Redis."""
import json
import os
from typing import Any

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KEY_TTL = 3600       # 1h; user secret key
META_TTL = 7200      # 2h; job metadata
STATUS_TTL = 7200
if "ANON_JOB_TTL_SECONDS" in os.environ:
    KEY_TTL = META_TTL = STATUS_TTL = int(os.environ["ANON_JOB_TTL_SECONDS"])
    if STATUS_TTL < 0:
        raise ValueError("ANON_JOB_TTL_SECONDS must be non-negative; use 0 for no expiry.")

_pool: redis.ConnectionPool | None = None


def _client() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
    return redis.Redis(connection_pool=_pool)


# ── Key management ─────────────────────────────────────────────────────────────

def store_key(job_id: str, key: str) -> None:
    _store(f"job:{job_id}:key", key, KEY_TTL)


def _store(name: str, value: str, ttl: int) -> None:
    if ttl:
        _client().setex(name, ttl, value)
    else:
        _client().set(name, value)


def pop_key(job_id: str) -> str:
    r = _client()
    key = r.get(f"job:{job_id}:key") or ""
    r.delete(f"job:{job_id}:key")
    return key


# ── Status ─────────────────────────────────────────────────────────────────────

def set_status(job_id: str, status: str, **extra: Any) -> None:
    data = {"status": status, **extra}
    _store(f"job:{job_id}:status", json.dumps(data), STATUS_TTL)


def get_status(job_id: str) -> dict | None:
    raw = _client().get(f"job:{job_id}:status")
    return json.loads(raw) if raw else None


# ── Metadata ───────────────────────────────────────────────────────────────────

def store_meta(job_id: str, meta: dict) -> None:
    _store(f"job:{job_id}:meta", json.dumps(meta), META_TTL)


def get_meta(job_id: str) -> dict | None:
    raw = _client().get(f"job:{job_id}:meta")
    return json.loads(raw) if raw else None


def delete_job_keys(job_id: str) -> None:
    r = _client()
    r.delete(f"job:{job_id}:key", f"job:{job_id}:status", f"job:{job_id}:meta")


# ── Worker warm-up ─────────────────────────────────────────────────────────────
# A worker loading the NER model takes no job until it is done, so a job queued
# meanwhile waits for the model, not for another file; the interface says which.
# The TTL clears the flag if the worker dies while loading.
WARMING_KEY = "worker:warming"
WARMING_TTL = 1800


def set_warming(on: bool) -> None:
    try:
        if on:
            _client().setex(WARMING_KEY, WARMING_TTL, "1")
        else:
            _client().delete(WARMING_KEY)
    except redis.RedisError:
        pass  # only the waiting message depends on it


def warming() -> bool:
    try:
        return bool(_client().exists(WARMING_KEY))
    except redis.RedisError:
        return False
