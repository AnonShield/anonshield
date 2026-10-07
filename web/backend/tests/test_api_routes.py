"""Integration tests for FastAPI routes using TestClient (no real Redis/Celery)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytest.importorskip("fastapi", reason="fastapi not installed; run: pip install fastapi httpx")
pytest.importorskip("httpx", reason="httpx not installed; run: pip install httpx")

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
        from services import storage
        monkeypatch.setattr(storage, "JOBS_ROOT", tmp_path / "jobs")
        monkeypatch.setattr(app.state.limiter, "enabled", False)
        yield TestClient(app)


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_large_xlsx_field_detection_reads_the_complete_archive(client):
    import io
    import random
    import string
    import openpyxl
    workbook = openpyxl.Workbook(write_only=True)
    sheet = workbook.create_sheet()
    sheet.append(["email", "notes"])
    rng = random.Random(12)
    for _ in range(4000):
        sheet.append(["a@example.com", "".join(rng.choices(string.ascii_letters, k=100))])
    buffer = io.BytesIO()
    workbook.save(buffer)
    assert buffer.tell() > 256 * 1024
    response = client.post("/api/analyze-fields", files={"file": ("large.xlsx", buffer.getvalue())})
    assert response.status_code == 200
    assert response.json() == {"fields": [{"name": "email"}, {"name": "notes"}]}


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
    r = client.get("/api/jobs/00000000-0000-0000-0000-000000000000/status")
    assert r.status_code == 404


def test_download_not_found(client):
    r = client.get("/api/jobs/00000000-0000-0000-0000-000000000000/download")
    assert r.status_code == 404


def test_job_directory_traversal_is_rejected(client, tmp_path):
    outside = tmp_path / "keep.txt"
    outside.write_text("keep")
    r = client.delete("/api/jobs/%2e%2e")
    assert r.status_code == 422
    assert outside.read_text() == "keep"


def test_job_keeps_explicit_empty_selection_and_settings(client):
    with patch("services.job_service.store_meta") as store:
        r = client.post("/api/jobs", files={"file": ("test.txt", b"a@example.com")}, data={
            "strategy": "regex", "entities": "[]", "slug_length": "0",
            "ner_score_threshold": "0.3", "model": "example/custom-model",
            "config": "custom_patterns:\n  - entity_type: ASSET\n    pattern: 'ASSET-[0-9]+'\n",
        })
    assert r.status_code == 202, r.text
    meta = store.call_args.args[1]
    assert meta["entities"] == []
    assert meta["slug_length"] == 0
    assert meta["ner_score_threshold"] == 0.3
    assert meta["model"] == "example/custom-model"
    assert meta["custom_patterns"][0]["entity_type"] == "ASSET"


@pytest.mark.parametrize("data", [{"entities": '{"EMAIL_ADDRESS": true}'}, {"slug_length": "-1"}, {"strategy": "typo"}, {"ner_score_threshold": "2"}])
def test_bad_job_settings_are_actionable_errors(client, data):
    r = client.post("/api/jobs", files={"file": ("test.txt", b"a@example.com")}, data=data)
    assert r.status_code == 422
    assert r.json()["detail"]


def test_download_supports_unicode_filename(client, tmp_path):
    from services import storage
    job_id = "00000000-0000-0000-0000-000000000001"
    storage.create_job_dir(job_id)
    (storage.output_dir(job_id) / "anon_input.txt").write_text("[EMAIL_ADDRESS]")
    with patch("services.job_service.get_status", return_value={"status": "done"}), patch("services.job_service.get_meta", return_value={"filename": 'relatório 🛡.txt'}):
        r = client.get(f"/api/jobs/{job_id}/download")
    assert r.status_code == 200
    assert r.text == "[EMAIL_ADDRESS]"
    assert "filename*=UTF-8''" in r.headers["content-disposition"]
    assert not storage.output_dir(job_id).exists()


def test_pretty_printed_json_array_with_a_large_first_record_has_fields(client):
    import json
    records = [{"output": "x" * (300 * 1024), "id": 1, "asset": {"id": 2, "name": "host", "tags": [{"value": "a"}]}}] * 2
    body = json.dumps(records, indent=2).replace("\n", "\r\n").encode()
    response = client.post("/api/analyze-fields", files={"file": ("tickets.json", body)})
    assert response.status_code == 200
    assert [f["name"] for f in response.json()["fields"]] == ["output", "id", "asset.id", "asset.name", "asset.tags"]


def test_unsupported_upload_is_refused_before_queueing(client):
    with patch("services.job_service.store_meta") as store:
        r = client.post("/api/jobs", files={"file": ("dados.tsv", b"id\tmail\n")})
    assert r.status_code == 415
    assert ".tsv" in r.json()["detail"] and "csv" in r.json()["detail"]
    store.assert_not_called()


@pytest.mark.parametrize("name,body,fields", [
    ("report.json", {"scan": {"target": "10.0.0.1", "id": 7}, "findings": [{"host": "x"}] * 20000, "owner": "a@example.com"},
     ["scan.target", "scan.id", "findings", "owner"]),
    ("events.jsonl", {"message": "x" * (300 * 1024), "user": {"email": "a@example.com"}}, ["message", "user.email"]),
])
def test_large_json_object_and_long_jsonl_line_have_their_fields(client, name, body, fields):
    import json
    data = json.dumps(body).encode() + (b"\n" if name.endswith("jsonl") else b"")
    assert len(data) > 256 * 1024
    response = client.post("/api/analyze-fields", files={"file": (name, data)})
    assert [f["name"] for f in response.json()["fields"]] == fields


@pytest.mark.parametrize("name", ["hosts.json", "hosts.jsonl"])
def test_a_field_only_in_record_12001_is_listed(client, name):
    import json
    records = [{"asset": {"host_name": "a"}}] * 12000 + [{"asset": {"host_name": "c", "netbios_name": "C"}}]
    data = (json.dumps(records) if name.endswith(".json") else "".join(json.dumps(r) + "\n" for r in records)).encode()
    response = client.post("/api/analyze-fields", files={"file": (name, data)})
    assert [f["name"] for f in response.json()["fields"]] == ["asset.host_name", "asset.netbios_name"]
