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
    model       TEXT,
    queue       TEXT,
    entity_cnt  INTEGER,
    entity_json TEXT,
    ms          REAL,
    throughput_bps REAL,
    ocr_engine  TEXT,
    ocr_ms      REAL,
    ocr_calls   INTEGER
);
CREATE INDEX IF NOT EXISTS req_ts  ON req(ts);
CREATE INDEX IF NOT EXISTS job_ts  ON job(ts);
CREATE INDEX IF NOT EXISTS job_str ON job(strategy);
CREATE INDEX IF NOT EXISTS job_mdl ON job(model);
"""



def init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock, sqlite3.connect(str(_DB_PATH)) as c:
        c.executescript(_DDL)
        # Migrate existing DBs: add missing columns one-by-one (idempotent).
        cols = {r[1] for r in c.execute("PRAGMA table_info(job)")}
        for col, decl in [
            ("model",       "TEXT"),
            ("ocr_engine",  "TEXT"),
            ("ocr_ms",      "REAL"),
            ("ocr_calls",   "INTEGER"),
        ]:
            if col not in cols:
                try:
                    c.execute(f"ALTER TABLE job ADD COLUMN {col} {decl}")
                except Exception:
                    pass


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
               strategy: str | None, lang: str | None, model: str | None,
               queue: str | None, entity_cnt: int | None,
               entity_counts: dict | None, ms: float | None,
               ocr_engine: str | None = None, ocr_ms: float | None = None,
               ocr_calls: int | None = None) -> None:
    try:
        throughput = None
        if ms and file_b and ms > 0:
            throughput = round(file_b / (ms / 1000), 2)
        with _lock, sqlite3.connect(str(_DB_PATH)) as c:
            c.execute(
                "INSERT INTO job(ts,job_id,file_ext,file_b,strategy,lang,model,queue,"
                "entity_cnt,entity_json,ms,throughput_bps,ocr_engine,ocr_ms,ocr_calls)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), job_id, file_ext, file_b, strategy, lang, model, queue,
                 entity_cnt, json.dumps(entity_counts) if entity_counts else None,
                 ms and round(ms, 2), throughput,
                 ocr_engine, ocr_ms and round(ocr_ms, 2), ocr_calls),
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


def record_job(job_id: str, file_ext: str | None = None, file_b: int | None = None,
               strategy: str | None = None, lang: str | None = None,
               model: str | None = None, queue: str | None = None,
               entity_cnt: int | None = None, entity_counts: dict | None = None,
               ms: float | None = None, ocr_engine: str | None = None,
               ocr_ms: float | None = None, ocr_calls: int | None = None) -> None:
    _pool.submit(_write_job, job_id, file_ext, file_b, strategy, lang, model,
                 queue, entity_cnt, entity_counts, ms, ocr_engine, ocr_ms, ocr_calls)


# ── Middleware ────────────────────────────────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402


_UUID_RE = __import__('re').compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', __import__('re').I
)


def _normalize_path(path: str) -> str:
    """Replace UUIDs in paths with {id} so routes group correctly."""
    return _UUID_RE.sub('{id}', path)


class MetricsMiddleware(BaseHTTPMiddleware):
    _SKIP = {"/api/health", "/api/metrics", "/api/config"}

    async def dispatch(self, request, call_next):
        if request.url.path in self._SKIP:
            return await call_next(request)
        t0 = time.monotonic()
        req_b = int(request.headers.get("content-length", 0))
        response = await call_next(request)
        ms = (time.monotonic() - t0) * 1000
        resp_b = int(response.headers.get("content-length", 0))
        record_request(request.method, _normalize_path(request.url.path),
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
                       ROUND(AVG(file_b)) avg_file_b,
                       SUM(entity_cnt) total_entities,
                       ROUND(AVG(throughput_bps)) avg_throughput_bps
                FROM job WHERE file_ext IS NOT NULL
                GROUP BY file_ext ORDER BY n DESC
            """)
            by_model = _rows(c, """
                SELECT model, COUNT(*) n, ROUND(AVG(ms),2) avg_ms,
                       SUM(entity_cnt) total_entities,
                       ROUND(AVG(throughput_bps)) avg_throughput_bps
                FROM job WHERE model IS NOT NULL
                GROUP BY model ORDER BY n DESC
            """)
            by_ocr_engine = _rows(c, """
                SELECT ocr_engine, COUNT(*) n,
                       ROUND(AVG(ocr_ms),2) avg_ocr_ms,
                       ROUND(MAX(ocr_ms),2) max_ocr_ms,
                       ROUND(MIN(ocr_ms),2) min_ocr_ms,
                       SUM(ocr_calls) total_calls,
                       ROUND(AVG(ocr_ms * 1.0 / NULLIF(ocr_calls,0)),2) avg_ms_per_page
                FROM job WHERE ocr_engine IS NOT NULL
                GROUP BY ocr_engine ORDER BY n DESC
            """)
            by_endpoint = _rows(c, """
                SELECT method, path, COUNT(*) n,
                       ROUND(AVG(ms),2) avg_ms, ROUND(MIN(ms),2) min_ms, ROUND(MAX(ms),2) max_ms
                FROM req GROUP BY method, path ORDER BY n DESC
            """)
            recent_jobs = _rows(c, """
                SELECT ts, job_id, file_ext, file_b, strategy, lang, model,
                       entity_cnt, entity_json, ms, throughput_bps,
                       ocr_engine, ocr_ms, ocr_calls
                FROM job ORDER BY ts DESC LIMIT 50
            """)
            # Aggregate entity counts from JSON blobs
            entity_rows = _rows(c, "SELECT entity_json FROM job WHERE entity_json IS NOT NULL")
            entity_totals: dict[str, int] = {}
            for row in entity_rows:
                try:
                    counts = json.loads(row["entity_json"])
                    if isinstance(counts, dict):
                        for k, v in counts.items():
                            entity_totals[k] = entity_totals.get(k, 0) + int(v)
                except Exception:
                    pass
            by_entity_type = sorted(
                [{"entity": k, "n": v} for k, v in entity_totals.items()],
                key=lambda x: x["n"], reverse=True
            )
            return {
                "requests": {"aggregate": req_agg, "by_endpoint": by_endpoint},
                "jobs": {
                    "aggregate": job_agg,
                    "by_strategy": by_strategy,
                    "by_format": by_ext,
                    "by_model": by_model,
                    "by_ocr_engine": by_ocr_engine,
                    "by_entity_type": by_entity_type,
                    "recent": recent_jobs,
                },
            }
    except Exception as e:
        return {"error": str(e)}
