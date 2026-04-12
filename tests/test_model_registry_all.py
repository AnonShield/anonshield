"""
E2E + unit tests for the full model registry (all 8 registered models).

Covers:
  - Each registered model returns its correct entity mapping values
  - get_supported_entities() is model-aware (different results per model)
  - Unknown model falls back to default with a warning
  - register_model() runtime registration works
  - CLI --list-entities respects the model parameter
"""
import logging
import subprocess
import sys
from pathlib import Path

import pytest

from src.anon.model_registry import MODEL_REGISTRY, get_entity_mapping, register_model

PROJECT_ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entity_values(model_id: str) -> set[str]:
    """Return the set of Presidio entity types a model produces (mapping values)."""
    return set(get_entity_mapping(model_id).values())


# ---------------------------------------------------------------------------
# 1. Registry completeness — all frontend models must be registered
# ---------------------------------------------------------------------------

FRONTEND_MODELS = [
    "Davlan/xlm-roberta-base-ner-hrl",
    "attack-vector/SecureModernBERT-NER",
    "lakshyakh93/deberta_finetuned_pii",
    "dslim/bert-base-NER",
    "Jean-Baptiste/roberta-large-ner-english",
    "obi/deid_roberta_i2b2",
    "d4data/biomedical-ner-all",
    "Davlan/distilbert-base-multilingual-cased-ner-hrl",
]

@pytest.mark.parametrize("model_id", FRONTEND_MODELS)
def test_all_frontend_models_are_registered(model_id):
    assert model_id in MODEL_REGISTRY, (
        f"{model_id} is shown in the UI but missing from MODEL_REGISTRY"
    )


# ---------------------------------------------------------------------------
# 2. Correct mapping values per model
# ---------------------------------------------------------------------------

class TestDefaultXLMRoberta:
    def test_person(self):
        m = get_entity_mapping("Davlan/xlm-roberta-base-ner-hrl")
        assert m["PER"] == "PERSON"
        assert m["PERSON"] == "PERSON"

    def test_org_loc(self):
        m = get_entity_mapping("Davlan/xlm-roberta-base-ner-hrl")
        assert m["ORG"] == "ORGANIZATION"
        assert m["LOC"] == "LOCATION"
        assert m["GPE"] == "LOCATION"

    def test_contact(self):
        m = get_entity_mapping("Davlan/xlm-roberta-base-ner-hrl")
        assert m["EMAIL"] == "EMAIL_ADDRESS"
        assert m["PHONE"] == "PHONE_NUMBER"


class TestDistilbertMultilingual:
    """DistilBERT multilingual uses same mapping as xlm-roberta."""

    def test_same_labels_as_default(self):
        distil = get_entity_mapping("Davlan/distilbert-base-multilingual-cased-ner-hrl")
        xlm = get_entity_mapping("Davlan/xlm-roberta-base-ner-hrl")
        assert distil == xlm

    def test_person_org_loc(self):
        m = get_entity_mapping("Davlan/distilbert-base-multilingual-cased-ner-hrl")
        assert m["PER"] == "PERSON"
        assert m["ORG"] == "ORGANIZATION"
        assert m["LOC"] == "LOCATION"


class TestConllEnModels:
    """bert-base-NER and roberta-large both trained on CoNLL-2003 English."""

    @pytest.mark.parametrize("model_id", [
        "dslim/bert-base-NER",
        "Jean-Baptiste/roberta-large-ner-english",
    ])
    def test_conll_labels(self, model_id):
        m = get_entity_mapping(model_id)
        assert m["PER"] == "PERSON"
        assert m["ORG"] == "ORGANIZATION"
        assert m["LOC"] == "LOCATION"

    @pytest.mark.parametrize("model_id", [
        "dslim/bert-base-NER",
        "Jean-Baptiste/roberta-large-ner-english",
    ])
    def test_no_misc_mapping(self, model_id):
        """MISC is not PII — must NOT map to a Presidio entity."""
        m = get_entity_mapping(model_id)
        assert "MISC" not in m

    @pytest.mark.parametrize("model_id", [
        "dslim/bert-base-NER",
        "Jean-Baptiste/roberta-large-ner-english",
    ])
    def test_same_mapping(self, model_id):
        """Both CoNLL-2003 models share the same mapping."""
        bert = get_entity_mapping("dslim/bert-base-NER")
        roberta = get_entity_mapping("Jean-Baptiste/roberta-large-ner-english")
        assert bert == roberta


