"""Local uploads use disk capacity, with production limits still enforceable."""
import errno
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    from main import app
    from services import job_service, limiter, storage
    from workers.celery_app import app as celery

    monkeypatch.setattr(limiter.limiter, "enabled", False)
    monkeypatch.setattr(storage, "JOBS_ROOT", tmp_path / "jobs")
    monkeypatch.setattr(job_service, "_client", MagicMock())
    monkeypatch.setattr(celery, "send_task", MagicMock())
    return TestClient(app)


@pytest.mark.parametrize("key", ["", "my-custom-key"])
def test_unlimited_upload_exceeds_hosted_limits(client, monkeypatch, key):
    from routers import jobs

    monkeypatch.setattr(jobs, "LIMIT_NO_KEY", 0)
    monkeypatch.setattr(jobs, "LIMIT_WITH_KEY", 0)
    assert client.get("/api/config").json()["limit_no_key_mb"] == 0
    data = b"x" * (2 * 1024 * 1024)
    response = client.post("/api/jobs", files={"file": ("large.txt", data)}, data={"strategy": "regex", "key": key})
    assert response.status_code == 202
    saved = jobs.storage.input_path(response.json()["job_id"], "txt")
    assert saved.read_bytes() == data


@pytest.mark.parametrize("key", ["", "my-custom-key"])
def test_configured_limit_rejects_large_upload(client, monkeypatch, key):
    from routers import jobs

    monkeypatch.setattr(jobs, "LIMIT_NO_KEY", 1024 * 1024)
    monkeypatch.setattr(jobs, "LIMIT_WITH_KEY", 1024 * 1024)
    response = client.post("/api/jobs", files={"file": ("large.txt", b"x" * (1024 * 1024 + 1))}, data={"key": key})
    assert response.status_code == 413
    assert "1 MB" in response.json()["detail"]


def test_unlimited_upload_reports_insufficient_disk(client, monkeypatch):
    from routers import jobs

    monkeypatch.setattr(jobs, "LIMIT_NO_KEY", 0)
    monkeypatch.setattr(jobs.shutil, "disk_usage", lambda path: SimpleNamespace(free=1))
    response = client.post("/api/jobs", files={"file": ("hello.txt", b"hello")})
    assert response.status_code == 507
    assert "Free space" in response.json()["detail"]


def test_upload_reports_disk_full_during_write(client, monkeypatch):
    from routers import jobs

    monkeypatch.setattr(jobs.aiofiles, "open", MagicMock(side_effect=OSError(errno.ENOSPC, "No space left")))
    response = client.post("/api/jobs", files={"file": ("hello.txt", b"hello")})
    assert response.status_code == 507
    assert "Free disk space" in response.json()["detail"]
    assert list(jobs.storage.JOBS_ROOT.iterdir()) == []


def test_concurrent_startup_keeps_one_persistent_secret(tmp_path):
    from local_entrypoint import persistent_key

    key_path = tmp_path / "state" / ".secret-key"
    with ThreadPoolExecutor(max_workers=8) as pool:
        keys = list(pool.map(persistent_key, [key_path] * 32))
    assert len(set(keys)) == 1
    assert len(keys[0]) == 64
    assert persistent_key(key_path) == keys[0]
    assert key_path.stat().st_mode & 0o777 == 0o600


def test_long_local_jobs_do_not_expire(monkeypatch):
    from services import job_service

    redis = MagicMock()
    monkeypatch.setattr(job_service, "_client", lambda: redis)
    monkeypatch.setattr(job_service, "STATUS_TTL", 0)
    monkeypatch.setattr(job_service, "META_TTL", 0)
    monkeypatch.setattr(job_service, "KEY_TTL", 0)
    job_service.set_status("local-job", "queued")
    job_service.store_meta("local-job", {"filename": "large.csv"})
    job_service.store_key("local-job", "key")
    assert redis.set.call_count == 3
    redis.setex.assert_not_called()
