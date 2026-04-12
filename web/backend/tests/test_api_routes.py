"""Integration tests for FastAPI routes using TestClient (no real Redis/Celery)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytest.importorskip("fastapi", reason="fastapi not installed — run: pip install fastapi httpx")
pytest.importorskip("httpx", reason="httpx not installed — run: pip install httpx")

from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ANON_JOBS_DIR", str(tmp_path / "jobs"))

    # Patch Redis and Celery so tests don't need a running broker
    with (
        patch("services.job_service._client") as mock_redis_fn,
        patch("workers.celery_app.app") as mock_celery,
    ):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.hset.return_value = True
        mock_redis_fn.return_value = mock_redis

        from main import app
        yield TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_entities_default(client):
    r = client.get("/api/entities")
    assert r.status_code == 200
    data = r.json()
    assert "groups" in data
    assert len(data["groups"]) > 0


def test_entities_regex_strategy(client):
    """Regex strategy excludes NER entities and includes custom regex recognizers."""
    r = client.get("/api/entities?strategy=regex")
    assert r.status_code == 200
    ids = [e["id"] for g in r.json()["groups"] for e in g["entities"]]
    # NER-only entities must be absent in regex mode
    assert "PERSON" not in ids
    # At least one custom recognizer must be present (IP_ADDRESS, URL, etc.)
    assert any(e in ids for e in ("IP_ADDRESS", "URL", "EMAIL_ADDRESS", "HOSTNAME"))


def test_profile_validate_valid(client):
    r = client.post("/api/profiles/validate", json={"content": "strategy: regex\nlang: pt\n"})
    assert r.status_code == 200
    assert r.json()["valid"] is True


def test_profile_validate_invalid(client):
    r = client.post("/api/profiles/validate", json={"content": "strategy: fake_strategy\n"})
    assert r.status_code == 200
    assert r.json()["valid"] is False


def test_create_job_no_key_size_limit(client, tmp_path):
    """File > 1 MB without key must return 413."""
    big_file = b"x" * (1 * 1024 * 1024 + 1)
    r = client.post(
        "/api/jobs",
        files={"file": ("big.txt", big_file, "text/plain")},
        data={"strategy": "regex", "lang": "en"},
    )
    assert r.status_code == 413


def test_create_job_small_file(client, tmp_path, monkeypatch):
    """Small file (< 1 MB, no key) must return 202 or 507 if disk check fails in CI."""
    with (
        patch("services.job_service.store_meta"),
        patch("services.job_service.set_status"),
        patch("services.job_service.store_key"),
        patch("workers.celery_app.app.send_task"),
        patch("services.storage.JOBS_ROOT", tmp_path / "jobs"),
    ):
        r = client.post(
            "/api/jobs",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            data={"strategy": "regex", "lang": "en"},
        )
    assert r.status_code in (202, 507)


def test_job_status_not_found(client):
    r = client.get("/api/jobs/nonexistent-id/status")
    assert r.status_code == 404


def test_download_not_found(client):
    r = client.get("/api/jobs/nonexistent-id/download")
    assert r.status_code == 404