class TestI2B2Clinical:
    MODEL = "obi/deid_roberta_i2b2"

    def test_patient_and_staff_map_to_person(self):
        m = get_entity_mapping(self.MODEL)
        assert m["PATIENT"] == "PERSON"
        assert m["STAFF"] == "PERSON"

    def test_location_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["HOSP"] == "LOCATION"
        assert m["LOC"] == "LOCATION"

    def test_contact_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["PHONE"] == "PHONE_NUMBER"
        assert m["EMAIL"] == "EMAIL_ADDRESS"

    def test_temporal_and_id(self):
        m = get_entity_mapping(self.MODEL)
        assert m["DATE"] == "DATE_TIME"
        assert m["AGE"] == "AGE"
        assert m["ID"] == "ID"

    def test_org(self):
        m = get_entity_mapping(self.MODEL)
        assert m["PATORG"] == "ORGANIZATION"

    def test_no_old_wrong_labels(self):
        """The old (wrong) i2b2 2006 labels must NOT be present."""
        m = get_entity_mapping(self.MODEL)
        assert "NAME" not in m, "NAME was an i2b2 2006 label — model uses PATIENT/STAFF"
        assert "CONTACT" not in m, "CONTACT was old label — model uses PHONE/EMAIL"
        assert "LOCATION" not in m, "LOCATION was old label — model uses LOC/HOSP"


class TestBiomedicalMaccrobat:
    MODEL = "d4data/biomedical-ner-all"

    def test_maccrobat_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["Disease_disorder"] == "DISEASE"
        assert m["Medication"] == "DRUG"
        assert m["Age"] == "AGE"
        assert m["Date"] == "DATE_TIME"

    def test_no_bc5cdr_labels(self):
        """BC5CDR/NCBI labels (DISEASE, DRUG, GENE) must NOT be present — wrong dataset."""
        m = get_entity_mapping(self.MODEL)
        assert "DISEASE" not in m, "DISEASE is a BC5CDR label; model uses Disease_disorder"
        assert "DRUG" not in m, "DRUG is a BC5CDR label; model uses Medication"
        assert "GENE_OR_GENE_PRODUCT" not in m, "GENE_OR_GENE_PRODUCT is NCBI label — not MACCROBAT"
        assert "GENE" not in m
        assert "CANCER" not in m

    def test_personal_background(self):
        m = get_entity_mapping(self.MODEL)
        assert m["Personal_background"] == "PERSON"
        assert m["Occupation"] == "NRP"
        assert m["Family_history"] == "PERSON"


class TestSecureModernBERT:
    MODEL = "attack-vector/SecureModernBERT-NER"

    def test_cybersecurity_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["CVE"] == "CVE_ID"
        assert m["MALWARE"] == "MALWARE"
        assert m["THREAT-ACTOR"] == "THREAT_ACTOR"
        assert m["TOOL"] == "TOOL"
        assert m["CAMPAIGN"] == "CAMPAIGN"

    def test_network_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["IPV4"] == "IP_ADDRESS"
        assert m["IPV6"] == "IP_ADDRESS"
        assert m["DOMAIN"] == "HOSTNAME"

    def test_hash_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["MD5"] == "HASH"
        assert m["SHA1"] == "HASH"
        assert m["SHA256"] == "HASH"

    def test_no_person_label(self):
        """SecureModernBERT does not detect PERSON names."""
        values = _entity_values(self.MODEL)
        assert "PERSON" not in values


class TestDebertaFinancialPII:
    MODEL = "lakshyakh93/deberta_finetuned_pii"

    def test_identity_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["FIRSTNAME"] == "PERSON"
        assert m["LASTNAME"] == "PERSON"
        assert m["FULLNAME"] == "PERSON"

    def test_financial_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["CREDITCARDNUMBER"] == "CREDIT_CARD"
        assert m["CREDITCARDCVV"] == "CREDIT_CARD"
        assert m["IBAN"] == "IBAN_CODE"
        assert m["ACCOUNTNUMBER"] == "ID"
        assert m["BIC"] == "ID"

    def test_crypto_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["BITCOINADDRESS"] == "CRYPTO"
        assert m["ETHEREUMADDRESS"] == "CRYPTO"
        assert m["LITECOINADDRESS"] == "CRYPTO"

    def test_network_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["IPV4"] == "IP_ADDRESS"
        assert m["IPV6"] == "IP_ADDRESS"
        assert m["MAC"] == "MAC_ADDRESS"

    def test_credential_labels(self):
        m = get_entity_mapping(self.MODEL)
        assert m["PASSWORD"] == "PASSWORD"
        assert m["PIN"] == "PASSWORD"
        assert m["USERNAME"] == "USERNAME"

    def test_non_pii_not_mapped(self):
        """Amounts, currencies, ordinal directions are not PII — must be absent."""
        m = get_entity_mapping(self.MODEL)
        assert "AMOUNT" not in m
        assert "CURRENCY" not in m
        assert "CURRENCYNAME" not in m
        assert "ORDINALDIRECTION" not in m


# ---------------------------------------------------------------------------
# 3. get_supported_entities is model-aware
# ---------------------------------------------------------------------------

def test_get_supported_entities_default_model_has_person():
    from src.anon.api import get_supported_entities
    entities = get_supported_entities(strategy="regex", lang="en",
                                      model="Davlan/xlm-roberta-base-ner-hrl")
    # regex strategy → no NER model entities, only custom regex
    assert "PERSON" not in entities
    assert "IP_ADDRESS" in entities


