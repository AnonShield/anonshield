"""Job state management via Redis."""
import json
import os
from typing import Any

import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KEY_TTL = 3600       # 1h — user secret key
META_TTL = 7200      # 2h — job metadata
STATUS_TTL = 7200

_pool: redis.ConnectionPool | None = None


def _client() -> redis.Redis:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
    return redis.Redis(connection_pool=_pool)


# ── Key management ─────────────────────────────────────────────────────────────

def store_key(job_id: str, key: str) -> None:
    _client().setex(f"job:{job_id}:key", KEY_TTL, key)


def pop_key(job_id: str) -> str:
    r = _client()
    key = r.get(f"job:{job_id}:key") or ""
    r.delete(f"job:{job_id}:key")
    return key


# ── Status ─────────────────────────────────────────────────────────────────────

def set_status(job_id: str, status: str, **extra: Any) -> None:
    data = {"status": status, **extra}
    _client().setex(f"job:{job_id}:status", STATUS_TTL, json.dumps(data))


def get_status(job_id: str) -> dict | None:
    raw = _client().get(f"job:{job_id}:status")
    return json.loads(raw) if raw else None


# ── Metadata ───────────────────────────────────────────────────────────────────

def store_meta(job_id: str, meta: dict) -> None:
    _client().setex(f"job:{job_id}:meta", META_TTL, json.dumps(meta))


def get_meta(job_id: str) -> dict | None:
    raw = _client().get(f"job:{job_id}:meta")
    return json.loads(raw) if raw else None


def delete_job_keys(job_id: str) -> None:
    r = _client()
    r.delete(f"job:{job_id}:key", f"job:{job_id}:status", f"job:{job_id}:meta")
