"""
Tests for PT-BR NER defaults and person-name detection.

Focus: cheques, extratos bancários, certidões — document types where the
*primary* anonymization target is the person's name (not CPF/CNPJ, which
are handled by regex). These tests verify:

1. Auto-selection: when lang=pt and --transformer-model is unset, the system
   picks a PT-BR fine-tuned model from the registry.
2. Registry coverage: every PT-BR model entry resolves to a mapping that
   produces PERSON labels.
3. The registry default for PT is a LeNER-Br model — best PT-BR F1 for
   person / organization / location on formal/legal text.
"""
from __future__ import annotations

import pytest

from src.anon.model_registry import (
    DEFAULT_MODEL,
    MODEL_REGISTRY,
    default_transformer_for_lang,
    get_entity_mapping,
)


# ---------------------------------------------------------------------------
# Auto-selection helper
# ---------------------------------------------------------------------------

def test_default_transformer_for_english_is_multilingual():
    assert default_transformer_for_lang("en") == DEFAULT_MODEL


def test_default_transformer_for_portuguese_is_lenerbr():
    picked = default_transformer_for_lang("pt")
    assert picked in MODEL_REGISTRY, f"{picked!r} not registered"
    entry = MODEL_REGISTRY[picked]
    assert "pt" in entry.languages
    # Must be able to detect person names
    assert "PERSON" in entry.entity_mapping.values()


def test_default_transformer_falls_back_for_unknown_lang():
    # Languages without a dedicated PT-style fine-tune reuse the multilingual model
    assert default_transformer_for_lang("de") == DEFAULT_MODEL
    assert default_transformer_for_lang("fr") == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# Registry coverage for PT-BR models
# ---------------------------------------------------------------------------

PT_BR_MODELS = [
    "pierreguillou/ner-bert-large-cased-pt-lenerbr",
    "pierreguillou/ner-bert-base-cased-pt-lenerbr",
    "monilouise/ner_pt_br",
    "marquesafonso/bertimbau-large-ner-selective",
    "lfcc/bert-portuguese-ner",
    "dominguesm/ner-bertimbau-large-pt-legal-br",
]


@pytest.mark.parametrize("model_id", PT_BR_MODELS)
def test_pt_br_model_maps_person_label(model_id):
    """Every registered PT-BR model must expose a PERSON mapping so
    person names are captured during anonymization of cheques / extratos /
    certidões."""
    mapping = get_entity_mapping(model_id)
    assert "PERSON" in mapping.values(), (
        f"{model_id} does not map any label to PERSON"
    )


@pytest.mark.parametrize("model_id", PT_BR_MODELS)
def test_pt_br_model_registered_as_portuguese(model_id):
    assert model_id in MODEL_REGISTRY
    assert "pt" in MODEL_REGISTRY[model_id].languages


def test_lenerbr_models_expose_legal_refs():
    """LeNER-Br models keep LEGISLACAO / JURISPRUDENCIA as separate entity
    types so they can be preserved or redacted independently."""
    for mid in (
        "pierreguillou/ner-bert-large-cased-pt-lenerbr",
        "pierreguillou/ner-bert-base-cased-pt-lenerbr",
        "dominguesm/ner-bertimbau-large-pt-legal-br",
    ):
        mapping = get_entity_mapping(mid)
        assert mapping.get("LEGISLACAO") == "LAW_REFERENCE"
        assert mapping.get("JURISPRUDENCIA") == "CASE_REFERENCE"


def test_harem_model_accepts_multiple_label_casings():
    """HAREM corpora ship with both uppercase (PESSOA) and title-case
    (Pessoa) label variants depending on the checkpoint. Both must map."""
    mapping = get_entity_mapping("monilouise/ner_pt_br")
    assert mapping.get("PESSOA") == "PERSON"
    assert mapping.get("Pessoa") == "PERSON"
    assert mapping.get("VALOR") == "MONEY"


# ---------------------------------------------------------------------------
# CLI auto-resolution (integration — no subprocess needed, just _parse_arguments)
# ---------------------------------------------------------------------------

def test_cli_auto_selects_pt_model_when_lang_is_pt(monkeypatch, tmp_path):
    """`anon.py --lang pt <file>` (without --transformer-model) should
    upgrade to the PT-BR LeNER-Br model automatically."""
    import anon as anon_mod

    p = tmp_path / "x.txt"
    p.write_text("João Silva deposita em 01/02/2024.\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["anon.py", "--lang", "pt", str(p)])
    args = anon_mod._parse_arguments()

    assert args.lang == "pt"
    assert args.transformer_model == default_transformer_for_lang("pt")


def test_cli_preserves_explicit_model_override(monkeypatch, tmp_path):
    """Even with --lang pt, an explicit --transformer-model must win."""
    import anon as anon_mod

    p = tmp_path / "x.txt"
    p.write_text("João Silva.\n", encoding="utf-8")
    explicit = "Davlan/xlm-roberta-base-ner-hrl"
    monkeypatch.setattr(
        "sys.argv",
        ["anon.py", "--lang", "pt", "--transformer-model", explicit, str(p)],
    )
    args = anon_mod._parse_arguments()
    assert args.transformer_model == explicit


def test_cli_english_keeps_multilingual_default(monkeypatch, tmp_path):
    """Default English behavior unchanged — still multilingual model."""
    import anon as anon_mod

    p = tmp_path / "x.txt"
    p.write_text("John Doe.\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["anon.py", str(p)])
    args = anon_mod._parse_arguments()
    assert args.transformer_model == DEFAULT_MODEL
