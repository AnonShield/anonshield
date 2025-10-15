# /engine.py

import hashlib
import hmac
import os
import subprocess
import sys

import pandas as pd
import spacy
import spacy.cli
from huggingface_hub import snapshot_download
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NerModelConfiguration, TransformersNlpEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig
from presidio_anonymizer.operators import Operator, OperatorType

from config import (
    DB_PATH,
    ENTITY_MAPPING,
    SECRET_KEY,
    TRANSFORMER_MODEL,
    TRF_MODEL_PATH,
    save_entity,
)


class CustomSlugAnonymizer(Operator):
    """A custom Presidio operator that replaces text with a hashed slug and records it in a database."""
    def operate(self, text: str, params: dict | None = None) -> str:
        if SECRET_KEY is None:
            raise ValueError("ANON_SECRET_KEY environment variable not set")
        
        clean_text = " ".join(text.split()).strip()
        full_hash = hmac.new(
            SECRET_KEY.encode(), clean_text.encode(), hashlib.sha256
        ).hexdigest()
        
        entity_type = params.get("entity_type", "UNKNOWN") if params else "UNKNOWN"
        save_entity(DB_PATH, entity_type, clean_text, full_hash, full_hash)
        
        return f"[{entity_type}_{full_hash}]"

    def validate(self, params: dict | None = None) -> None: pass
    def operator_name(self) -> str: return "custom_slug"
    def operator_type(self) -> OperatorType: return OperatorType.Anonymize


def load_custom_recognizers():
    """Loads custom regex-based recognizers for cybersecurity entities."""
    cve_pattern = Pattern(name="CVE Pattern", regex=r"CVE-\d{4}-\d+", score=0.8)
    cve_recognizer = PatternRecognizer(supported_entity="CVE", patterns=[cve_pattern])
    ip_pattern = Pattern(name="IP Address Pattern", regex=r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", score=0.6)
    ipv6_pattern = Pattern(name="IPv6 Address Pattern", regex=r"(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,6})|:)|:((:[0-9a-fA-F]{1,7})|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", score=0.6)
    ip_recognizer = PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[ip_pattern, ipv6_pattern])
    return [cve_recognizer, ip_recognizer]


def get_presidio_engines(lang: str = "pt") -> tuple[AnalyzerEngine, AnonymizerEngine]:
    """Initializes and returns the Presidio Analyzer and Anonymizer engines for a specific language."""
    
    lang_model_map = { "pt": "pt_core_news_lg", "en": "en_core_web_lg" }
    spacy_model_name = lang_model_map.get(lang, "xx_ent_wiki_sm")

    try:
        spacy.load(spacy_model_name)
        print(f"[*] Successfully loaded spaCy model '{spacy_model_name}'.")
    except OSError:
        print(f"[!] Critical Error: spaCy model '{spacy_model_name}' could not be loaded even after download.", file=sys.stderr)
        sys.exit(1)

    trf_model_config = [{"lang_code": lang, "model_name": {"spacy": spacy_model_name, "transformers": TRANSFORMER_MODEL}}]
    ner_model_configuration = NerModelConfiguration(
        model_to_presidio_entity_mapping=ENTITY_MAPPING, alignment_mode="expand",
        aggregation_strategy="max", labels_to_ignore=["O"],
    )
    transformers_nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_model_configuration)
    analyzer_engine = AnalyzerEngine(
        nlp_engine=transformers_nlp_engine, supported_languages=[lang, "en"], log_decision_process=False,
    )
    for recognizer in load_custom_recognizers():
        analyzer_engine.registry.add_recognizer(recognizer)
    anonymizer_engine = AnonymizerEngine()
    anonymizer_engine.add_anonymizer(CustomSlugAnonymizer)
    return analyzer_engine, anonymizer_engine

def batch_process_text(
    texts: list[str],
    analyzer_engine: AnalyzerEngine,
    anonymizer_engine: AnonymizerEngine,
    lang: str,
    allow_list: list[str],
    entities_to_preserve: list[str] | None = None,
    batch_size: int = 32
) -> list[str]:
    """Anonymizes a list of texts in batches for performance."""
    results = []
    
    all_entities = analyzer_engine.get_supported_entities()
    entities_to_anonymize = [
        ent for ent in all_entities if ent != "DATE_TIME" and (not entities_to_preserve or ent not in entities_to_preserve)
    ]

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch = [str(text) if pd.notna(text) else "" for text in batch]

        analyzer_results = [
            analyzer_engine.analyze(
                text=text, language=lang, score_threshold=0.6,
                allow_list=allow_list, entities=entities_to_anonymize
            )
            for text in batch
        ]

        anonymized_texts = [
            anonymizer_engine.anonymize(
                text=batch[j], analyzer_results=analyzer_results[j],
                operators={"DEFAULT": OperatorConfig("custom_slug")}
            ).text
            for j in range(len(batch))
        ]
        results.extend(anonymized_texts)
    return results

def anonymize_text(
    text: str,
    analyzer_engine: AnalyzerEngine,
    anonymizer_engine: AnonymizerEngine,
    allow_list: list[str],
    entities_to_preserve: list[str] | None = None,
    lang: str = "pt"
) -> str:
    """Anonymizes a single block of text."""
    if not isinstance(text, str) or not text.strip():
        return text

    all_entities = analyzer_engine.get_supported_entities()
    entities_to_anonymize = [
        ent for ent in all_entities if ent != "DATE_TIME" and (not entities_to_preserve or ent not in entities_to_preserve)
    ]
    analyzer_results = analyzer_engine.analyze(
        text=text, language=lang, score_threshold=0.6,
        allow_list=allow_list, entities=entities_to_anonymize,
    )
    anonymizer_results = anonymizer_engine.anonymize(
        text=text, analyzer_results=analyzer_results,
        operators={"DEFAULT": OperatorConfig("custom_slug")},
    )
    return anonymizer_results.text