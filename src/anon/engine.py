# src/anon/engine.py

import hashlib
import hmac
import re
from typing import Dict, List, Optional, Union
from collections import OrderedDict # Add this import
import logging

import pandas as pd  # type: ignore
import spacy  # type: ignore
import torch  # type: ignore
from presidio_analyzer import (  # type: ignore
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)
from presidio_analyzer.batch_analyzer_engine import (  # type: ignore
    BatchAnalyzerEngine,
)
from presidio_analyzer.nlp_engine import (  # type: ignore
    NerModelConfiguration,
    TransformersNlpEngine,
)
from presidio_anonymizer import AnonymizerEngine, OperatorConfig  # type: ignore
from presidio_anonymizer.operators import Operator, OperatorType  # type: ignore

from .config import (
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
    """
    Custom Presidio operator that replaces text with an HMAC-based slug.
    """
    def operate(self, text: str, params: dict | None = None) -> str:
        # 1. Clean the text (remove extra spaces)
        clean_text = " ".join(text.split()).strip()
        
        if not SECRET_KEY:
            raise ValueError("SECRET_KEY is not set.")

        # 2. Generate a secure HMAC (using the secret key)
        full_hash = hmac.new(
            SECRET_KEY.encode(), 
            clean_text.encode(), 
            hashlib.sha256
        ).hexdigest()

        entity_type = params.get("entity_type", "UNKNOWN") if params else "UNKNOWN"
        slug_length = params.get("slug_length", None) if params else None
        
        display_hash = full_hash[:slug_length] if slug_length is not None else full_hash

        if params and "entity_collector" in params:
            params["entity_collector"].append((entity_type, clean_text, display_hash, full_hash))

        return f"[{entity_type}_{display_hash}]"

    def validate(self, params: dict | None = None) -> None: pass
    def operator_name(self) -> str: return "custom_slug"
    def operator_type(self) -> OperatorType: return OperatorType.Anonymize


def load_custom_recognizers(langs: List[str], regex_priority: bool = False) -> List[PatternRecognizer]:
    """Loads Regex recognizers optimized for infrastructure/cybersecurity/PII entities."""
    
    # Define a score boost for regex patterns if priority is enabled
    SCORE_BOOST = 0.15 if regex_priority else 0.0

    # --- 1. URL & NETWORK ---
    url_pattern = Pattern(
      name="URL Pattern", 
      regex=r"(?:https?://|ftp://|www\.)[^\s]+(?:\.(?:com|net|org|edu|gov|mil|int|br|app|dev|io|co|uk|de|fr|es|it|ru|cn|jp|kr|au|ca|mx|ar|cl|pe|co\.uk|com\.br|org\.br|gov\.br|edu\.br|net\.br|vercel\.app|herokuapp\.com|github\.io|gitlab\.io|netlify\.app|firebase\.app|appspot\.com|cloudfront\.net|amazonaws\.com|azure\.com|digitalocean\.com)|localhost|(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))(?::[0-9]{1,5})?(?:/[^\s]*)?",
      score=0.7 + SCORE_BOOST
    )

    ip_pattern = Pattern(
        name="IP Address Pattern", 
        regex=r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b", 
        score=0.85 + SCORE_BOOST
    )
    
    ipv6_pattern = Pattern(
      name="IPv6 Address Pattern", 
      regex=r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))", 
      score=0.6 + SCORE_BOOST
    )
    serial_pattern = Pattern(
        name="Certificate Serial",
        regex=r"\b[0-9a-fA-F]{16,40}\b",
        score=0.75 + SCORE_BOOST
    )
    
    oid_pattern = Pattern(
        name="OID Pattern",
        regex=r"\b[0-2](?:\.\d+){3,}\b", 
        score=0.95 + SCORE_BOOST
    )
    port_pattern = Pattern(
        name="Port/Protocol",
        regex=r"\b\d{1,5}/(?:tcp|udp|sctp)\b",
        score=0.85 + SCORE_BOOST
    )
    hostname_patterns = [
        Pattern(name="FQDN Pattern", regex=r"\b(?!Not-A\.Brand)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b", score=0.6 + SCORE_BOOST),
        Pattern(name="Certificate CN Pattern", regex=r"CN=([a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]|[a-f0-9]{8,16})\b", score=0.7 + SCORE_BOOST),
        Pattern(name="Standalone Hex Hostname Pattern", regex=r"(?<![:/])(?<![vV])\b(?!20\d{10})[a-f0-9]{12,16}\b(?!\.)", score=0.6 + SCORE_BOOST),
    ]

    hash_patterns = [
        Pattern(name="SHA256 Hash", regex=r"\b[0-9a-fA-F]{64}\b", score=0.8 + SCORE_BOOST),
        Pattern(name="MD5 Colon-Separated Hash", regex=r"\b([0-9a-fA-F]{2}:){15}[0-9a-fA-F]{2}\b", score=0.85 + SCORE_BOOST)
    ]

    cve_pattern = Pattern(
        name="CVE ID Pattern",
        regex=r"\bCVE-\d{4}-\d{4,}\b", 
        score=0.95 + SCORE_BOOST
    )

    cpe_pattern = Pattern(
        name="CPE String",
        regex=r"\bcpe:(?:/|2\.3:)[aho](?::[A-Za-z0-9\._\-~%*]+){2,}\b",
        score=0.9 + SCORE_BOOST
    )

    auth_token_patterns = [
        Pattern(name="Cookie/Session Assignment", regex=r"(?<=[=])[a-zA-Z0-9\-_]{32,128}\b", score=0.9 + SCORE_BOOST),
        Pattern(name="Generic Auth Token", regex=r"\b[a-zA-Z0-9]{32,128}\b", score=0.5 + SCORE_BOOST)
    ]

    password_pattern = Pattern(
        name="Contextual Password",
        regex=r"(?<=password=|passwd=|pwd=|secret=|api_key=|apikey=|access_key=|client_secret=)[^\s,;\"']+\b",
        score=0.95 + SCORE_BOOST
    )

    username_pattern = Pattern(
        name="Contextual Username",
        regex=r"(?<=user=|username=|uid=|login=|user_id=)[a-zA-Z0-9_.-]+\b",
        score=0.8 + SCORE_BOOST
    )

    email_pattern = Pattern(name="Email Pattern", regex=r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", score=1.0 + SCORE_BOOST)
    
    phone_pattern = Pattern(
        name="Phone Number Pattern",
        regex=r"\b(?:\+?\d{1,3}[-. ]?)?\(?\d{2,3}\)?[-. ]?\d{4,5}[-. ]?\d{4}\b",
        score=0.6 + SCORE_BOOST
    )

    cpf_pattern = Pattern(name="CPF Pattern", regex=r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", score=0.85 + SCORE_BOOST)

    cc_pattern = Pattern(name="Credit Card Pattern", regex=r"\b(?:\d{4}[- ]?){3}\d{4}\b", score=0.7 + SCORE_BOOST)

    uuid_pattern = Pattern(name="UUID Pattern", regex=r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", score=0.8 + SCORE_BOOST)
    cert_body_pattern = Pattern(name="Certificate Body", regex=r"\bMII[a-zA-Z0-9+/=\n]{100,}\b", score=0.8 + SCORE_BOOST)
    mac_pattern = Pattern(name="MAC Address", regex=r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b", score=0.8 + SCORE_BOOST)
    path_pattern = Pattern(name="User Home Path", regex=r"(?:/home/|/Users/|C:\\Users\\)([^/\\]+)", score=0.6 + SCORE_BOOST)
    
    pgp_pattern = Pattern(
        name="PGP Block",
        regex=r"-----BEGIN PGP (?:SIGNATURE|PUBLIC KEY BLOCK)-----.+?-----END PGP (?:SIGNATURE|PUBLIC KEY BLOCK)-----",
        score=0.95 + SCORE_BOOST
    )
    recognizers = []
    for lang in langs:
        recognizers.extend([
            PatternRecognizer(supported_entity="URL", patterns=[url_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[ip_pattern, ipv6_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="HOSTNAME", patterns=hostname_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="MAC_ADDRESS", patterns=[mac_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="FILE_PATH", patterns=[path_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="HASH", patterns=hash_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="AUTH_TOKEN", patterns=auth_token_patterns, supported_language=lang),
            PatternRecognizer(supported_entity="CVE_ID", patterns=[cve_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CPE_STRING", patterns=[cpe_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CERT_SERIAL", patterns=[serial_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CERT_BODY", patterns=[cert_body_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="PASSWORD", patterns=[password_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="USERNAME", patterns=[username_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[email_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[phone_pattern, cpf_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="CREDIT_CARD", patterns=[cc_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="UUID", patterns=[uuid_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="PGP_BLOCK", patterns=[pgp_pattern], supported_language=lang), # Added PGP_BLOCK
            PatternRecognizer(supported_entity="PORT", patterns=[port_pattern], supported_language=lang),
            PatternRecognizer(supported_entity="OID", patterns=[oid_pattern], supported_language=lang),
        ])
    return recognizers

class AnonymizationOrchestrator:
    """
    Secure and Optimized Anonymization Orchestrator.
    Combines Transformer models (via SpaCy) with high-performance Regex.
    """

    def __init__(self, 
                 lang: str, 
                 allow_list: List[str], 
                 entities_to_preserve: List[str], 
                 slug_length: int | None = None, 
                 strategy: str = "presidio", 
                 use_cache: bool = True, 
                 regex_priority: bool = False, 
                 max_cache_size: int = 10000,
                 analyzer_engine: Optional[BatchAnalyzerEngine] = None,
                 anonymizer_engine: Optional[AnonymizerEngine] = None):
        self.lang = lang
        self.allow_list = set(allow_list) 
        self.entities_to_preserve = set(entities_to_preserve)
        self.slug_length = slug_length
        self.strategy = strategy
        self.use_cache = use_cache
        self.regex_priority = regex_priority
        self.total_entities_processed = 0
        self.entity_counts: Dict[str, int] = {}
        self.max_cache_size = max_cache_size
        self.cache: OrderedDict[str, str] = OrderedDict()
        
        if analyzer_engine and anonymizer_engine:
            self.analyzer_engine = analyzer_engine
            self.anonymizer_engine = anonymizer_engine
        else:
            self.analyzer_engine, self.anonymizer_engine = self._setup_engines()
        
        self.compiled_patterns = []
        custom_recognizers = load_custom_recognizers([self.lang], regex_priority=self.regex_priority)
        
        for recognizer in custom_recognizers:
            entity_type = recognizer.supported_entities[0] 
            if entity_type in self.entities_to_preserve:
                continue
            for pattern in recognizer.patterns:
                try:
                    self.compiled_patterns.append({
                        "label": entity_type,
                        "regex": re.compile(pattern.regex, flags=re.DOTALL | re.IGNORECASE),
                        "score": pattern.score
                    })
                except re.error:
                    pass

    def _get_from_cache(self, key: str) -> Optional[str]:
        """Retrieves an item from the cache, moving it to the front (most recently used)."""
        if not self.use_cache:
            return None
        if key in self.cache:
            value = self.cache.pop(key) # Remove and re-insert to mark as recently used
            self.cache[key] = value
            return value
        return None

    def _add_to_cache(self, key: str, value: str):
        """Adds an item to the cache, implementing LRU eviction if size limit is exceeded."""
        if not self.use_cache:
            return
        if key in self.cache:
            self.cache.pop(key) # Update value and mark as recently used
        elif len(self.cache) >= self.max_cache_size:
            self.cache.popitem(last=False) # Remove LRU item
        self.cache[key] = value

    def _setup_engines(self) -> tuple[BatchAnalyzerEngine, AnonymizerEngine]:
        """Initializes the Presidio engines, keeping the XLM-Roberta model and security settings."""
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
        core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=list(supported_langs))
        
        for recognizer in load_custom_recognizers(langs=core_analyzer.supported_languages, regex_priority=self.regex_priority):
            core_analyzer.registry.add_recognizer(recognizer)
        
        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)
        
        return batch_analyzer, anonymizer

    def anonymize_text(self, text: str, operator_params: Optional[Dict] = None, forced_entity_type: Optional[Union[str, List[str]]] = None) -> str:
        if not isinstance(text, str) or not text.strip():
            return text
        return self.anonymize_texts([text], operator_params=operator_params, forced_entity_type=forced_entity_type)[0]

    def _get_core_entities(self) -> List[str]:
        """Returns a curated list of entities supported by our core recognizers (NLP + Custom Regex)."""
        core_entities = set(ENTITY_MAPPING.values())
        for recognizer in load_custom_recognizers(langs=[self.lang]):
            core_entities.update(recognizer.supported_entities)
        return list(core_entities)

    def anonymize_texts(self, texts: List[str], operator_params: Optional[Dict] = None, forced_entity_type: Optional[Union[str, List[str]]] = None) -> List[str]:
        """
        Anonymizes a list of texts based on the configured strategy.

        This method dispatches to the appropriate internal method ('presidio', 'fast', 'balanced', etc.)
        and includes a fallback mechanism to ensure data integrity.
        """
        if isinstance(forced_entity_type, list):
            results = self._anonymize_texts_pick_one(texts, forced_entity_type, operator_params)
        elif isinstance(forced_entity_type, str):
            results = self._anonymize_texts_forced_type(texts, forced_entity_type, operator_params)
        elif self.strategy == "fast":
            results = self._anonymize_texts_fast_path(texts, operator_params)
        elif self.strategy == "balanced":
            core_entities = self._get_core_entities()
            entities_to_anonymize = [e for e in core_entities if e not in self.entities_to_preserve]
            results = self._anonymize_texts_presidio(texts, operator_params, entities=entities_to_anonymize)
        else: # "presidio" strategy
            entities_to_anonymize = self._get_entities_to_anonymize()
            results = self._anonymize_texts_presidio(texts, operator_params, entities=entities_to_anonymize)

        # --- FALLBACK ARCHITECTURE ---
        if len(results) != len(texts):
            logging.warning(
                "Batch integrity failure detected (Input: %d vs Output: %d). "
                "Triggering Safe Fallback Mechanism.",
                len(texts), len(results)
            )
            return self._safe_fallback_processing(texts, operator_params, forced_entity_type)
        
        return results

    def _safe_fallback_processing(self, texts: List[str], operator_params: Optional[Dict], forced_entity_type: Optional[Union[str, List[str]]]) -> List[str]:
        """
        Fallback Method: Processes item by item to ensure atomicity and alignment.
        Isolates failures: If one item fails, only that item is affected.
        """
        fallback_results = []
        for text in texts:
            try:
                single_result_list = []
                
                # Re-use existing dispatch logic to keep it DRY
                if isinstance(forced_entity_type, list):
                    single_result_list = self._anonymize_texts_pick_one([text], forced_entity_type, operator_params)
                elif isinstance(forced_entity_type, str):
                    single_result_list = self._anonymize_texts_forced_type([text], forced_entity_type, operator_params)
                elif self.strategy == "fast":
                    single_result_list = self._anonymize_texts_fast_path([text], operator_params)
                elif self.strategy == "balanced":
                    core_entities = self._get_core_entities()
                    entities_to_anonymize = [e for e in core_entities if e not in self.entities_to_preserve]
                    single_result_list = self._anonymize_texts_presidio([text], operator_params, entities=entities_to_anonymize)
                else: # "presidio"
                    if not text or not str(text).strip():
                        single_result_list = [text]
                    else:
                        entities_to_anonymize = self._get_entities_to_anonymize()
                        single_result_list = self._anonymize_texts_presidio([text], operator_params, entities=entities_to_anonymize)

                if not single_result_list:
                    fallback_results.append(text) 
                else:
                    fallback_results.append(single_result_list[0])

            except Exception as e:
                logging.error(f"Fallback failed for a specific item: {str(e)[:100]}...", exc_info=True)
                fallback_results.append(text)
        
        return fallback_results

    def _anonymize_texts_pick_one(self, texts: List[str], entity_types: List[str], operator_params: Optional[Dict] = None) -> List[str]:
        anonymized_list = []
        if operator_params is None: operator_params = {}
        
        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            texts, language=self.lang, entities=entity_types
        )

        for text, analyzer_results in zip(texts, analyzer_results_iterator):
            if not analyzer_results:
                anonymized_list.append(text)
                continue
            
            best_result: RecognizerResult = max(analyzer_results, key=lambda r: r.score)
            anonymized_text = self._anonymize_texts_forced_type([text], best_result.entity_type, operator_params)[0]
            anonymized_list.append(anonymized_text)
            
        return anonymized_list

    def _anonymize_texts_forced_type(self, texts: List[str], entity_type: str, operator_params: Optional[Dict] = None) -> List[str]:
        anonymized_list = []
        if operator_params is None: operator_params = {}
        entity_collector = operator_params.get("entity_collector")

        for text in texts:
            if not isinstance(text, str) or not text.strip():
                anonymized_list.append(text)
                continue

            # This path treats the entire text as a single entity, so we count it here.
            self.total_entities_processed += 1
            self.entity_counts[entity_type] = self.entity_counts.get(entity_type, 0) + 1

            clean_text = " ".join(text.split()).strip()
            
            cache_key = f"forced_{entity_type}_{clean_text}"
            cached_value = self._get_from_cache(cache_key) # Use helper
            if cached_value:
                anonymized_list.append(cached_value)
                continue

            if not SECRET_KEY: raise ValueError("SECRET_KEY is not set.")
            full_hash = hmac.new(SECRET_KEY.encode(), clean_text.encode(), hashlib.sha256).hexdigest()
            display_hash = full_hash[:self.slug_length] if self.slug_length is not None else full_hash

            if entity_collector is not None:
                entity_collector.append((entity_type, clean_text, display_hash, full_hash))
            
            anonymized_text = f"[{entity_type}_{display_hash}]"
            self._add_to_cache(cache_key, anonymized_text) # Use helper
            anonymized_list.append(anonymized_text)
        return anonymized_list

    def _extract_entities_from_doc(self, doc, original_doc_text: str) -> List[Dict]:
        """Extracts entities from a spaCy Doc object and custom regex patterns."""
        detected_entities = []

        # Extract entities from spaCy Doc
        for ent in doc.ents:
            normalized_label = ENTITY_MAPPING.get(ent.label_, ent.label_)
            if normalized_label not in self.entities_to_preserve:
                detected_entities.append({
                    "start": ent.start_char, "end": ent.end_char, "label": normalized_label,
                    "text": ent.text, "score": 1.0
                })

        # Extract entities from custom regex patterns
        for pat in self.compiled_patterns:
            for match in pat["regex"].finditer(original_doc_text):
                match_text = match.group()
                if match_text not in self.allow_list and pat["label"] not in self.entities_to_preserve:
                    detected_entities.append({
                        "start": match.start(), "end": match.end(), "label": pat["label"],
                        "text": match_text, "score": pat["score"]
                    })
        return detected_entities

    def _merge_overlapping_entities(self, detected_entities: List[Dict]) -> List[Dict]:
        """Sorts and merges overlapping entities based on score and length."""
        # Sort by start position, then by inverse score (higher score first), then by inverse length (longer first)
        detected_entities.sort(key=lambda x: (x["start"], -x["score"], -(x["end"] - x["start"])))
        
        merged_entities = []
        last_end = -1
        for ent in detected_entities:
            if ent["start"] >= last_end:
                merged_entities.append(ent)
                last_end = ent["end"]
        return merged_entities

    def _generate_anonymized_text(self, original_doc_text: str, merged_entities: List[Dict], entity_collector: Optional[List]) -> str:
        """Generates the anonymized text based on merged entities."""
        new_text_parts = []
        current_idx = 0
        for ent in merged_entities:
            self.total_entities_processed += 1
            self.entity_counts[ent["label"]] = self.entity_counts.get(ent["label"], 0) + 1
            new_text_parts.append(original_doc_text[current_idx:ent["start"]])
            clean_text = " ".join(ent["text"].split()).strip()
            
            if not SECRET_KEY: raise ValueError("SECRET_KEY is not set.")
            full_hash = hmac.new(SECRET_KEY.encode(), clean_text.encode(), hashlib.sha256).hexdigest()
            display_hash = full_hash[:self.slug_length] if self.slug_length else full_hash

            if entity_collector is not None:
                entity_collector.append((ent["label"], clean_text, display_hash, full_hash))
            new_text_parts.append(f"[{ent['label']}_{display_hash}]")
            current_idx = ent["end"]
        
        new_text_parts.append(original_doc_text[current_idx:])
        return "".join(new_text_parts)


    def _anonymize_texts_fast_path(self, texts: List[str], operator_params: Optional[Dict] = None) -> List[str]:
        if not texts: return []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        
        # This path no longer deduplicates. It processes all texts to preserve context.
        # The cache is still checked on a per-item basis.
        
        anonymized_results = []
        texts_to_process_in_batch = []
        indices_map = [] # To map batch results back to original positions

        for i, text in enumerate(original_texts):
            if not text:
                anonymized_results.append("")
                continue

            cached_value = self._get_from_cache(text)
            if cached_value:
                anonymized_results.append(cached_value)
            else:
                anonymized_results.append(None) # Placeholder for now
                texts_to_process_in_batch.append(text)
                indices_map.append(i)

        if not texts_to_process_in_batch:
            return [res if res is not None else "" for res in anonymized_results]

        if operator_params is None: operator_params = {}
        entity_collector = operator_params.get("entity_collector")
        nlp_engine = self.analyzer_engine.analyzer_engine.nlp_engine
        nlp_model = nlp_engine.nlp[self.lang] 
        docs = nlp_model.pipe(texts_to_process_in_batch, batch_size=500)

        processed_texts = []
        for doc in docs:
            original_doc_text = doc.text
            
            detected_entities = self._extract_entities_from_doc(doc, original_doc_text)
            merged_entities = self._merge_overlapping_entities(detected_entities)
            anonymized_text = self._generate_anonymized_text(original_doc_text, merged_entities, entity_collector)

            self._add_to_cache(original_doc_text, anonymized_text)
            processed_texts.append(anonymized_text)
        
        # Populate the final results using the processed texts and the index map
        for i, anonymized_text in enumerate(processed_texts):
            original_index = indices_map[i]
            anonymized_results[original_index] = anonymized_text

        return [res if res is not None else "" for res in anonymized_results]

    def _anonymize_texts_presidio(self, texts: List[str], operator_params: Optional[Dict] = None, entities: Optional[List[str]] = None) -> List[str]:
        if not texts: return []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        
        final_anonymized_list = []

        # If no specific entities are passed, use the default logic for the "presidio" strategy.
        entities_to_use = entities if entities is not None else self._get_entities_to_anonymize()
        
        if operator_params is None: operator_params = {}
        operator_params["total_entities_counter"] = self
        operator_params["entity_counts"] = self.entity_counts
        operator_params["slug_length"] = self.slug_length
        
        logging.debug(f"[_anonymize_texts_presidio] Input texts count: {len(original_texts)}")

        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            original_texts, language=self.lang,
            entities=entities_to_use, score_threshold=0.6,
            allow_list=self.allow_list
        )
        
        analyzer_results_list = list(analyzer_results_iterator)
        logging.debug(f"[_anonymize_texts_presidio] Analyzer results count: {len(analyzer_results_list)}")

        if len(analyzer_results_list) != len(original_texts):
            logging.error(f"[_anonymize_texts_presidio] Mismatch between original_texts and analyzer_results_list! Input: {len(original_texts)}, Analyzer Results: {len(analyzer_results_list)}. This will lead to batch integrity failure.")

        for text, analyzer_results in zip(original_texts, analyzer_results_list):
            logging.debug(f"[_anonymize_texts_presidio] Processing text: '{text}'")
            logging.debug(f"[_anonymize_texts_presidio]   Analyzer Results for text: {analyzer_results}")

            cached_value = self._get_from_cache(text)
            if cached_value:
                final_anonymized_list.append(cached_value)
                logging.debug(f"[_anonymize_texts_presidio]   Cache hit for '{text}'. Anonymized: '{cached_value}'")
                continue

            for res in analyzer_results:
                if res.entity_type not in self.entities_to_preserve:
                    self.total_entities_processed += 1
                    self.entity_counts[res.entity_type] = self.entity_counts.get(res.entity_type, 0) + 1

            anonymizer_result = self.anonymizer_engine.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators={"DEFAULT": OperatorConfig("custom_slug", operator_params)},
            )
            
            anonymized_text = anonymizer_result.text
            self._add_to_cache(text, anonymized_text)
            final_anonymized_list.append(anonymized_text)
            logging.debug(f"[_anonymize_texts_presidio]   Final anonymized text: '{anonymized_text}'")
        
        return final_anonymized_list

    def _get_entities_to_anonymize(self) -> List[str]:
        all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
        return [ent for ent in all_entities if ent not in self.entities_to_preserve]

    def detect_entities(self, texts: List[str]) -> List[dict]:
        if not texts: return []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        unique_texts_to_process = sorted(list(set(t for t in original_texts if t)))

        if not unique_texts_to_process: return []

        nlp_engine = self.analyzer_engine.analyzer_engine.nlp_engine
        nlp_model = nlp_engine.nlp[self.lang]
        docs = nlp_model.pipe(unique_texts_to_process, batch_size=500)
        results = []

        for doc in docs:
            original_doc_text = doc.text
            detected_entities = []

            for ent in doc.ents:
                normalized_label = ENTITY_MAPPING.get(ent.label_, ent.label_)
                detected_entities.append({
                    "start": ent.start_char, "end": ent.end_char,
                    "label": normalized_label, "score": 1.0
                })

            for pat in self.compiled_patterns:
                for match in pat["regex"].finditer(original_doc_text):
                    detected_entities.append({
                        "start": match.start(), "end": match.end(),
                        "label": pat["label"], "score": pat["score"]
                    })

            detected_entities.sort(key=lambda x: (x["start"], -x["score"], -(x["end"] - x["start"])))
            
            merged_entities = []
            last_end = -1
            for ent in detected_entities:
                if ent["start"] >= last_end:
                    if ent["label"] in self.entities_to_preserve: continue
                    if original_doc_text[ent['start']:ent['end']] in self.allow_list: continue
                    merged_entities.append(ent)
                    last_end = ent["end"]

            if merged_entities:
                labels = [[ent['start'], ent['end'], ent['label']] for ent in merged_entities]
                results.append({"text": original_doc_text, "label": labels})
        
        return results
