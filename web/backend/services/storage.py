"""File lifecycle management — zero persistence guarantee.

ANON_JOBS_DIR env var sets the root directory for job files.
Default: /tmp/anon/jobs (fine for dev/demo on shared servers).
No dedicated partition required — the sweep task keeps disk usage bounded.
"""
import os
import shutil
import time
from pathlib import Path

JOBS_ROOT = Path(os.getenv("ANON_JOBS_DIR", "/tmp/anon/jobs"))


def job_dir(job_id: str) -> Path:
    return JOBS_ROOT / job_id


def input_path(job_id: str, ext: str) -> Path:
    return job_dir(job_id) / f"input.{ext}"


def output_dir(job_id: str) -> Path:
    return job_dir(job_id) / "output"


def create_job_dir(job_id: str) -> Path:
    d = job_dir(job_id)
    d.mkdir(parents=True, exist_ok=True)
    output_dir(job_id).mkdir(exist_ok=True)
    return d


def delete_input(job_id: str) -> None:
    d = job_dir(job_id)
    for f in d.iterdir():
        if f.name.startswith("input."):
            f.unlink(missing_ok=True)


def delete_output(job_id: str) -> None:
    od = output_dir(job_id)
    if od.exists():
        shutil.rmtree(od, ignore_errors=True)


def delete_job(job_id: str) -> None:
    d = job_dir(job_id)
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def get_output_file(job_id: str) -> Path | None:
    od = output_dir(job_id)
    if not od.exists():
        return None
    files = list(od.iterdir())
    return files[0] if files else None


def sweep_orphaned_jobs(max_age_seconds: int = 1800) -> int:
    """Delete jobs older than max_age_seconds. Returns count deleted."""
    if not JOBS_ROOT.exists():
        return 0
    now = time.time()
    deleted = 0
    for d in JOBS_ROOT.iterdir():
        if d.is_dir() and (now - d.stat().st_mtime) > max_age_seconds:
            shutil.rmtree(d, ignore_errors=True)
            deleted += 1
    return deleted
