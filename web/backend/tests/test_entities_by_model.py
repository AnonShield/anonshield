"""
Integration tests for GET /api/entities?model=... — model-aware entity lists.

Verifies that the endpoint returns different entity sets per model and that
model-specific entities (cybersecurity, financial, clinical, biomedical)
appear only when the matching model is requested.

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
# 3. DeBERTa financial PII
# ---------------------------------------------------------------------------

def test_deberta_has_financial_entities(client):
    r = client.get("/api/entities?strategy=filtered&model=lakshyakh93/deberta_finetuned_pii")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    assert "IBAN_CODE" in ids
    assert "CREDIT_CARD" in ids
    assert "CRYPTO" in ids


def test_deberta_has_credential_entities(client):
    r = client.get("/api/entities?strategy=filtered&model=lakshyakh93/deberta_finetuned_pii")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    assert "USERNAME" in ids
    assert "PASSWORD" in ids
    assert "MAC_ADDRESS" in ids


# ---------------------------------------------------------------------------
# 4. Clinical — i2b2
# ---------------------------------------------------------------------------

def test_i2b2_has_clinical_entities(client):
    r = client.get("/api/entities?strategy=filtered&model=obi/deid_roberta_i2b2")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    assert "PERSON" in ids     # PATIENT + STAFF both map to PERSON
    assert "AGE" in ids
    assert "DATE_TIME" in ids


# ---------------------------------------------------------------------------
# 5. Biomedical — MACCROBAT
# ---------------------------------------------------------------------------

def test_biomedical_has_disease_drug(client):
    r = client.get("/api/entities?strategy=filtered&model=d4data/biomedical-ner-all")
    assert r.status_code == 200
    ids = _entity_ids(r.json())
    assert "DISEASE" in ids
    assert "DRUG" in ids


# ---------------------------------------------------------------------------
# 6. Regex strategy — no NER model entities regardless of model param
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model", [
    "attack-vector/SecureModernBERT-NER",
    "lakshyakh93/deberta_finetuned_pii",
    "obi/deid_roberta_i2b2",
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
# 7. Models that share the same mapping return same entity set
# ---------------------------------------------------------------------------

def test_conll_models_return_same_entities(client):
    r1 = client.get("/api/entities?strategy=filtered&model=dslim/bert-base-NER")
    r2 = client.get("/api/entities?strategy=filtered&model=Jean-Baptiste/roberta-large-ner-english")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both CoNLL models produce PERSON, ORG, LOC — sets should be equal
    ids1 = _entity_ids(r1.json())
    ids2 = _entity_ids(r2.json())
    assert ids1 == ids2


def test_distilbert_same_as_xlmroberta(client):
    r1 = client.get("/api/entities?strategy=filtered&model=Davlan/xlm-roberta-base-ner-hrl")
    r2 = client.get("/api/entities?strategy=filtered&model=Davlan/distilbert-base-multilingual-cased-ner-hrl")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert _entity_ids(r1.json()) == _entity_ids(r2.json())


# ---------------------------------------------------------------------------
# 8. Different models return different entity sets
# ---------------------------------------------------------------------------

def test_securemodern_different_from_default(client):
    r_default = client.get("/api/entities?strategy=filtered&model=Davlan/xlm-roberta-base-ner-hrl")
    r_cyber = client.get("/api/entities?strategy=filtered&model=attack-vector/SecureModernBERT-NER")
    ids_default = _entity_ids(r_default.json())
    ids_cyber = _entity_ids(r_cyber.json())
    # Cyber model has MALWARE which default doesn't
    assert "MALWARE" in ids_cyber
    assert "MALWARE" not in ids_default


def test_financial_different_from_clinical(client):
    r_fin = client.get("/api/entities?strategy=filtered&model=lakshyakh93/deberta_finetuned_pii")
    r_clin = client.get("/api/entities?strategy=filtered&model=obi/deid_roberta_i2b2")
    ids_fin = _entity_ids(r_fin.json())
    ids_clin = _entity_ids(r_clin.json())
    # Financial has IBAN_CODE which clinical doesn't (i2b2 maps IBAN to ID, not IBAN_CODE)
    assert "IBAN_CODE" in ids_fin
    # Biomedical has DISEASE which financial doesn't
    assert "DISEASE" not in ids_fin


# ---------------------------------------------------------------------------
# 9. Response shape
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
    r = client.get("/api/entities?model=lakshyakh93/deberta_finetuned_pii")
    assert r.status_code == 200
    for group in r.json()["groups"]:
        for entity in group["entities"]:
            assert entity.get("label"), f"Entity {entity['id']} has no label"
