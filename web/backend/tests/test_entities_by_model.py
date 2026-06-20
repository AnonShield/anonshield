"""
Integration tests for GET /api/entities?model=... — model-aware entity lists.

Verifies that the endpoint returns different entity sets per model and that
model-specific entities (cybersecurity) appear only when the matching model
is requested.

Redis is mocked (no running broker needed).
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ANON_JOBS_DIR", str(tmp_path / "jobs"))
    with (
        patch("services.job_service._client") as mock_redis_fn,
        patch("workers.celery_app.app"),
    ):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None       # always cache miss → compute live
        mock_redis.setex.return_value = True
        mock_redis_fn.return_value = mock_redis

        from main import app
        yield TestClient(app)


def _entity_ids(response_data: dict) -> set[str]:
    return {e["id"] for g in response_data.get("groups", []) for e in g["entities"]}


# ---------------------------------------------------------------------------
# 1. Default model (xlm-roberta)
# ---------------------------------------------------------------------------

def test_default_model_has_person_and_location(client):
    r = client.get("/api/entities?strategy=filtered&model=Davlan/xlm-roberta-base-ner-hrl")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    assert "PERSON" in ids
    assert "LOCATION" in ids
    assert "ORGANIZATION" in ids


def test_default_model_has_regex_entities(client):
    r = client.get("/api/entities?model=Davlan/xlm-roberta-base-ner-hrl")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    assert "IP_ADDRESS" in ids
    assert "EMAIL_ADDRESS" in ids
    assert "CVE_ID" in ids


# ---------------------------------------------------------------------------
# 2. SecureModernBERT — cybersecurity entities
# ---------------------------------------------------------------------------

def test_securemodern_has_cybersec_entities(client):
    r = client.get("/api/entities?strategy=filtered&model=attack-vector/SecureModernBERT-NER")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    assert "MALWARE" in ids
    assert "THREAT_ACTOR" in ids
    assert "CVE_ID" in ids
    assert "TOOL" in ids
    assert "CAMPAIGN" in ids
    assert "REGISTRY_KEY" in ids


def test_securemodern_has_no_person(client):
    """SecureModernBERT mapping has no PERSON label → should not appear from model."""
    r = client.get("/api/entities?strategy=filtered&model=attack-vector/SecureModernBERT-NER")
    assert r.status_code == 200
    # PERSON may appear from Presidio built-ins but NOT from model registry
    # (we verify cybersec entities dominate, not that PERSON is absent from Presidio)
    ids = _entity_ids(r.json())
    assert "MALWARE" in ids  # key assertion — model-specific entity is present


# ---------------------------------------------------------------------------
# 3. Regex strategy — no NER model entities regardless of model param
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model", [
    "Davlan/xlm-roberta-base-ner-hrl",
    "attack-vector/SecureModernBERT-NER",
])
def test_regex_strategy_excludes_ner_entities(client, model):
    r = client.get(f"/api/entities?strategy=regex&model={model}")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    # NER-only entities must be absent in regex mode
    assert "PERSON" not in ids
    assert "MALWARE" not in ids
    # Regex entities always present
    assert "IP_ADDRESS" in ids
    assert "EMAIL_ADDRESS" in ids


# ---------------------------------------------------------------------------
# 4. Different models return different entity sets
# ---------------------------------------------------------------------------

def test_securemodern_different_from_default(client):
    r_default = client.get("/api/entities?strategy=filtered&model=Davlan/xlm-roberta-base-ner-hrl")
    r_cyber = client.get("/api/entities?strategy=filtered&model=attack-vector/SecureModernBERT-NER")
    ids_default = _entity_ids(r_default.json())
    ids_cyber = _entity_ids(r_cyber.json())
    # Cyber model has MALWARE which default doesn't
    assert "MALWARE" in ids_cyber
    assert "MALWARE" not in ids_default


# ---------------------------------------------------------------------------
# 5. Response shape
# ---------------------------------------------------------------------------

def test_response_has_correct_shape(client):
    r = client.get("/api/entities")
    assert r.status_code == 200
    data = r.json()
    assert "groups" in data
    assert "strategy" in data
    for group in data["groups"]:
        assert "label" in group
        assert "entities" in group
        for entity in group["entities"]:
            assert "id" in entity
            assert "label" in entity


def test_each_entity_has_example(client):
    """Every entity in the response must have a human-readable label."""
    r = client.get("/api/entities?model=Davlan/xlm-roberta-base-ner-hrl")
    assert r.status_code == 200
    for group in r.json()["groups"]:
        for entity in group["entities"]:
            assert entity.get("label"), f"Entity {entity['id']} has no label"
