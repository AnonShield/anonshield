"""Benchmark runner: executes OCR engines against loaded samples.

Design principles:
- One engine at a time (memory constraint — VLMs can use 8+ GB VRAM)
- Resume from interruption via incremental JSON state
- Per-document result persisted immediately after inference
- Preprocessing pipeline injected at call site (not hardcoded)
- Engine load/unload managed explicitly to free GPU memory between engines
"""
import hashlib
import json
import logging
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from .datasets import Sample, NUMERIC_FIELDS
from .metrics import (
    DocumentResult,
    EngineAggregate,
    normalize,
    cer,
    wer,
    cer_no_diacritic,
    anls_score,
    field_f1,
    bootstrap_ci,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State persistence (resume support)
# ---------------------------------------------------------------------------

class RunState:
    """Persists per-document results and tracks which (engine, doc) pairs are done."""

    def __init__(self, state_path: Path) -> None:
        self._path = state_path
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        return {"results": [], "done": []}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))

    def is_done(self, engine: str, doc_id: str) -> bool:
        return f"{engine}::{doc_id}" in self._data["done"]

    def record(self, result: DocumentResult) -> None:
        key = f"{result.engine}::{result.doc_id}"
        if key not in self._data["done"]:
            self._data["done"].append(key)
            self._data["results"].append(asdict(result))
            self._save()

    @property
    def results(self) -> list[dict]:
        return self._data["results"]


# ---------------------------------------------------------------------------
# Hardware metadata (for reproducibility log)
# ---------------------------------------------------------------------------

