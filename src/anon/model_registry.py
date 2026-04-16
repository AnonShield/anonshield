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

# CoNLL-2003 English (bert-base-NER, roberta-large-ner-english)
# Labels: PER, ORG, LOC, MISC — MISC (misc. named entities) is not PII, omitted
_CONLL_EN_ENTITY_MAPPING: dict[str, str] = {
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "LOC": "LOCATION",
}

# i2b2 2014 Clinical De-identification (obi/deid_roberta_i2b2)
# Actual label set from BILOU tagging on i2b2/UTHealth dataset.
# Model card: https://huggingface.co/obi/deid_roberta_i2b2
_I2B2_ENTITY_MAPPING: dict[str, str] = {
    "PATIENT": "PERSON",        # Patient name
    "STAFF": "PERSON",          # Doctor / nurse / staff name
    "AGE": "AGE",
    "DATE": "DATE_TIME",
    "PHONE": "PHONE_NUMBER",
    "EMAIL": "EMAIL_ADDRESS",
    "ID": "ID",                 # Medical record, health plan, account numbers
    "HOSP": "LOCATION",         # Hospital / facility name
    "LOC": "LOCATION",          # Geographic location
    "PATORG": "ORGANIZATION",   # Patient's employer / organization
    "OTHERPHI": "ID",           # Other PHI not captured above
}

# Biomedical NER (d4data/biomedical-ner-all)
# Trained on MACCROBAT corpus (43 entity types).
# Model card: https://huggingface.co/d4data/biomedical-ner-all
# Only privacy-relevant MACCROBAT labels are mapped; non-identifying labels omitted.
_BIOMEDICAL_ENTITY_MAPPING: dict[str, str] = {
    # Personal / demographic
    "Age": "AGE",
    "Date": "DATE_TIME",
    "Time": "DATE_TIME",
    "Personal_background": "PERSON",  # Personal background info about the patient
    "Occupation": "NRP",              # Job title (closest standard type)
    "Family_history": "PERSON",       # Refers to specific family members
    # Clinical entities relevant for de-identification in research publications
    "Disease_disorder": "DISEASE",
    "Sign_symptom": "DISEASE",        # Symptoms — may identify patient condition
    "Medication": "DRUG",
    "Dosage": "DRUG",                 # Dosage tied to specific medication
    "Therapeutic_procedure": "DRUG",  # Treatments administered
    "Diagnostic_procedure": "DISEASE",
    "Lab_value": "ID",                # Lab results (can be patient-identifying)
}

# Financial / Banking PII (lakshyakh93/deberta_finetuned_pii)
# 60+ label types from the Faker-generated financial PII dataset.
# Model card: https://huggingface.co/lakshyakh93/deberta_finetuned_pii
_DEBERTA_PII_ENTITY_MAPPING: dict[str, str] = {
    # ── Identity ─────────────────────────────────────────────────────────────
    "FIRSTNAME": "PERSON", "MIDDLENAME": "PERSON", "LASTNAME": "PERSON",
    "FULLNAME": "PERSON", "NAME": "PERSON", "DISPLAYNAME": "PERSON",
    "PREFIX": "PERSON",    # Mr., Dr. — appears attached to names
    "SUFFIX": "PERSON",    # Jr., Sr.
    # ── Contact ──────────────────────────────────────────────────────────────
    "EMAIL": "EMAIL_ADDRESS",
    "PHONE_NUMBER": "PHONE_NUMBER",
    # ── Location ─────────────────────────────────────────────────────────────
    "STREETADDRESS": "LOCATION", "SECONDARYADDRESS": "LOCATION",
    "STREET": "LOCATION",  "CITY": "LOCATION", "STATE": "LOCATION",
    "COUNTY": "LOCATION",  "ZIPCODE": "LOCATION", "BUILDINGNUMBER": "LOCATION",
    "NEARBYGPSCOORDINATE": "LOCATION",
    # ── Organization ─────────────────────────────────────────────────────────
    "COMPANY_NAME": "ORGANIZATION",
    "CREDITCARDISSUER": "ORGANIZATION",   # Visa, Mastercard, etc.
    # ── Financial / Banking ───────────────────────────────────────────────────
    # Real observed labels (tested empirically):
    # - Model uses NUMBER for credit card numbers (not CREDITCARDNUMBER in practice)
    # - Model uses ACCOUNTNUMBER + MASKEDNUMBER for IBANs (splits across tokens)
    # - IBAN and CREDITCARDNUMBER labels exist in vocab but rarely triggered
    "CREDITCARDNUMBER": "CREDIT_CARD",
    "CREDITCARDCVV": "CREDIT_CARD",      # CVV is part of card data
    "NUMBER": "CREDIT_CARD",             # Observed: model uses NUMBER for card-like numbers
    "IBAN": "IBAN_CODE",
    "BIC": "ID",                          # Bank Identifier Code
    "ACCOUNTNUMBER": "ID",
    "ACCOUNTNAME": "ID",
    "MASKEDNUMBER": "ID",                # Used for IBAN fragments and masked card numbers
    # ── Crypto ───────────────────────────────────────────────────────────────
    "BITCOINADDRESS": "CRYPTO",
    "ETHEREUMADDRESS": "CRYPTO",
    "LITECOINADDRESS": "CRYPTO",
    # ── Network / Tech ───────────────────────────────────────────────────────
    # NOTE: model outputs "IP" for IPv4 (not "IPV4"). Both kept for safety.
    "IPV4": "IP_ADDRESS", "IPV6": "IP_ADDRESS", "IP": "IP_ADDRESS",
    "MAC": "MAC_ADDRESS",
    "URL": "URL",
    "USERAGENT": "ID",
    # ── Credentials ──────────────────────────────────────────────────────────
    "USERNAME": "USERNAME",
    "PASSWORD": "PASSWORD",
    "PIN": "PASSWORD",
    # ── Government / Vehicle IDs ─────────────────────────────────────────────
    "SSN": "US_SSN",
    "VEHICLEVIN": "ID",    # Vehicle Identification Number
    "VEHICLEVRM": "ID",    # Vehicle Registration Mark
    "PHONEIMEI": "ID",     # Device IMEI number
    # ── Temporal ─────────────────────────────────────────────────────────────
    "DATE": "DATE_TIME",
    "TIME": "DATE_TIME",
    # ── Professional / Demographic ───────────────────────────────────────────
    "JOBTITLE": "NRP", "JOBDESCRIPTOR": "NRP", "JOBAREA": "NRP", "JOBTYPE": "NRP",
    "SEX": "NRP", "SEXTYPE": "NRP", "GENDER": "NRP",
    # AMOUNT, CURRENCY, CURRENCYNAME, CURRENCYSYMBOL, CURRENCYCODE, NUMBER,
    # ORDINALDIRECTION are not PII — intentionally omitted
}

