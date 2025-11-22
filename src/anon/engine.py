# /engine.py

import hashlib
import hmac
import sys
from typing import Dict, Iterable, List

import pandas as pd
import spacy
import torch
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.batch_analyzer_engine import BatchAnalyzerEngine
from presidio_analyzer.nlp_engine import NerModelConfiguration, TransformersNlpEngine
from presidio_anonymizer import AnonymizerEngine, OperatorConfig
from presidio_anonymizer.operators import Operator, OperatorType

from .config import (
    DB_PATH,
    ENTITY_MAPPING,
    SECRET_KEY,
    TRANSFORMER_MODEL,
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
        clean_text = " ".join(text.split()).strip()
        full_hash = hashlib.sha256(clean_text.encode()).hexdigest()

        entity_type = params.get("entity_type", "UNKNOWN") if params else "UNKNOWN"
        slug_length = params.get("slug_length", None) if params else None
        
        display_hash = full_hash[:slug_length] if slug_length is not None else full_hash

        if params and "entity_collector" in params:
            params["entity_collector"].append((entity_type, clean_text, display_hash, full_hash))

        return f"[{entity_type}_{display_hash}]"

    def validate(self, params: dict | None = None) -> None: pass
    def operator_name(self) -> str: return "custom_slug"
    def operator_type(self) -> OperatorType: return OperatorType.Anonymize


def load_custom_recognizers(langs: List[str]) -> List[PatternRecognizer]:
    """Loads custom regex-based recognizers for cybersecurity entities for specific languages."""
    
    # URL recognizer
    url_pattern = Pattern(
      name="URL Pattern", 
      regex=r"(?:https?://|ftp://|www\.)[^\s]+\.(?:com|net|org|edu|gov|mil|int|br|app|dev|io|co|uk|de|fr|es|it|ru|cn|jp|kr|au|ca|mx|ar|cl|pe|co\.uk|com\.br|org\.br|gov\.br|edu\.br|net\.br|vercel\.app|herokuapp\.com|github\.io|gitlab\.io|netlify\.app|firebase\.app|appspot\.com|cloudfront\.net|amazonaws\.com|azure\.com|digitalocean\.com)[^\s]*",
      score=0.7
    )

    # IP address recognizers (IPv4 and IPv6)
    ip_pattern = Pattern(name="IP Address Pattern", regex=r"(?<!\d\.)\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b(?!\.\d)", score=0.6)
    ipv6_pattern = Pattern(name="IPv6 Address Pattern", regex=r"^((?:[0-9A-Fa-f]{1,4}:){7}[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,7}:|:(?:(?::[0-9A-Fa-f]{1,4}){1,7}|:)|(?:[0-9A-Fa-f]{1,4}:){1,6}:[0-9A-Fa-f]{1,4}|(?:[0-9A-Fa-f]{1,4}:){1,5}(?::[0-9A-Fa-f]{1,4}){1,2}|(?:[0-9A-Fa-f]{1,4}:){1,4}(?::[0-9A-Fa-f]{1,4}){1,3}|(?:[0-9A-Fa-f]{1,4}:){1,3}(?::[0-9A-Fa-f]{1,4}){1,4}|(?:[0-9A-Fa-f]{1,4}:){1,2}(?::[0-9A-Fa-f]{1,4}){1,5}|[0-9A-Fa-f]{1,4}:(?:(?::[0-9A-Fa-f]{1,4}){1,6})|::(?:[0-9A-Fa-f]{1,4}:){0,5}(?:[0-9A-Fa-f]{1,4}|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))|(?:[0-9A-Fa-f]{1,4}:){1,4}:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))$", score=0.6)

    hostname_patterns = [
        Pattern(
            name="FQDN Pattern",
            regex=r"\b([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b",
            score=0.6
        ),
        Pattern(
            name="Common Hostname Pattern",
            regex=r"\b(localhost)\b", # Simplificado para focar no seu problema
            score=0.65
        ),
        Pattern(
            name="Certificate CN Pattern",
            regex=r"CN=([a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]|[a-f0-9]{8,16})\b",
            score=0.7
        ),
        Pattern(
            name="Standalone Hex Hostname Pattern",
            regex=r"(?<![:/])(?<![vV])\b(?!20\d{10})[a-f0-9]{12,16}\b(?!\.)",
            score=0.6
        ),
    ]


    # 2. Hashes (SHA256 e MD5 com dois-pontos)
    hash_patterns = [
        # Para: 0631792DF994C0A697B4FD08A4BDBDF47FE99620C3AF773B5CAB7052CC0E119E
        Pattern(name="SHA256 Hash", regex=r"\b[0-9a-fA-F]{64}\b", score=0.8),
        # Para: 8d:3d:d5:0a:9c:d9:5f:5f:7b:96:cd:b4:9f:9c:c0:18
        Pattern(
            name="MD5 Colon-Separated Hash",
            regex=r"\b([0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}\b",
            score=0.85 # Score alto para vencer o IPv6
        )
    ]

    # 3. UUIDs (Para todos os Report IDs, Task IDs, etc.)
    uuid_pattern = Pattern(
        name="UUID Pattern",
        regex=r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
        score=0.8
    )

    # 4. Seriais de Certificado (Os de 40 caracteres)
    serial_pattern = Pattern(
        name="Certificate Serial (40-char Hex)",
        regex=r"\b[0-9a-fA-F]{40}\b",
        score=0.75
    )

    # 5. Strings CPE (cpe:/a:...)
    cpe_pattern = Pattern(
        name="CPE String",
        regex=r"\bcpe:/[a-z]:[^:]+:[^:]+(:[^:]+){0,4}\b",
        score=0.7
    )
    
    # 6. Corpos de Certificado (Blocos Base64)
    cert_body_pattern = Pattern(
        name="Certificate Body (Base64)",
        regex=r"\bMII[a-zA-Z0-9+/=\n]{100,}\b", # Pega blocos Base64 que começam com MII e são longos
        score=0.8
    )

    # === CARREGANDO OS RECOGNIZERS ===
    
    recognizers = []
    for lang in langs:
        recognizers.append(PatternRecognizer(supported_entity="URL", patterns=[url_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[ip_pattern, ipv6_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="HOSTNAME", patterns=hostname_patterns, supported_language=lang))
        
        # Adicionando os novos
        recognizers.append(PatternRecognizer(supported_entity="HASH", patterns=hash_patterns, supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="UUID", patterns=[uuid_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CERT_SERIAL", patterns=[serial_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CPE_STRING", patterns=[cpe_pattern], supported_language=lang))
        recognizers.append(PatternRecognizer(supported_entity="CERT_BODY", patterns=[cert_body_pattern], supported_language=lang))
    return recognizers

class AnonymizationOrchestrator:
    """Orchestrates the text anonymization process using Presidio."""

    def __init__(self, lang: str, allow_list: List[str], entities_to_preserve: List[str], slug_length: int | None = None):
        self.lang = lang
        self.allow_list = allow_list
        self.entities_to_preserve = entities_to_preserve
        self.slug_length = slug_length
        self.total_entities_processed = 0
        self.entity_counts = {}
        # Cache para armazenar resultados de strings já processadas
        self.cache = {}
        self.analyzer_engine, self.anonymizer_engine = self._setup_engines()

    def _setup_engines(self) -> tuple[BatchAnalyzerEngine, AnonymizerEngine]:
        """Initializes and configures the Presidio Analyzer and Anonymizer engines."""
        lang_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
        
        supported_langs = set(["en", self.lang])

        trf_model_config = []
        for lang_code in supported_langs:
            spacy_model_name = lang_model_map.get(lang_code, f"{lang_code}_core_news_lg")
            trf_model_config.append(
                {"lang_code": lang_code, "model_name": {"spacy": spacy_model_name, "transformers": TRANSFORMER_MODEL}}
            )

        ner_config = NerModelConfiguration(
            model_to_presidio_entity_mapping=ENTITY_MAPPING, 
            aggregation_strategy="max", 
            labels_to_ignore=["O"]
        )
        
        nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_config)
        
        # 1. Create a standard AnalyzerEngine
        core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=list(supported_langs))
        
        # 2. Add recognizers to the standard engine
        try:
            core_analyzer.registry.remove_recognizer("DateRecognizer")
            core_analyzer.registry.remove_recognizer("MedicalLicenseRecognizer")
            core_analyzer.registry.remove_recognizer("IpRecognizer")
        except Exception:
            pass

        for recognizer in load_custom_recognizers(langs=core_analyzer.supported_languages):
            core_analyzer.registry.add_recognizer(recognizer)
        
        # 3. Wrap the standard engine with BatchAnalyzerEngine
        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
            
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)
        
        return batch_analyzer, anonymizer

    def anonymize_text(self, text: str, operator_params: dict = None) -> str:
        """Anonymizes a single block of text by wrapping it in a list."""
        if not isinstance(text, str) or not text.strip():
            return text
        return self.anonymize_texts([text], operator_params=operator_params)[0]

    def anonymize_texts(self, texts: List[str], operator_params: dict = None) -> List[str]:
        """
        Anonymizes a list of texts using a fast, direct SpaCy pipeline approach,
        combined with an instance-level cache.
        """
        if not texts:
            return []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        final_anonymized_list = [""] * len(original_texts)
        
        texts_to_process_map = {} 
        for i, text in enumerate(original_texts):
            if text in self.cache:
                final_anonymized_list[i] = self.cache[text]
            else:
                if text not in texts_to_process_map:
                    texts_to_process_map[text] = []
                texts_to_process_map[text].append(i)

        if not texts_to_process_map:
            return final_anonymized_list

        unique_texts_to_process = list(texts_to_process_map.keys())
        
        # Setup for anonymization
        if operator_params is None: operator_params = {}
        entity_collector = operator_params.get("entity_collector")
        entities_to_anonymize = self._get_entities_to_anonymize()
        nlp = self.analyzer_engine.analyzer_engine.nlp_engine.nlp
        
        docs = nlp.pipe(unique_texts_to_process, batch_size=500)

        for doc in docs:
            original_doc_text = doc.text
            new_text_parts = []
            last_index = 0
            
            sorted_ents = sorted(doc.ents, key=lambda e: e.start_char)

            for ent in sorted_ents:
                if ent.label_ not in entities_to_anonymize or ent.text in self.allow_list:
                    continue

                new_text_parts.append(original_doc_text[last_index:ent.start_char])
                
                clean_text = " ".join(ent.text.split()).strip()
                full_hash = hashlib.sha256(clean_text.encode()).hexdigest()
                display_hash = full_hash[:self.slug_length] if self.slug_length is not None else full_hash

                if entity_collector is not None:
                    entity_collector.append((ent.label_, clean_text, display_hash, full_hash))

                new_text_parts.append(f"[{ent.label_}_{display_hash}]")
                last_index = ent.end_char
            
            new_text_parts.append(original_doc_text[last_index:])
            anonymized_text = "".join(new_text_parts)

            self.cache[original_doc_text] = anonymized_text
            for index in texts_to_process_map[original_doc_text]:
                final_anonymized_list[index] = anonymized_text

        return final_anonymized_list

    def anonymize_texts_legacy(self, texts: List[str], operator_params: dict = None) -> List[str]:
        """Anonymizes a list of texts using the BatchAnalyzerEngine (legacy method)."""
        if not texts:
            return []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        final_anonymized_list = [""] * len(original_texts)
        
        texts_to_process_map = {}
        for i, text in enumerate(original_texts):
            if text in self.cache:
                final_anonymized_list[i] = self.cache[text]
            else:
                if text not in texts_to_process_map:
                    texts_to_process_map[text] = []
                texts_to_process_map[text].append(i)

        if not texts_to_process_map:
            return final_anonymized_list
            
        unique_texts_to_process = list(texts_to_process_map.keys())
        entities_to_anonymize = self._get_entities_to_anonymize()
        
        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            unique_texts_to_process,
            language=self.lang,
            entities=entities_to_anonymize,
            score_threshold=0.6,
        )

        if operator_params is None: operator_params = {}
        operator_params["total_entities_counter"] = self
        operator_params["entity_counts"] = self.entity_counts

        for text, analyzer_results in zip(unique_texts_to_process, analyzer_results_iterator):
            filtered_analyzer_results = [
                result for result in analyzer_results
                if text[result.start:result.end] not in self.allow_list
            ]
            anonymizer_result = self.anonymizer_engine.anonymize(
                text=text,
                analyzer_results=filtered_analyzer_results,
                operators={"DEFAULT": OperatorConfig("custom_slug", operator_params)},
            )
            
            anonymized_text = anonymizer_result.text
            self.cache[text] = anonymized_text
            for index in texts_to_process_map[text]:
                final_anonymized_list[index] = anonymized_text
        
        return final_anonymized_list

    def _get_entities_to_anonymize(self) -> List[str]:
        """Gets the list of entities to anonymize based on the preserve list."""
        all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
        return [
            ent for ent in all_entities 
            if not self.entities_to_preserve or ent not in self.entities_to_preserve
        ]