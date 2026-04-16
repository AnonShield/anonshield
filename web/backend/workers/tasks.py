"""Celery tasks — anonymization jobs."""
import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from celery.utils.log import get_task_logger

from workers.celery_app import app
from services import job_service, storage

logger = get_task_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
if not (_REPO_ROOT / "anon.py").exists():
    _REPO_ROOT = Path(__file__).resolve().parents[3]

if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _anonymize(input_file: Path, out_dir: Path, meta: dict, key: str) -> dict:
    from src.anon.api import anonymize_file
    return anonymize_file(
        input_path=input_file,
        output_dir=out_dir,
        strategy=meta.get("strategy", "filtered"),
        lang=meta.get("lang", "en"),
        entities=meta.get("entities") or None,
        custom_patterns=meta.get("custom_patterns") or None,
        ocr_engine=meta.get("ocr_engine", "tesseract"),
        ocr_preprocess=meta.get("ocr_preprocess") or None,
        secret_key=key,
        anonymization_config=meta.get("anonymization_config"),
        slug_length=meta["slug_length"] if meta.get("slug_length") is not None else 8,
        transformer_model=meta.get("model") or "Davlan/xlm-roberta-base-ner-hrl",
        ner_score_threshold=meta.get("ner_score_threshold"),
        ner_aggregation_strategy=meta.get("ner_aggregation_strategy"),
    )


def _process_zip(zip_path: Path, out_dir: Path, meta: dict, key: str) -> dict:
    stats: dict = {"files_processed": 0, "files_skipped": 0, "entity_count": 0}
    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = Path(tmp) / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, "r") as zf:
            total = sum(i.file_size for i in zf.infolist())
            if total > 10 * 1024 ** 3:
                raise ValueError("ZIP content exceeds 10 GB limit")
            for member in zf.infolist():
                target = (extract_dir / member.filename).resolve()
                if not str(target).startswith(str(extract_dir)):
                    raise ValueError(f"Path traversal blocked: {member.filename}")
            zf.extractall(extract_dir)

        repack_dir = Path(tmp) / "repack"
        repack_dir.mkdir()

        for src in extract_dir.rglob("*"):
            if not src.is_file():
                continue
            per_out = Path(tmp) / f"out_{src.stem}"
            per_out.mkdir(exist_ok=True)
            try:
                result = _anonymize(src, per_out, meta, key)
                processed = list(per_out.iterdir())
                if processed:
                    shutil.copy2(processed[0], repack_dir / processed[0].name)
                stats["files_processed"] += 1
                stats["entity_count"] += result.get("entity_count", 0)
            except Exception as exc:
                logger.warning("Skipping %s: %s", src.name, exc)
                stats["files_skipped"] += 1

        zip_out = out_dir / f"anon_{zip_path.stem}.zip"
        with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in repack_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.name)

    return stats


def _release_vram() -> None:
    """Best-effort VRAM release between jobs (only runs when VLM engines were used).
    PyTorch's caching allocator keeps freed tensors in a pool; empty_cache returns
    that pool to the driver so the next engine swap doesn't stack models."""
    try:
        import gc, torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except Exception:
        pass


def _execute(job_id: str) -> dict:
    meta = job_service.get_meta(job_id)
    if not meta:
        raise RuntimeError(f"No metadata for job {job_id}")

    key = job_service.pop_key(job_id)
    job_service.set_status(job_id, "running", progress=0)

    input_file = storage.input_path(job_id, meta["ext"])
    out_dir = storage.output_dir(job_id)
    t0 = time.monotonic()

    # Reset OCR timer so we can attribute elapsed OCR time to the engine
    # used for this specific job (thread-local; clean under Celery prefork).
    try:
        from src.anon.ocr import _timer as _ocr_timer
        _ocr_timer.reset()
    except Exception:
        _ocr_timer = None  # type: ignore

    try:
        if meta["ext"] == "zip":
            result = _process_zip(input_file, out_dir, meta, key)
        else:
            result = _anonymize(input_file, out_dir, meta, key)

        ms = (time.monotonic() - t0) * 1000
        ocr_stats = _ocr_timer.snapshot() if _ocr_timer else {"ms": 0.0, "calls": 0}
        storage.delete_input(job_id)
        out_file = storage.get_output_file(job_id)
        output_size = out_file.stat().st_size if out_file else 0
        job_service.set_status(job_id, "done", output_size_bytes=output_size, result=result)

        # Record job metrics (best-effort, never blocks)
        try:
            from services.metrics import record_job
            record_job(
                job_id=job_id,
                file_ext=meta.get("ext"),
                file_b=meta.get("size"),
                strategy=meta.get("strategy"),
                lang=meta.get("lang"),
                model=meta.get("model"),
                queue="fast",
                entity_cnt=result.get("entity_count"),
                entity_counts=result.get("entity_counts"),
                ms=ms,
                ocr_engine=meta.get("ocr_engine") if ocr_stats["calls"] > 0 else None,
                ocr_ms=ocr_stats["ms"] if ocr_stats["calls"] > 0 else None,
                ocr_calls=ocr_stats["calls"] if ocr_stats["calls"] > 0 else None,
            )
        except Exception:
            pass

        return result
    except Exception as exc:
        storage.delete_input(job_id)
        job_service.set_status(job_id, "error", message=str(exc))
        raise
    finally:
        # Release VRAM held by cached VLM engines. No-op when no GPU / no VLM
        # was used. Runs even when WORKER_MAX_TASKS_PER_CHILD=0 (warm mode) so
        # switching engines between jobs doesn't stack models in VRAM.
        if os.getenv("ANON_RELEASE_VRAM_PER_JOB", "1") == "1":
            _release_vram()


@app.task(bind=True, name="workers.tasks.process_job", queue="gpu")
def process_job(self, job_id: str) -> dict:  # noqa: ARG001
    return _execute(job_id)


@app.task(bind=True, name="workers.tasks.process_job_fast", queue="fast")
def process_job_fast(self, job_id: str) -> dict:  # noqa: ARG001
    return _execute(job_id)


@app.task(name="workers.tasks.sweep_jobs")
def sweep_jobs() -> int:
    deleted = storage.sweep_orphaned_jobs(max_age_seconds=7200)
    logger.info("Swept %d orphaned jobs", deleted)
    return deleted
