# /engine.py

import hashlib
import hmac
import sys
from typing import List

import pandas as pd
import spacy
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NerModelConfiguration, TransformersNlpEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig
from presidio_anonymizer.operators import Operator, OperatorType

from .config import (
    DB_PATH,
    ENTITY_MAPPING,
    SECRET_KEY,
    TRANSFORMER_MODEL,
    bulk_save_entities,
)


SUPPORTED_LANGUAGES = {
    "ca": "Catalan", "zh": "Chinese", "hr": "Croatian", "da": "Danish",
    "nl": "Dutch", "en": "English", "fi": "Finnish", "fr": "French",
    "de": "German", "el": "Greek", "it": "Italian", "ja": "Japanese",
    "ko": "Korean", "lt": "Lithuanian", "mk": "Macedonian", "nb": "Norwegian Bokmål",
    "pl": "Polish", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
    "sl": "Slovenian", "es": "Spanish", "sv": "Swedish", "uk": "Ukrainian"
}


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
        slug_length = params.get("slug_length", None) if params else None
        entity_collector = params.get("entity_collector", None) if params else None

        display_hash = full_hash[:slug_length] if slug_length is not None else full_hash

        if entity_collector is not None:
            entity_collector.append((entity_type, clean_text, display_hash, full_hash))
        
        return f"[{entity_type}_{display_hash}]"

    def validate(self, params: dict | None = None) -> None: pass
    def operator_name(self) -> str: return "custom_slug"
    def operator_type(self) -> OperatorType: return OperatorType.Anonymize


def load_custom_recognizers() -> List[PatternRecognizer]:
    """Loads custom regex-based recognizers for cybersecurity entities."""
    cve_pattern = Pattern(name="CVE Pattern", regex=r"CVE-\d{4}-\d+", score=0.8)
    cve_recognizer = PatternRecognizer(supported_entity="CVE", context=["CVE"],  patterns=[cve_pattern])
    ip_pattern = Pattern(name="IP Address Pattern", regex=r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", score=0.6)
    ipv6_pattern = Pattern(name="IPv6 Address Pattern", regex=r"(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,6})|:)|:((:[0-9a-fA-F]{1,7})|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", score=0.6)
    ip_recognizer = PatternRecognizer(supported_entity="IP_ADDRESS", context=["IP, IPV6"], patterns=[ip_pattern, ipv6_pattern])
    return [cve_recognizer, ip_recognizer]


class AnonymizationOrchestrator:
    """Orchestrates the text anonymization process using Presidio."""

    def __init__(self, lang: str, allow_list: List[str], entities_to_preserve: List[str], slug_length: int | None = None):
        self.lang = lang
        self.allow_list = allow_list
        self.entities_to_preserve = entities_to_preserve
        self.slug_length = slug_length
        self.analyzer_engine, self.anonymizer_engine = self._setup_engines()

    def _setup_engines(self) -> tuple[AnalyzerEngine, AnonymizerEngine]:
        """Initializes and configures the Presidio Analyzer and Anonymizer engines."""
        lang_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
        spacy_model_name = lang_model_map.get(self.lang, f"{self.lang}_core_news_lg")

        trf_model_config = [
            {"lang_code": "en", "model_name": {"spacy": "en_core_web_lg", "transformers": TRANSFORMER_MODEL}},
            {"lang_code": self.lang, "model_name": {"spacy": spacy_model_name, "transformers": TRANSFORMER_MODEL}}
        ]

        ner_config = NerModelConfiguration(
            model_to_presidio_entity_mapping=ENTITY_MAPPING, 
            aggregation_strategy="max", 
            labels_to_ignore=["O"]
        )
        
        nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_config)
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=[self.lang, "en"])
        
        # Remove built-in recognizers that are not desired
        try:
            analyzer.registry.remove_recognizer("DateRecognizer")
            analyzer.registry.remove_recognizer("MedicalLicenseRecognizer")
        except Exception:
            # Recognizer might not exist for the selected language, fail silently
            pass

        for recognizer in load_custom_recognizers():
            analyzer.registry.add_recognizer(recognizer)
            
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)
        
        return analyzer, anonymizer

    def anonymize_text(self, text: str) -> str:
        """Anonymizes a single block of text."""
        if not isinstance(text, str) or not text.strip():
            return text

        entity_collector = []
        entities = self._get_entities_to_anonymize()
        analyzer_results = self.analyzer_engine.analyze(
            text=text, language=self.lang, score_threshold=0.6,
            allow_list=self.allow_list, entities=entities
        )
        anonymizer_results = self.anonymizer_engine.anonymize(
            text=text, analyzer_results=analyzer_results, # type: ignore
            operators={
                "DEFAULT": OperatorConfig(
                    "custom_slug", 
                    {
                        "slug_length": self.slug_length, 
                        "entity_collector": entity_collector
                    }
                )
            }
        )
        
        if entity_collector:
            bulk_save_entities(DB_PATH, entity_collector)

        return anonymizer_results.text

    def anonymize_texts(self, texts: List[str], batch_size: int = 32) -> List[str]:
        """Anonymizes a list of texts in batches."""
        results = []
        entity_collector = []
        entities_to_anonymize = self._get_entities_to_anonymize()

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch = [str(text) if pd.notna(text) else "" for text in batch]

            analyzer_results = [
                self.analyzer_engine.analyze(
                    text=text, language=self.lang, score_threshold=0.6,
                    allow_list=self.allow_list, entities=entities_to_anonymize
                )
                for text in batch
            ]

            anonymized_texts = [
                self.anonymizer_engine.anonymize(
                    text=batch[j], analyzer_results=analyzer_results[j], # type: ignore
                    operators={
                        "DEFAULT": OperatorConfig(
                            "custom_slug", 
                            {
                                "slug_length": self.slug_length, 
                                "entity_collector": entity_collector
                            }
                        )
                    }
                ).text
                for j in range(len(batch))
            ]
            results.extend(anonymized_texts)

        if entity_collector:
            bulk_save_entities(DB_PATH, entity_collector)

        return results

    def _get_entities_to_anonymize(self) -> List[str]:
        """Gets the list of entities to anonymize based on the preserve list."""
        all_entities = self.analyzer_engine.get_supported_entities()
        return [
            ent for ent in all_entities 
            if not self.entities_to_preserve or ent not in self.entities_to_preserve
        ]