# ─────────────────────────────────────────────────────────────────────────────
#  PT-BR NER models
# ─────────────────────────────────────────────────────────────────────────────

# LeNER-Br (legal-Portuguese) label set used by pierreguillou/ner-bert-*-pt-lenerbr
# and dominguesm/ner-bertimbau-large-pt-legal-br.
# Source dataset: https://github.com/peluz/lener-br
# Legal-reference labels (LEGISLACAO, JURISPRUDENCIA) are preserved as dedicated
# entity types so they can be either redacted or selectively kept.
_LENERBR_ENTITY_MAPPING: dict[str, str] = {
    "PESSOA": "PERSON",
    "ORGANIZACAO": "ORGANIZATION",
    "LOCAL": "LOCATION",
    "TEMPO": "DATE_TIME",
    "LEGISLACAO": "LAW_REFERENCE",
    "JURISPRUDENCIA": "CASE_REFERENCE",
}

# HAREM / Portuguese classic NER (monilouise/ner_pt_br, lfcc/bert-portuguese-ner,
# marquesafonso/bertimbau-*-ner-selective).
# Covers both uppercase (HAREM canonical) and title-case (some variants) labels.
_HAREM_PT_ENTITY_MAPPING: dict[str, str] = {
    "PESSOA": "PERSON",       "Pessoa": "PERSON",
    "LOCAL": "LOCATION",      "Localizacao": "LOCATION", "Local": "LOCATION",
    "ORGANIZACAO": "ORGANIZATION", "Organizacao": "ORGANIZATION",
    "TEMPO": "DATE_TIME",     "Tempo": "DATE_TIME",
    "VALOR": "MONEY",         "Valor": "MONEY",
    # Also accept the 3-letter abbreviations used by some checkpoints
    "PER": "PERSON",
    "LOC": "LOCATION",
    "ORG": "ORGANIZATION",
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

# Default transformer model IDs per language.
# Used by default_transformer_for_lang() to auto-select the best NER model
# when the user hasn't explicitly picked one via --transformer-model.
DEFAULT_MODEL = "Davlan/xlm-roberta-base-ner-hrl"

_LANG_DEFAULT_MODEL: dict[str, str] = {
    "pt": "pierreguillou/ner-bert-base-cased-pt-lenerbr",
}


def default_transformer_for_lang(lang: str) -> str:
    """Return the recommended default NER model for *lang*.

    Falls back to the multilingual default for languages with no dedicated
    registered model. Called from CLI/API entry points after lang is known
    so Portuguese documents automatically use a PT-BR fine-tuned model
    (better on PT-BR person names, legal/financial docs).
    """
    return _LANG_DEFAULT_MODEL.get(lang, DEFAULT_MODEL)


MODEL_REGISTRY: dict[str, ModelEntry] = {
    # ── Multilingual general-purpose ─────────────────────────────────────────
    "Davlan/xlm-roberta-base-ner-hrl": ModelEntry(
        entity_mapping=_DEFAULT_ENTITY_MAPPING,
        description="Multilingual NER (default) — covers en, pt, es, fr, de, ar, zh",
        languages=["en", "pt", "es", "fr", "de", "ar", "zh"],
    ),
    "Davlan/distilbert-base-multilingual-cased-ner-hrl": ModelEntry(
        entity_mapping=_DEFAULT_ENTITY_MAPPING,
        description="Compact multilingual NER — same label set as xlm-roberta-hrl, faster inference",
        languages=["en", "pt", "es", "fr", "de", "ar", "zh"],
    ),
    # ── English general-purpose (CoNLL-2003) ─────────────────────────────────
    "dslim/bert-base-NER": ModelEntry(
        entity_mapping=_CONLL_EN_ENTITY_MAPPING,
        description="Fast English NER (CoNLL-2003) — PER, ORG, LOC only",
        languages=["en"],
    ),
    "Jean-Baptiste/roberta-large-ner-english": ModelEntry(
        entity_mapping=_CONLL_EN_ENTITY_MAPPING,
        description="Accurate English NER (CoNLL-2003) — PER, ORG, LOC only",
        languages=["en"],
    ),
    # ── Clinical / Medical ───────────────────────────────────────────────────
    "obi/deid_roberta_i2b2": ModelEntry(
        entity_mapping=_I2B2_ENTITY_MAPPING,
        description="Clinical de-identification (i2b2 2014 PHI) — NAME, DATE, CONTACT, ID, LOCATION, AGE",
        languages=["en"],
    ),
    "d4data/biomedical-ner-all": ModelEntry(
        entity_mapping=_BIOMEDICAL_ENTITY_MAPPING,
        description="Biomedical NER (BC5CDR + NCBI-disease + others) — DISEASE, DRUG, GENE, CELL, SPECIES",
        languages=["en"],
    ),
    # ── Financial / Banking PII ──────────────────────────────────────────────
    "lakshyakh93/deberta_finetuned_pii": ModelEntry(
        entity_mapping=_DEBERTA_PII_ENTITY_MAPPING,
        description="Financial & general PII (DeBERTa) — IBAN, BIC, account numbers, credit card CVV, crypto addresses, 60+ types",
        languages=["en"],
    ),
    # ── Cybersecurity ────────────────────────────────────────────────────────
    "attack-vector/SecureModernBERT-NER": ModelEntry(
        entity_mapping=_SECURE_MODERNBERT_ENTITY_MAPPING,
        description="Cybersecurity-focused NER — extracts CVE, malware, threat actors, hashes, IPs",
        languages=["en"],
    ),
    # ── Portuguese (PT-BR) ──────────────────────────────────────────────────
    # Recommended default for Brazilian documents (certidões, contratos, etc.).
    # LeNER-Br fine-tune — best on formal/legal Portuguese.
    "pierreguillou/ner-bert-large-cased-pt-lenerbr": ModelEntry(
        entity_mapping=_LENERBR_ENTITY_MAPPING,
        description="PT-BR NER (BERT-large / LeNER-Br) — highest F1 on formal/legal Brazilian Portuguese. Recommended for certidões, contratos, decisões.",
        languages=["pt"],
    ),
    "pierreguillou/ner-bert-base-cased-pt-lenerbr": ModelEntry(
        entity_mapping=_LENERBR_ENTITY_MAPPING,
        description="PT-BR NER (BERT-base / LeNER-Br) — ~3x faster than the large variant with ~2% F1 drop. Same label set.",
        languages=["pt"],
    ),
    # Generic PT-BR NER (HAREM-style labels) — good for free-text docs
    "monilouise/ner_pt_br": ModelEntry(
        entity_mapping=_HAREM_PT_ENTITY_MAPPING,
        description="PT-BR NER (BERT-base / HAREM+LeNER-Br) — general-purpose Brazilian Portuguese with PESSOA, LOCAL, ORGANIZACAO, TEMPO, VALOR.",
        languages=["pt"],
    ),
    "marquesafonso/bertimbau-large-ner-selective": ModelEntry(
        entity_mapping=_HAREM_PT_ENTITY_MAPPING,
        description="PT-BR NER (BERTimbau-large / HAREM Selective) — strong on Brazilian Portuguese, 5 entity types.",
        languages=["pt"],
    ),
    "lfcc/bert-portuguese-ner": ModelEntry(
        entity_mapping=_CONLL_EN_ENTITY_MAPPING,  # uses 3-letter CoNLL labels (PER, ORG, LOC)
        description="PT-BR NER (Portuguese-BERT / CoNLL-style) — simple PER, ORG, LOC labels.",
        languages=["pt"],
    ),
    "dominguesm/ner-bertimbau-large-pt-legal-br": ModelEntry(
        entity_mapping=_LENERBR_ENTITY_MAPPING,
        description="PT-BR NER (BERTimbau-large on LeNER-Br) — alternative legal-Portuguese model from the BERTimbau family.",
        languages=["pt"],
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