def _hardware_meta() -> dict:
    meta: dict = {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "cpu": platform.processor() or "unknown",
    }
    try:
        import torch
        meta["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            meta["cuda_version"] = torch.version.cuda
            meta["gpu"] = torch.cuda.get_device_name(0)
            meta["gpu_vram_gb"] = round(
                torch.cuda.get_device_properties(0).total_memory / 1e9, 1
            )
    except ImportError:
        meta["cuda_available"] = False
    return meta


def _dataset_hash(samples: list[Sample]) -> str:
    h = hashlib.sha256()
    for s in sorted(samples, key=lambda x: x.id):
        h.update(s.id.encode())
        h.update(str(s.image_path.stat().st_size).encode())
    return h.hexdigest()[:16]


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_benchmark(
    engine_names: list[str],
    samples: list[Sample],
    output_dir: Path,
    *,
    preprocess: Callable[[bytes], bytes] | None = None,
    seed: int = 42,
    anls_threshold: float = 0.5,
    store_texts: bool = False,
) -> list[EngineAggregate]:
    """
    Run all engines over all samples, computing all metrics defined in
    METHODOLOGY.md §1. Persists results incrementally; resumes on restart.

    Args:
        engine_names:  OCR engine identifiers (must be registered in factory).
        samples:       Loaded Sample objects (from datasets.load_dataset).
        output_dir:    Where results/, logs/ and run_state.json are written.
        preprocess:    Optional callable: raw image bytes → preprocessed bytes.
        seed:          Random seed for bootstrap CI.
        anls_threshold: ANLS score threshold τ (default 0.5 per DocVQA standard).

    Returns:
        List of EngineAggregate, one per engine, sorted by mean CER ascending.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    state = RunState(output_dir / "run_state.json")

    run_meta = {
        "hardware": _hardware_meta(),
        "dataset_hash": _dataset_hash(samples),
        "n_samples": len(samples),
        "engines": engine_names,
        "seed": seed,
        "anls_threshold": anls_threshold,
        "preprocessing": preprocess.__name__ if preprocess else None,
    }
    (output_dir / "run_meta.json").write_text(
        json.dumps(run_meta, indent=2, ensure_ascii=False)
    )

    # Load OCR factory lazily (keeps test imports fast)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.anon.ocr.factory import get_ocr_engine

    for engine_name in engine_names:
        logger.info("=== Engine: %s ===", engine_name)
        try:
            engine = get_ocr_engine(engine_name)
        except (ValueError, RuntimeError) as exc:
            logger.warning("Skipping %s: %s", engine_name, exc)
            continue

        for sample in samples:
            if state.is_done(engine_name, sample.id):
                logger.debug("Skip (done): %s / %s", engine_name, sample.id)
                continue

            image_bytes = sample.image_path.read_bytes()
            if preprocess:
                try:
                    image_bytes = preprocess(image_bytes)
                except Exception as exc:
                    logger.warning("Preprocess failed for %s: %s", sample.id, exc)

            t0 = time.monotonic()
            try:
                raw_output = engine.extract_text(image_bytes)
            except Exception as exc:
                logger.error("Engine %s failed on %s: %s", engine_name, sample.id, exc)
                raw_output = ""
            latency = time.monotonic() - t0

            hyp = normalize(raw_output)
            ref = sample.reference_text   # already normalized by loader

            # --- CER / WER --------------------------------------------------
            doc_cer = cer(ref, hyp) if ref else 0.0
            doc_wer = wer(ref, hyp) if ref else 0.0
            doc_cer_nd = cer_no_diacritic(ref, hyp) if ref else 0.0

            # --- Field F1 (forms only) --------------------------------------
            f1_scores: dict[str, float] = {}
            if sample.fields and sample.doc_type == "form":
                pred_fields = _extract_fields(hyp, sample.fields)
                f1_scores = field_f1(
                    pred_fields,
                    sample.fields,
                    numeric_fields=NUMERIC_FIELDS,
                )

            # --- ANLS (field values as "questions") -------------------------
            doc_anls = 0.0
            if sample.fields:
                field_preds = list(_extract_fields(hyp, sample.fields).values())
                field_refs = [[v] for v in sample.fields.values()]
                scores = [
                    anls_score(p, g, anls_threshold)
                    for p, g in zip(field_preds, field_refs)
                ]
                doc_anls = sum(scores) / len(scores) if scores else 0.0

            result = DocumentResult(
                doc_id=sample.id,
                engine=engine_name,
                quality_tier=sample.quality_tier,
                doc_type=sample.doc_type,
                cer=doc_cer,
                wer=doc_wer,
                cer_no_diac=doc_cer_nd,
                latency_s=latency,
                field_f1=f1_scores,
                anls_score=doc_anls,
                _ref=ref if store_texts else "",
                _hyp=hyp if store_texts else "",
            )
            state.record(result)
            logger.info(
                "%s | %s | CER=%.4f WER=%.4f lat=%.2fs",
                engine_name, sample.id, doc_cer, doc_wer, latency,
            )

        # Free GPU memory between engines
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        del engine

    return _aggregate(state.results, seed=seed)


# ---------------------------------------------------------------------------
# Field extraction helper (best-effort substring search)
# ---------------------------------------------------------------------------

def _extract_fields(ocr_text: str, reference_fields: dict[str, str]) -> dict[str, str]:
    """
    Best-effort field extraction from raw OCR text.

    For each reference field, attempt to find the value in the OCR text using
    the reference value as a search key (substring or fuzzy). Returns a dict
    with the same keys as reference_fields; value is "" when not found.

    This is a heuristic for when no structured extractor is available.
    A downstream project may replace this with a regex- or VLM-based extractor.
    """
    extracted: dict[str, str] = {}
    for fname, ref_val in reference_fields.items():
        if not ref_val:
            extracted[fname] = ""
            continue
        # Digits-only search for numeric fields
        from .datasets import NUMERIC_FIELDS
        if fname in NUMERIC_FIELDS:
            digits_ref = re.sub(r"\D", "", ref_val)
            digits_hyp = re.sub(r"\D", "", ocr_text)
            extracted[fname] = ref_val if digits_ref and digits_ref in digits_hyp else ""
        else:
            # Case-insensitive substring search for text fields
            if ref_val.lower() in ocr_text.lower():
                extracted[fname] = ref_val
            else:
                extracted[fname] = ""
    return extracted


import re   # noqa: E402 — placed after _extract_fields to avoid forward ref issue


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate(raw_results: list[dict], *, seed: int) -> list[EngineAggregate]:
    from collections import defaultdict

    by_engine: dict[str, list[dict]] = defaultdict(list)
    for r in raw_results:
        by_engine[r["engine"]].append(r)

    aggregates = []
    for engine_name, docs in by_engine.items():
        cer_vals = [d["cer"] for d in docs if d["cer"] is not None]
        wer_vals = [d["wer"] for d in docs if d["wer"] is not None]
        nd_vals  = [d["cer_no_diac"] for d in docs]
        lat_vals = [d["latency_s"] for d in docs]
        anls_vals = [d["anls_score"] for d in docs]

        f1_vals = [
            d["field_f1"].get("macro_f1", 0.0)
            for d in docs if d.get("field_f1")
        ]

        # Stratified CER: key = "quality_tier::doc_type"
        strat: dict[str, list[float]] = defaultdict(list)
        for d in docs:
            strat_key = f"{d['quality_tier']}::{d['doc_type']}"
            strat[strat_key].append(d["cer"])
        stratified = {k: sum(v) / len(v) for k, v in strat.items()}

        ci_cer = bootstrap_ci(cer_vals, seed=seed) if len(cer_vals) >= 2 else (0.0, 0.0)
        ci_wer = bootstrap_ci(wer_vals, seed=seed) if len(wer_vals) >= 2 else (0.0, 0.0)

        aggregates.append(EngineAggregate(
            engine=engine_name,
            n_docs=len(docs),
            mean_cer=sum(cer_vals) / len(cer_vals) if cer_vals else 0.0,
            ci_cer=ci_cer,
            mean_wer=sum(wer_vals) / len(wer_vals) if wer_vals else 0.0,
            ci_wer=ci_wer,
            mean_cer_no_diac=sum(nd_vals) / len(nd_vals) if nd_vals else 0.0,
            macro_field_f1=sum(f1_vals) / len(f1_vals) if f1_vals else 0.0,
            mean_anls=sum(anls_vals) / len(anls_vals) if anls_vals else 0.0,
            mean_latency_s=sum(lat_vals) / len(lat_vals) if lat_vals else 0.0,
            stratified_cer=stratified,
        ))

    aggregates.sort(key=lambda a: a.mean_cer)
    return aggregates
