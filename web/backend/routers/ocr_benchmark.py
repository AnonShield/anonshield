"""GET /api/benchmark/ocr/* — serve OCR benchmark results to the dashboard.

Reads directly from `benchmark/ocr/results/` so results stream without an
intermediate DB. Cached per-file by mtime to keep large per-doc payloads cheap.
"""
import csv
import json
import logging
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/benchmark/ocr", tags=["ocr-benchmark"])

_here = Path(__file__).resolve()
for candidate in (_here.parents[0], *_here.parents[1:]):
    if (candidate / "benchmark" / "ocr").exists():
        _REPO_ROOT = candidate
        break
else:
    _REPO_ROOT = _here.parents[1]

_RESULTS_DIR = _REPO_ROOT / "benchmark" / "ocr" / "results"


def _mtime(path: Path) -> float:
    return path.stat().st_mtime if path.exists() else 0.0


@lru_cache(maxsize=16)
def _load_consolidated(mtime: float) -> list[dict]:
    """mtime arg is a cache key — content depends on file freshness."""
    del mtime
    csv_path = _RESULTS_DIR / "ablation_consolidated.csv"
    if not csv_path.exists():
        return []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append({
                "engine": r["engine"],
                "preprocess": r["preprocess"],
                "n_docs": int(r["n_docs"]),
                "mean_cer": float(r["mean_cer"]),
                "mean_wer": float(r["mean_wer"]),
                "macro_field_f1": float(r["macro_field_f1"]),
                "mean_latency_s": float(r["mean_latency_s"]),
            })
        return rows


@lru_cache(maxsize=32)
def _load_run_state(preprocess: str, mtime: float) -> list[dict]:
    """Load per-doc results for one preprocess step."""
    del mtime
    path = _RESULTS_DIR / preprocess / "run_state.json"
    if not path.exists():
        return []
    with path.open() as f:
        state = json.load(f)
    return state.get("results", [])


@lru_cache(maxsize=32)
def _load_run_meta(preprocess: str, mtime: float) -> dict | None:
    del mtime
    path = _RESULTS_DIR / preprocess / "run_meta.json"
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def _list_preprocess_dirs() -> list[str]:
    if not _RESULTS_DIR.exists():
        return []
    dirs = []
    for p in sorted(_RESULTS_DIR.iterdir()):
        if p.is_dir() and (p / "run_state.json").exists():
            dirs.append(p.name)
    return dirs


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/engines")
def engines_availability() -> dict:
    """Map of OCR engine name → bool (True if loadable in this image or its sidecars).

    The frontend uses this to filter the dropdown so users only see engines
    that will actually run. is_available() is import-only for local engines and
    a 5s GET /engines for sidecar-routed ones.
    """
    from src.anon.ocr.factory import _REGISTRY, _SIDECAR_ROUTES
    from src.anon.ocr.sidecar_engine import SidecarOCREngine

    out: dict[str, bool] = {}
    for name, cls in _REGISTRY.items():
        try:
            if cls().is_available():
                out[name] = True
                continue
        except Exception:
            pass
        url = _SIDECAR_ROUTES.get(name)
        if url:
            try:
                out[name] = SidecarOCREngine(name, url).is_available()
                continue
            except Exception:
                pass
        out[name] = False
    return {"engines": out}


