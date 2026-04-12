"""Lightweight SQLite metrics collector — never crashes the app."""
import json
import os
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import asyncio

_DB_PATH = Path(os.getenv("ANON_METRICS_DB", "/tmp/anon_metrics.db"))
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="metrics")

# ── Schema ────────────────────────────────────────────────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS req (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL    NOT NULL,
    method  TEXT    NOT NULL,
    path    TEXT    NOT NULL,
    status  INTEGER,
    ms      REAL,
    req_b   INTEGER DEFAULT 0,
    resp_b  INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS job (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL    NOT NULL,
    job_id      TEXT,
    file_ext    TEXT,
    file_b      INTEGER,
    strategy    TEXT,
    lang        TEXT,
    queue       TEXT,
    entity_cnt  INTEGER,
    entity_json TEXT,
    ms          REAL,
    throughput_bps REAL
);
CREATE INDEX IF NOT EXISTS req_ts  ON req(ts);
CREATE INDEX IF NOT EXISTS job_ts  ON job(ts);
CREATE INDEX IF NOT EXISTS job_str ON job(strategy);
"""


def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, sqlite3.connect(str(_DB_PATH)) as c:
        c.executescript(_DDL)


# ── Writers ───────────────────────────────────────────────────────────────────

def _write_request(method: str, path: str, status: int,
                   ms: float, req_b: int, resp_b: int) -> None:
    try:
        with _lock, sqlite3.connect(str(_DB_PATH)) as c:
            c.execute(
                "INSERT INTO req(ts,method,path,status,ms,req_b,resp_b)"
                " VALUES(?,?,?,?,?,?,?)",
                (time.time(), method, path, status, round(ms, 2), req_b, resp_b),
            )
    except Exception:
        pass


def _write_job(job_id: str, file_ext: str | None, file_b: int | None,
               strategy: str | None, lang: str | None, queue: str | None,
               entity_cnt: int | None, entity_counts: dict | None,
               ms: float | None) -> None:
    try:
        throughput = None
        if ms and file_b and ms > 0:
            throughput = round(file_b / (ms / 1000), 2)
        with _lock, sqlite3.connect(str(_DB_PATH)) as c:
            c.execute(
                "INSERT INTO job(ts,job_id,file_ext,file_b,strategy,lang,queue,"
                "entity_cnt,entity_json,ms,throughput_bps) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), job_id, file_ext, file_b, strategy, lang, queue,
                 entity_cnt, json.dumps(entity_counts) if entity_counts else None,
                 ms and round(ms, 2), throughput),
            )
    except Exception:
        pass


# ── Async-safe helpers ────────────────────────────────────────────────────────

def record_request(method: str, path: str, status: int,
                   ms: float, req_b: int = 0, resp_b: int = 0) -> None:
    try:
        loop = asyncio.get_event_loop()
        loop.run_in_executor(_pool, _write_request, method, path, status, ms, req_b, resp_b)
    except RuntimeError:
        _write_request(method, path, status, ms, req_b, resp_b)


def record_job(**kw) -> None:
    _pool.submit(_write_job, **kw)


# ── Middleware ────────────────────────────────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402


class MetricsMiddleware(BaseHTTPMiddleware):
    _SKIP = {"/api/health", "/api/metrics"}

    async def dispatch(self, request, call_next):
        if request.url.path in self._SKIP:
            return await call_next(request)
        t0 = time.monotonic()
        req_b = int(request.headers.get("content-length", 0))
        response = await call_next(request)
        ms = (time.monotonic() - t0) * 1000
        resp_b = int(response.headers.get("content-length", 0))
        record_request(request.method, request.url.path,
                       response.status_code, ms, req_b, resp_b)
        return response


# ── Queries ───────────────────────────────────────────────────────────────────

def _row(c: sqlite3.Connection, sql: str, *args) -> dict:
    r = c.execute(sql, args).fetchone()
    return dict(r) if r else {}


def _rows(c: sqlite3.Connection, sql: str, *args) -> list[dict]:
    return [dict(r) for r in c.execute(sql, args).fetchall()]


def get_summary() -> dict:
    try:
        with sqlite3.connect(str(_DB_PATH)) as c:
            c.row_factory = sqlite3.Row
            req_agg = _row(c, """
                SELECT COUNT(*) n, ROUND(AVG(ms),2) avg_ms,
                       ROUND(MAX(ms),2) max_ms, ROUND(MIN(ms),2) min_ms,
                       SUM(req_b) total_req_b, SUM(resp_b) total_resp_b
                FROM req
            """)
            job_agg = _row(c, """
                SELECT COUNT(*) n, ROUND(AVG(ms),2) avg_ms, ROUND(MAX(ms),2) max_ms,
                       SUM(file_b) total_file_b, ROUND(AVG(file_b)) avg_file_b,
                       SUM(entity_cnt) total_entities,
                       ROUND(AVG(throughput_bps)) avg_throughput_bps
                FROM job
            """)
            by_strategy = _rows(c, """
                SELECT strategy, COUNT(*) n, ROUND(AVG(ms),2) avg_ms,
                       ROUND(AVG(file_b)) avg_file_b, SUM(entity_cnt) total_entities,
                       ROUND(AVG(throughput_bps)) avg_throughput_bps
                FROM job WHERE strategy IS NOT NULL
                GROUP BY strategy ORDER BY n DESC
            """)
            by_ext = _rows(c, """
                SELECT file_ext, COUNT(*) n, ROUND(AVG(ms),2) avg_ms,
                       ROUND(AVG(file_b)) avg_file_b
                FROM job WHERE file_ext IS NOT NULL
                GROUP BY file_ext ORDER BY n DESC
            """)
            by_endpoint = _rows(c, """
                SELECT method, path, COUNT(*) n,
                       ROUND(AVG(ms),2) avg_ms, ROUND(MIN(ms),2) min_ms, ROUND(MAX(ms),2) max_ms
                FROM req GROUP BY method, path ORDER BY n DESC
            """)
            recent_jobs = _rows(c, """
                SELECT ts, job_id, file_ext, file_b, strategy, lang, entity_cnt,
                       entity_json, ms, throughput_bps
                FROM job ORDER BY ts DESC LIMIT 50
            """)
            return {
                "requests": {"aggregate": req_agg, "by_endpoint": by_endpoint},
                "jobs": {
                    "aggregate": job_agg,
                    "by_strategy": by_strategy,
                    "by_format": by_ext,
                    "recent": recent_jobs,
                },
            }
    except Exception as e:
        return {"error": str(e)}
