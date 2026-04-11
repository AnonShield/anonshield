"""
Transformer NER model registry.

Adding a new model requires only a single entry here — no scattered
conditionals in engine.py or strategies.py.

Usage:
    from src.anon.model_registry import get_entity_mapping, register_model
    mapping = get_entity_mapping("Davlan/xlm-roberta-base-ner-hrl")
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Default multilingual entity mapping (covers xlm-roberta-base-ner-hrl and
# most generic HuggingFace NER models that follow OntoNotes/CoNLL conventions)
_DEFAULT_ENTITY_MAPPING: dict[str, str] = {
    "LOC": "LOCATION",
    "ORG": "ORGANIZATION",
    "PER": "PERSON",
    "EMAIL": "EMAIL_ADDRESS",
    "PHONE": "PHONE_NUMBER",
    "PERSON": "PERSON",
    "LOCATION": "LOCATION",
    "GPE": "LOCATION",
    "ORGANIZATION": "ORGANIZATION",
}

_SECURE_MODERNBERT_ENTITY_MAPPING: dict[str, str] = {
    "ORG": "ORGANIZATION",
    "LOC": "LOCATION",
    "EMAIL": "EMAIL_ADDRESS",
    "URL": "URL",
    "IPV4": "IP_ADDRESS",
    "IPV6": "IP_ADDRESS",
    "DOMAIN": "HOSTNAME",
    "MD5": "HASH",
    "SHA1": "HASH",
    "SHA256": "HASH",
    "FILEPATH": "FILE_PATH",
    "REGISTRY-KEYS": "REGISTRY_KEY",
    "THREAT-ACTOR": "THREAT_ACTOR",
    "MALWARE": "MALWARE",
    "CVE": "CVE_ID",
    "PLATFORM": "PLATFORM",
    "PRODUCT": "PRODUCT",
    "SECTOR": "SECTOR",
    "TOOL": "TOOL",
    "CAMPAIGN": "CAMPAIGN",
    "MITRE_TACTIC": "MITRE_TACTIC",
    "SERVICE": "SERVICE",
}


@dataclass
class ModelEntry:
    """Metadata for a registered NER transformer model."""
    entity_mapping: dict[str, str]
    description: str = ""
    languages: list[str] = field(default_factory=lambda: ["en"])


# ---------------------------------------------------------------------------
# Registry — add new models here only
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, ModelEntry] = {
    "Davlan/xlm-roberta-base-ner-hrl": ModelEntry(
        entity_mapping=_DEFAULT_ENTITY_MAPPING,
        description="Multilingual NER (default) — covers en, pt, es, fr, de, ar, zh",
        languages=["en", "pt", "es", "fr", "de", "ar", "zh"],
    ),
    "attack-vector/SecureModernBERT-NER": ModelEntry(
        entity_mapping=_SECURE_MODERNBERT_ENTITY_MAPPING,
        description="Cybersecurity-focused NER — extracts CVE, malware, threat actors, hashes, IPs",
        languages=["en"],
    ),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_entity_mapping(model_id: str) -> dict[str, str]:
    """Return entity mapping for *model_id*.

    Falls back to the default mapping with a warning for unknown models,
    so pipelines continue working even with unregistered community models.
    """
    if model_id in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_id].entity_mapping
    logger.warning(
        "Model '%s' is not in the registry — using default entity mapping. "
        "Register it with model_registry.register_model() for precise mapping.",
        model_id,
    )
    return dict(_DEFAULT_ENTITY_MAPPING)


def register_model(
    model_id: str,
    entity_mapping: dict[str, str],
    description: str = "",
    languages: Optional[list[str]] = None,
) -> None:
    """Register a custom NER model at runtime.

    Typically called from *anon.py* after reading ``custom_models`` from the
    YAML config file, before engine initialization.
    """
    MODEL_REGISTRY[model_id] = ModelEntry(
        entity_mapping=entity_mapping,
        description=description,
        languages=languages or ["en"],
    )
    logger.info("Registered custom model '%s'", model_id)
