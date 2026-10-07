"""Celery tasks: anonymization jobs."""
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from contextlib import contextmanager
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
        entities=meta.get("entities"),
        allow_list=meta.get("allow_list"),
        preserve_entities=meta.get("preserve_entities"),
        custom_patterns=meta.get("custom_patterns") or None,
        ocr_engine=meta.get("ocr_engine", "tesseract"),
        secret_key=key,
        anonymization_config=meta.get("anonymization_config"),
        slug_length=meta["slug_length"] if meta.get("slug_length") is not None else 8,
        transformer_model=meta.get("model") or "Davlan/xlm-roberta-base-ner-hrl",
        ner_score_threshold=meta.get("ner_score_threshold"),
        ner_aggregation_strategy=meta.get("ner_aggregation_strategy"),
        force_large_xml=os.getenv("ANON_FORCE_LARGE_XML", "false").lower() == "true",
    )


_PASS_RE = re.compile(r"Pass (\d+)/(\d+)")
_PROGRESS_EVERY_S = 2.0


@contextmanager
def _progress_to_status(job_id: str):
    """Publish the engine's file progress bars (tqdm) as the job's progress.

    "Pass k/n" bars map to their share of the run; the inner entity-detection
    bars are ignored. Progress never goes back, stays below 100 until the job
    is done, and is written at most every two seconds.
    """
    from tqdm import tqdm

    update, iterate = tqdm.update, tqdm.__iter__
    state = {"sent": 0, "at": 0.0}

    def report(bar, done: int) -> None:
        desc = str(getattr(bar, "desc", "") or "")
        if not bar.total or desc.startswith("Detecting Entities"):
            return
        fraction = min(1.0, done / bar.total)
        match = _PASS_RE.search(desc)
        if match:
            k, n = int(match.group(1)), int(match.group(2))
            fraction = (k - 1 + fraction) / n
        percent = min(99, int(100 * fraction))
        now = time.monotonic()
        if percent > state["sent"] and now - state["at"] >= _PROGRESS_EVERY_S:
            state.update(sent=percent, at=now)
            job_service.set_status(job_id, "running", progress=percent)

    def counted_update(self, n=1):
        self._anon_done = getattr(self, "_anon_done", 0) + (n or 0)
        report(self, self._anon_done)
        return update(self, n)

    def counted_iter(self):
        for done, item in enumerate(iterate(self), 1):
            report(self, done)
            yield item

    tqdm.update, tqdm.__iter__ = counted_update, counted_iter
    try:
        yield
    finally:
        tqdm.update, tqdm.__iter__ = update, iterate


def _public_error(exc: Exception, path: Path, name: str) -> str:
    """Engine errors name the worker's copy of the file; show the user's name instead."""
    return str(exc).replace(str(path), name)


def _process_zip(zip_path: Path, out_dir: Path, meta: dict, key: str) -> dict:
    from src.anon.processors import ProcessorRegistry
    stats: dict = {"files_processed": 0, "files_skipped": 0, "skipped_files": [], "entity_count": 0}
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        extract_dir = Path(tmp) / "extracted"
        extract_dir.mkdir()

        with zipfile.ZipFile(zip_path, "r") as zf:
            total = sum(i.file_size for i in zf.infolist())
            limit_mb = int(os.getenv("ANON_MAX_ZIP_SIZE_MB", "10240"))
            if limit_mb > 0 and total > limit_mb * 1024 ** 2:
                raise ValueError(f"ZIP content exceeds {limit_mb} MB limit")
            for member in zf.infolist():
                target = (extract_dir / member.filename).resolve()
                if not target.is_relative_to(extract_dir):
                    raise ValueError(f"Path traversal blocked: {member.filename}")
            zf.extractall(extract_dir)

        repack_dir = Path(tmp) / "repack"
        repack_dir.mkdir()

        for src in sorted(extract_dir.rglob("*")):
            if not src.is_file():
                continue
            relative = src.relative_to(extract_dir)
            if relative.parts[0] == "__MACOSX" or src.name == ".DS_Store":
                continue
            if src.suffix.lower() not in ProcessorRegistry._processors:
                stats["files_skipped"] += 1
                stats["skipped_files"].append(str(relative))
                continue
            per_out = Path(tmp) / "processed" / relative
            per_out.mkdir(parents=True, exist_ok=True)
            try:
                result = _anonymize(src, per_out, meta, key)
                processed = list(per_out.iterdir())
                if len(processed) != 1:
                    raise ValueError("Processing did not produce one output file.")
                destination = repack_dir / relative.parent / processed[0].name
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination.exists():
                    raise ValueError(f"Output filename collision: {destination.name}")
                shutil.copy2(processed[0], destination)
                stats["files_processed"] += 1
                stats["entity_count"] += result.get("entity_count", 0)
            except Exception as exc:
                logger.warning("Could not process %s: %s", relative, exc)
                message = _public_error(exc, src, str(relative))
                failures.append(message if str(relative) in message else f"{relative}: {message}")

        if failures:
            shown = "; ".join(failures[:3]) + ("; ..." if len(failures) > 3 else "")
            raise ValueError(f"{len(failures)} file(s) in the ZIP could not be processed, so no archive was published. Fix them and retry. {shown}")
        if not stats["files_processed"]:
            raise ValueError("The ZIP has no files in a supported format (" + " ".join(sorted(ProcessorRegistry._processors)) + ").")
        stats["skipped_files"] = stats["skipped_files"][:20]

        zip_out = out_dir / f"anon_{zip_path.stem}.zip"
        with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in repack_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(repack_dir))

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
        with _progress_to_status(job_id):
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
                model=None if meta.get("strategy") == "regex" else meta.get("model"),
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
        job_service.set_status(job_id, "error", message=_public_error(exc, input_file, meta.get("filename") or input_file.name))
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