def test_get_supported_entities_securemodern_includes_cybersec():
    from src.anon.api import get_supported_entities
    # Non-regex strategy → model NER entities are added
    entities = get_supported_entities(strategy="filtered", lang="en",
                                      model="attack-vector/SecureModernBERT-NER")
    assert "MALWARE" in entities
    assert "THREAT_ACTOR" in entities
    assert "CVE_ID" in entities


def test_get_supported_entities_deberta_includes_financial():
    from src.anon.api import get_supported_entities
    entities = get_supported_entities(strategy="filtered", lang="en",
                                      model="lakshyakh93/deberta_finetuned_pii")
    assert "IBAN_CODE" in entities
    assert "CREDIT_CARD" in entities
    assert "CRYPTO" in entities


def test_get_supported_entities_biomedical_includes_disease():
    from src.anon.api import get_supported_entities
    entities = get_supported_entities(strategy="filtered", lang="en",
                                      model="d4data/biomedical-ner-all")
    assert "DISEASE" in entities
    assert "DRUG" in entities


def test_get_supported_entities_i2b2_includes_clinical():
    from src.anon.api import get_supported_entities
    entities = get_supported_entities(strategy="filtered", lang="en",
                                      model="obi/deid_roberta_i2b2")
    # i2b2 model produces PERSON, LOCATION, DATE_TIME, PHONE_NUMBER, ID
    assert "PERSON" in entities
    assert "AGE" in entities
    assert "DATE_TIME" in entities


def test_get_supported_entities_cache_key_is_model_specific():
    """Different models must not share cached results."""
    from src.anon.api import get_supported_entities, _ENTITY_CACHE
    # Force cache population for two models
    e1 = get_supported_entities("filtered", "en", "attack-vector/SecureModernBERT-NER")
    e2 = get_supported_entities("filtered", "en", "Davlan/xlm-roberta-base-ner-hrl")
    assert set(e1) != set(e2), (
        "SecureModernBERT and xlm-roberta should return different entity sets"
    )
    assert "filtered:en:attack-vector/SecureModernBERT-NER" in _ENTITY_CACHE
    assert "filtered:en:Davlan/xlm-roberta-base-ner-hrl" in _ENTITY_CACHE


# ---------------------------------------------------------------------------
# 4. Unknown model fallback
# ---------------------------------------------------------------------------

def test_unknown_model_falls_back_to_default(caplog):
    with caplog.at_level(logging.WARNING, logger="src.anon.model_registry"):
        m = get_entity_mapping("totally-unknown/model-xyz")
    assert m["PER"] == "PERSON"
    assert "not in the registry" in caplog.text


def test_unknown_model_still_returns_regex_entities():
    from src.anon.api import get_supported_entities
    entities = get_supported_entities("regex", "en", "totally-unknown/model-xyz")
    # Even unknown model should return regex entities
    assert "IP_ADDRESS" in entities
    assert "EMAIL_ADDRESS" in entities


# ---------------------------------------------------------------------------
# 5. Runtime register_model
# ---------------------------------------------------------------------------

def test_register_model_runtime():
    register_model(
        "test-bank/banking-ner",
        {"IBAN": "IBAN_CODE", "BIC": "ID", "ACCOUNT": "ID"},
        description="Test banking model",
    )
    m = get_entity_mapping("test-bank/banking-ner")
    assert m["IBAN"] == "IBAN_CODE"
    assert m["BIC"] == "ID"


# ---------------------------------------------------------------------------
# 6. CLI --list-entities respects model (subprocess E2E)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model,expected_entity", [
    ("attack-vector/SecureModernBERT-NER", "MALWARE"),
    ("lakshyakh93/deberta_finetuned_pii", "IBAN_CODE"),
    ("obi/deid_roberta_i2b2", "AGE"),
    ("d4data/biomedical-ner-all", "DISEASE"),
])
def test_list_entities_model_specific(model, expected_entity):
    """--list-entities output must include model-specific entity types."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "anon.py"),
         "--list-entities",
         "--anonymization-strategy", "filtered",
         "--transformer-model", model],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert expected_entity in result.stdout, (
        f"Expected '{expected_entity}' in --list-entities for {model}.\n"
        f"Got:\n{result.stdout}"
    )


def test_list_entities_default_model_has_person():
    """Default model includes PERSON from entity mapping."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "anon.py"),
         "--list-entities",
         "--anonymization-strategy", "filtered"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "PERSON" in result.stdout


def test_list_entities_regex_strategy_no_ner():
    """Regex strategy must not include NER-only entities like PERSON."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "anon.py"),
         "--list-entities",
         "--anonymization-strategy", "regex"],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "IP_ADDRESS" in result.stdout
    assert "PERSON" not in result.stdout