@router.get("/summary")
def summary() -> dict:
    """Consolidated leaderboard across engines × preprocess steps.

    Returns rows from `ablation_consolidated.csv` plus available preprocess
    directories (even if consolidation hasn't been re-run yet).
    """
    csv_path = _RESULTS_DIR / "ablation_consolidated.csv"
    rows = _load_consolidated(_mtime(csv_path))
    available = _list_preprocess_dirs()

    # Merge in any preprocess dirs not yet in the consolidated CSV
    seen = {(r["engine"], r["preprocess"]) for r in rows}
    live_rows = []
    for step in available:
        results = _load_run_state(step, _mtime(_RESULTS_DIR / step / "run_state.json"))
        by_engine: dict[str, list[dict]] = {}
        for r in results:
            by_engine.setdefault(r["engine"], []).append(r)
        for engine, docs in by_engine.items():
            if (engine, step) in seen:
                continue
            cers = [d["cer"] for d in docs if d.get("cer") is not None]
            wers = [d["wer"] for d in docs if d.get("wer") is not None]
            lats = [d["latency_s"] for d in docs if d.get("latency_s") is not None]
            f1s = [d["field_f1"].get("macro_f1", 0.0) for d in docs
                   if isinstance(d.get("field_f1"), dict)]
            if not cers:
                continue
            live_rows.append({
                "engine": engine,
                "preprocess": step,
                "n_docs": len(cers),
                "mean_cer": sum(cers) / len(cers),
                "mean_wer": sum(wers) / len(wers) if wers else 0.0,
                "macro_field_f1": sum(f1s) / len(f1s) if f1s else 0.0,
                "mean_latency_s": sum(lats) / len(lats) if lats else 0.0,
                "in_progress": True,
            })

    return {
        "rows": rows + live_rows,
        "preprocess_steps": available,
        "engines": sorted({r["engine"] for r in rows + live_rows}),
    }


@router.get("/{preprocess}/meta")
def get_meta(preprocess: str) -> dict:
    """run_meta.json for a preprocess step."""
    path = _RESULTS_DIR / preprocess / "run_meta.json"
    meta = _load_run_meta(preprocess, _mtime(path))
    if meta is None:
        raise HTTPException(404, f"No run_meta.json for preprocess '{preprocess}'")
    return meta


@router.get("/{preprocess}/docs")
def list_docs(
    preprocess: str,
    engine: str | None = Query(None, description="Filter to one engine"),
    limit: int = Query(200, le=1000),
    offset: int = 0,
) -> dict:
    """List per-doc rows (without _ref/_hyp payload to stay light)."""
    path = _RESULTS_DIR / preprocess / "run_state.json"
    results = _load_run_state(preprocess, _mtime(path))
    if not results:
        raise HTTPException(404, f"No results for preprocess '{preprocess}'")

    filtered = [r for r in results if (engine is None or r["engine"] == engine)]
    total = len(filtered)
    page = filtered[offset:offset + limit]
    light = []
    for r in page:
        f1 = r.get("field_f1")
        macro = f1.get("macro_f1") if isinstance(f1, dict) else None
        light.append({
            "doc_id": r["doc_id"],
            "engine": r["engine"],
            "cer": r.get("cer"),
            "wer": r.get("wer"),
            "cer_no_diac": r.get("cer_no_diac"),
            "latency_s": r.get("latency_s"),
            "macro_f1": macro,
            "anls_score": r.get("anls_score"),
        })
    return {"total": total, "offset": offset, "limit": limit, "docs": light}


@router.get("/{preprocess}/docs/{doc_id}")
def get_doc(preprocess: str, doc_id: str, engine: str | None = None) -> dict:
    """Full per-doc record including `_ref` and `_hyp` for diff view.

    If `engine` is provided, returns that engine's record only; otherwise
    returns an object keyed by engine so the UI can show all hypotheses
    for the same ground truth side by side.
    """
    path = _RESULTS_DIR / preprocess / "run_state.json"
    results = _load_run_state(preprocess, _mtime(path))
    matches = [r for r in results if r["doc_id"] == doc_id]
    if not matches:
        raise HTTPException(404, f"No record for {doc_id} in '{preprocess}'")

    if engine:
        for r in matches:
            if r["engine"] == engine:
                return r
        raise HTTPException(404, f"No record for {doc_id}/{engine}")

    by_engine = {r["engine"]: r for r in matches}
    # Reference text is the same across engines — pull from any.
    reference = matches[0].get("_ref", "")
    return {
        "doc_id": doc_id,
        "reference": reference,
        "by_engine": {
            eng: {
                "hypothesis": r.get("_hyp", ""),
                "cer": r.get("cer"),
                "wer": r.get("wer"),
                "latency_s": r.get("latency_s"),
                "macro_f1": (r.get("field_f1") or {}).get("macro_f1"),
            }
            for eng, r in by_engine.items()
        },
    }
