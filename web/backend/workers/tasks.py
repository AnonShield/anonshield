"""Celery tasks — anonymization jobs."""
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
        secret_key=key,
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


def _execute(job_id: str) -> dict:
    meta = job_service.get_meta(job_id)
    if not meta:
        raise RuntimeError(f"No metadata for job {job_id}")

    key = job_service.pop_key(job_id)
    job_service.set_status(job_id, "running", progress=0)

    input_file = storage.input_path(job_id, meta["ext"])
    out_dir = storage.output_dir(job_id)
    t0 = time.monotonic()

    try:
        if meta["ext"] == "zip":
            result = _process_zip(input_file, out_dir, meta, key)
        else:
            result = _anonymize(input_file, out_dir, meta, key)

        ms = (time.monotonic() - t0) * 1000
        storage.delete_input(job_id)
        out_file = storage.get_output_file(job_id)
        output_size = out_file.stat().st_size if out_file else 0
        job_service.set_status(job_id, "done", output_size_bytes=output_size, result=result)

        # Record job metrics (best-effort, never blocks)
        try:
            import json
            from services.metrics import record_job
            queue = "gpu" if meta.get("strategy", "filtered") in {"filtered", "standalone", "hybrid", "presidio"} else "fast"
            record_job(
                job_id=job_id,
                file_ext=meta.get("ext"),
                file_b=meta.get("size"),
                strategy=meta.get("strategy"),
                lang=meta.get("lang"),
                queue=queue,
                entity_cnt=result.get("entity_count"),
                entity_counts=result.get("entity_counts"),
                ms=ms,
            )
        except Exception:
            pass

        return result
    except Exception as exc:
        storage.delete_input(job_id)
        job_service.set_status(job_id, "error", message=str(exc))
        raise


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
