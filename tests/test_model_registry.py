"""
Tests for the model registry (Step 6).

Covers:
  - Known models return correct entity mappings
  - Unknown models fall back to default mapping (with a warning)
  - register_model() adds a new entry that is immediately usable
  - custom_models in YAML config are registered before engine init
"""
import logging

from src.anon.model_registry import (
    MODEL_REGISTRY,
    get_entity_mapping,
    register_model,
)
from tests.conftest import _run_anon


# ---------------------------------------------------------------------------
# Unit-level registry tests (no subprocess)
# ---------------------------------------------------------------------------

def test_default_model_returns_correct_mapping():
    mapping = get_entity_mapping("Davlan/xlm-roberta-base-ner-hrl")
    assert mapping["PER"] == "PERSON"
    assert mapping["ORG"] == "ORGANIZATION"
    assert mapping["LOC"] == "LOCATION"


def test_securebertmodel_returns_correct_mapping():
    mapping = get_entity_mapping("attack-vector/SecureModernBERT-NER")
    assert mapping["CVE"] == "CVE_ID"
    assert mapping["IPV4"] == "IP_ADDRESS"
    assert mapping["MALWARE"] == "MALWARE"


def test_unknown_model_falls_back_to_default(caplog):
    with caplog.at_level(logging.WARNING, logger="src.anon.model_registry"):
        mapping = get_entity_mapping("unknown-org/some-model")
    assert "PER" in mapping
    assert "not in the registry" in caplog.text


def test_register_model_makes_it_retrievable():
    new_id = "test-org/custom-ner-test"
    custom_mapping = {"PER": "PERSON", "PRODUCT_ID": "PRODUCT"}
    register_model(new_id, custom_mapping, description="Test model")
    assert new_id in MODEL_REGISTRY
    retrieved = get_entity_mapping(new_id)
    assert retrieved["PRODUCT_ID"] == "PRODUCT"


def test_register_model_overrides_existing():
    # Register with initial mapping, then override
    mid = "test-org/override-model"
    register_model(mid, {"A": "ENTITY_A"})
    register_model(mid, {"A": "ENTITY_B"})
    assert get_entity_mapping(mid)["A"] == "ENTITY_B"


# ---------------------------------------------------------------------------
# E2E: custom_models via YAML config
# ---------------------------------------------------------------------------

def test_custom_models_in_config_file(tmp_path, tmp_output_dir):
    """Custom model entry in YAML config is registered before engine runs."""
    config = tmp_path / "cfg.yaml"
    config.write_text(
        "strategy: regex\n"
        "slug_length: 0\n"
        "custom_models:\n"
        "  - id: myorg/domain-ner\n"
        "    entity_mapping:\n"
        "      PER: PERSON\n"
        "      ORG: ORGANIZATION\n"
        "    description: Domain NER\n",
        encoding="utf-8",
    )
    p = tmp_path / "x.txt"
    p.write_text("admin@example.com\n", encoding="utf-8")
    result = _run_anon([
        str(p),
        "--config", str(config),
        "--output-dir", tmp_output_dir,
        "--overwrite",
    ])
    # The tool should start and succeed (model is registered but not used for
    # loading in regex mode — the key test is no crash)
    assert result.returncode == 0, result.stderr
