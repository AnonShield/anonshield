# src/anon/engine.py

import hashlib
import hmac
import re
from typing import Dict, List, Optional, Union, Tuple
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
    SpacyNlpEngine,
    TransformersNlpEngine,
)
from presidio_anonymizer import AnonymizerEngine, OperatorConfig  # type: ignore
from presidio_anonymizer.operators import Operator, OperatorType  # type: ignore

from .config import (
    ENTITY_MAPPING,
    SECRET_KEY,
    TRANSFORMER_MODEL,
    ProcessingLimits,
)
from .database import DatabaseContext
from .cache_manager import CacheManager
from .hash_generator import HashGenerator
from .strategies import strategy_factory
from .entity_detector import EntityDetector
from .core.protocols import EntityStorage, CacheStrategy, HashingStrategy, AnonymizationStrategy


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
        
        
        params = params or {}
        entity_type = params.get("entity_type", "UNKNOWN")
        logging.debug(f"Anonymizing text '{clean_text}' with entity type '{entity_type}'.")

        hash_generator = params.get("hash_generator")
        if not hash_generator:
            raise ValueError("HashGenerator instance not provided in operator params.")

        # Try to get the slug length from our custom parameter first.
        slug_length = params.get("custom_slug_length")
        logging.debug(f"CustomSlugAnonymizer.operate, received slug_length = {slug_length}")
        
        display_hash, full_hash = hash_generator.generate_slug(clean_text, slug_length)

        if "entity_collector" in params:
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
        Pattern(name="FQDN Pattern", regex=r"\b(?<!@)(?!Not-A\.Brand)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b", score=0.6 + SCORE_BOOST),
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
        regex=r"(?:password=|passwd=|pwd=|secret=|api_key=|apikey=|access_key=|client_secret=)([^\",;']+)\b",
        score=0.95 + SCORE_BOOST
    )

    username_pattern = Pattern(
        name="Contextual Username",
        regex=r"(?:user=|username=|uid=|login=|user_id=)([a-zA-Z0-9_.-]+)\b",
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
    Coordinates the anonymization process by selecting and executing a strategy.
    This class is responsible for high-level workflow, dependency injection,
    and fallback mechanisms, but delegates the core logic to strategy objects.
    """

    def __init__(self,
                 lang: str,
                 db_context: Optional[EntityStorage],
                 allow_list: List[str],
                 entities_to_preserve: List[str],
                 slug_length: Optional[int] = None,
                 strategy_name: str = "presidio",
                 regex_priority: bool = False,
                 analyzer_engine: Optional[BatchAnalyzerEngine] = None,
                 anonymizer_engine: Optional[AnonymizerEngine] = None,
                 nlp_batch_size: int = 500,
                 cache_manager: Optional[CacheStrategy] = None,
                 hash_generator: Optional[HashingStrategy] = None,
                 entity_detector: Optional[EntityDetector] = None,
                 ner_data_generation: bool = False):

        self.lang = lang
        self.db_context = db_context
        self.allow_list = set(allow_list)
        self.entities_to_preserve = set(entities_to_preserve)
        self.slug_length = slug_length
        self.nlp_batch_size = nlp_batch_size
        self.regex_priority = regex_priority
        self.ner_data_generation = ner_data_generation

        self.total_entities_processed = 0
        self.entity_counts: Dict[str, int] = {}

        # --- Dependency Injection and Engine Setup ---
        self.cache_manager = cache_manager or CacheManager(use_cache=False, max_cache_size=0)
        self.hash_generator = hash_generator or HashGenerator()

        if analyzer_engine and anonymizer_engine:
            self.analyzer_engine = analyzer_engine
            self.anonymizer_engine = anonymizer_engine
        else:
            self.analyzer_engine, self.anonymizer_engine = self._setup_engines()

        # If entity_detector was not provided, create a default one.
        if entity_detector:
            self.entity_detector = entity_detector
        else:
            custom_recognizers = load_custom_recognizers([self.lang], regex_priority=regex_priority)
            compiled_patterns = []
            for recognizer in custom_recognizers:
                entity_type = recognizer.supported_entities[0]
                if entity_type in self.entities_to_preserve:
                    continue
                for pattern in recognizer.patterns:
                    try:
                        compiled_patterns.append({
                            "label": entity_type,
                            "regex": re.compile(pattern.regex, flags=re.DOTALL | re.IGNORECASE),
                            "score": pattern.score
                        })
                    except re.error as e:
                        logging.warning(f"Invalid regex pattern skipped: {pattern.regex} - {e}")
            self.entity_detector = EntityDetector(
                compiled_patterns=compiled_patterns,
                entities_to_preserve=self.entities_to_preserve,
                allow_list=self.allow_list
            )

        # --- Strategy Factory ---
        # The factory is now called from the orchestrator, which injects dependencies into the strategy.
        self.anonymization_strategy = strategy_factory(
            strategy_name=strategy_name,
            analyzer_engine=self.analyzer_engine,
            anonymizer_engine=self.anonymizer_engine,
            entity_detector=self.entity_detector,
            hash_generator=self.hash_generator,
            cache_manager=self.cache_manager,
            lang=self.lang,
            entities_to_preserve=self.entities_to_preserve,
            allow_list=self.allow_list,
            nlp_batch_size=self.nlp_batch_size
        )
        logging.info(f"Anonymization strategy '{strategy_name}' initialized.")


    def _setup_engines(self) -> tuple[BatchAnalyzerEngine, AnonymizerEngine]:
        """Initializes the Presidio engines, switching between models based on `ner_data_generation`."""
        logging.info("Setting up Presidio analyzer and anonymizer engines.")
        lang_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
        
        # Determine the effective language for model loading, prioritizing self.lang
        effective_lang = self.lang if self.lang in lang_model_map else 'en'
        
        spacy_model_name = lang_model_map.get(effective_lang, f"{effective_lang}_core_news_lg")

        if self.ner_data_generation:
            logging.info(f"NER data generation mode: Initializing SpacyNlpEngine for '{effective_lang}'.")
            nlp_engine = SpacyNlpEngine(models=[{"lang_code": effective_lang, "model_name": spacy_model_name}])
            core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=[effective_lang])
        else:
            logging.info(f"Anonymization mode: Initializing TransformersNlpEngine for '{effective_lang}'.")
            trf_model_config = [
                {"lang_code": effective_lang, "model_name": {"spacy": spacy_model_name, "transformers": TRANSFORMER_MODEL}}
            ]
            ner_config = NerModelConfiguration(
                model_to_presidio_entity_mapping=ENTITY_MAPPING, 
                aggregation_strategy="max", 
                labels_to_ignore=["O"]
            )
            nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_config)
            core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=[effective_lang])
        
        # Load custom recognizers only for the effective_lang
        for recognizer in load_custom_recognizers(langs=[effective_lang], regex_priority=self.regex_priority):
            core_analyzer.registry.add_recognizer(recognizer)
        
        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)
        
        logging.info("Presidio engines setup complete.")
        return batch_analyzer, anonymizer

    def anonymize_text(self, text: str, forced_entity_type: Optional[Union[str, List[str]]] = None) -> str:
        if not isinstance(text, str) or not text.strip():
            return text
        anonymized_texts, _ = self.anonymize_texts([text], forced_entity_type=forced_entity_type)
        return anonymized_texts[0]

    def anonymize_texts(self, texts: List[str], forced_entity_type: Optional[Union[str, List[str]]] = None) -> List[str]:
        """
        Anonymizes a list of texts and saves the generated entity mappings to the database.
        This method dispatches to the appropriate internal method, collects all generated
        entities, and handles micro-batching persistence and entity counting.
        """
        all_collected_entities: List[Tuple] = [] # Orchestrator's master collector for micro-batching
        operator_params = {
            "hash_generator": self.hash_generator,
            "custom_slug_length": self.slug_length,
            # entity_collector will be passed to CustomSlugAnonymizer via operator_params in strategies
        }

        logging.debug(f"Anonymizing {len(texts)} texts using strategy: '{self.anonymization_strategy.__class__.__name__}'. Forced entity type: '{forced_entity_type}'")
        
        anonymized_results: List[str]
        collected_from_current_run: List[Tuple] = []

        if isinstance(forced_entity_type, list):
            logging.debug("Dispatching to _anonymize_texts_pick_one strategy.")
            anonymized_results, collected_from_current_run = self._anonymize_texts_pick_one(texts, forced_entity_type, operator_params)
        elif isinstance(forced_entity_type, str):
            logging.debug("Dispatching to _anonymize_texts_forced_type strategy.")
            anonymized_results, collected_from_current_run = self._anonymize_texts_forced_type(texts, forced_entity_type, operator_params)
        else:
            anonymized_results, collected_from_current_run = self.anonymization_strategy.anonymize(texts, operator_params)

        all_collected_entities.extend(collected_from_current_run)
        
        # Implement micro-batching: save entities if the collector grows large
        if self.db_context and len(all_collected_entities) >= ProcessingLimits.MICRO_BATCH_SAVE_SIZE:
            self._save_and_clear_entities(all_collected_entities)

        # --- FALLBACK ARCHITECTURE ---
        if len(anonymized_results) != len(texts):
            logging.warning(
                "Batch integrity failure detected (Input: %d vs Output: %d). "
                "Triggering Safe Fallback Mechanism.",
                len(texts), len(anonymized_results)
            )
            # The fallback will manage its own entity collection and saving.
            anonymized_results, collected_from_fallback = self._safe_fallback_processing(texts, operator_params, forced_entity_type)
            all_collected_entities.extend(collected_from_fallback) # Add any entities collected during fallback

        # --- DATABASE PERSISTENCE (Final Flush) ---
        # Any remaining entities from fallback or prior micro-batches will be flushed here.
        self._save_and_clear_entities(all_collected_entities) 

        return anonymized_results

    def _safe_fallback_processing(self, texts: List[str], operator_params: Optional[Dict], forced_entity_type: Optional[Union[str, List[str]]]) -> Tuple[List[str], List[Tuple]]:
        """
        Fallback Method: Processes item by item to ensure atomicity and alignment,
        with a circuit breaker to prevent runaway failures.
        """
        fallback_results = []
        collected_entities_fallback: List[Tuple] = []
        failure_count = 0
        # Circuit breaker activates if a defined percentage of the batch fails.
        failure_threshold = max(
            ProcessingLimits.CIRCUIT_BREAKER_MIN_FAILURES,
            int(len(texts) * ProcessingLimits.CIRCUIT_BREAKER_FAILURE_RATE)
        )

        for text in texts:
            single_item_collected_entities: List[Tuple] = []
            single_item_operator_params = operator_params.copy() if operator_params else {}
            single_item_operator_params["entity_collector"] = single_item_collected_entities # Pass collector to the operator
            
            single_anonymized_list = []
            
            try:
                # Re-use existing dispatch logic to keep it DRY
                if isinstance(forced_entity_type, list):
                    single_anonymized_list, collected_for_item = self._anonymize_texts_pick_one([text], forced_entity_type, single_item_operator_params)
                elif isinstance(forced_entity_type, str):
                    single_anonymized_list, collected_for_item = self._anonymize_texts_forced_type([text], forced_entity_type, single_item_operator_params)
                else:
                    # Use the strategy for the single text
                    single_anonymized_list, collected_for_item = self.anonymization_strategy.anonymize([text], single_item_operator_params)

                if collected_for_item:
                    collected_entities_fallback.extend(collected_for_item)
                    # Micro-batch save for fallback items
                    if self.db_context and len(collected_entities_fallback) >= ProcessingLimits.MICRO_BATCH_SAVE_SIZE:
                        self._save_and_clear_entities(collected_entities_fallback)

                if not single_anonymized_list:
                    fallback_results.append(text) 
                else:
                    fallback_results.append(single_anonymized_list[0])

            except Exception as e:
                logging.error(f"Fallback failed for a specific item: {str(e)[:100]}...", exc_info=True)
                fallback_results.append(text)
                failure_count += 1
                if failure_count > failure_threshold:
                    logging.critical(
                        f"Circuit breaker tripped! More than {failure_threshold} items failed in fallback processing. "
                        "Aborting processing for this batch to prevent further errors."
                    )
                    # Re-raise the last exception to halt processing of this file
                    raise e
        
        return fallback_results, collected_entities_fallback


    def _anonymize_texts_pick_one(self, texts: List[str], entity_types: List[str], operator_params: Optional[Dict] = None) -> Tuple[List[str], List[Tuple]]:
        anonymized_list = []
        collected_entities_from_pick_one: List[Tuple] = []
        if operator_params is None: operator_params = {}
        
        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            texts, language=self.lang, entities=entity_types
        )

        for text, analyzer_results in zip(texts, analyzer_results_iterator):
            if not analyzer_results:
                anonymized_list.append(text)
                continue
            
            best_result: RecognizerResult = max(analyzer_results, key=lambda r: r.score)
            anonymized_text_list, collected_from_forced = self._anonymize_texts_forced_type([text], best_result.entity_type, operator_params)
            anonymized_list.append(anonymized_text_list[0])
            collected_entities_from_pick_one.extend(collected_from_forced)
            
        return anonymized_list, collected_entities_from_pick_one

    def _anonymize_texts_forced_type(self, texts: List[str], entity_type: str, operator_params: Optional[Dict] = None) -> Tuple[List[str], List[Tuple]]:
        anonymized_list = []
        collected_entities_from_forced: List[Tuple] = []
        if operator_params is None: operator_params = {}
        
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                anonymized_list.append(text)
                continue

            clean_text = " ".join(text.split()).strip()
            
            cache_key = f"forced_{entity_type}_{clean_text}"
            cached_value = self.cache_manager.get(cache_key) # Use CacheManager
            if cached_value:
                anonymized_list.append(cached_value)
                # No entities collected if from cache
                continue

            display_hash, full_hash = self.hash_generator.generate_slug(clean_text, self.slug_length)

            collected_entities_from_forced.append((entity_type, clean_text, display_hash, full_hash))
            
            anonymized_text = f"[{entity_type}_{display_hash}]"
            self.cache_manager.add(cache_key, anonymized_text) # Use CacheManager
            anonymized_list.append(anonymized_text)
        return anonymized_list, collected_entities_from_forced

    def detect_entities(self, texts: List[str]) -> List[dict]:
        if not texts:
            return []

        logging.debug(f"Detecting entities for {len(texts)} texts using analyzer_engine.")
        
        results = []
        
        # Get all supported entities, but filter out those the user wants to preserve.
        if self.analyzer_engine and self.analyzer_engine.analyzer_engine:
            all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
            entities_to_analyze = [e for e in all_entities if e not in self.entities_to_preserve]
        else:
            entities_to_analyze = []

        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            texts,
            language=self.lang,
            entities=entities_to_analyze,
            allow_list=self.allow_list,
            score_threshold=0.1
        )

        for i, analyzer_results in enumerate(analyzer_results_iterator):
            text = texts[i]
            # Even if there are no PIIs, we might want to return the text.
            # The current NER implementation expects a "label" key.
            # We will only append if entities are found.
            if analyzer_results:
                # Sort by start offset to ensure labels are ordered
                sorted_results = sorted(analyzer_results, key=lambda r: r.start)
                labels = [[res.start, res.end, res.entity_type] for res in sorted_results]
                results.append({"text": text, "label": labels})
        
        return results

    def _save_and_clear_entities(self, entities: List[Tuple]):
        """Saves a batch of entities to the database and clears the list."""
        if self.db_context and entities:
            self.db_context.save_entities(entities)
            self._increment_entity_counters_for_batch(entities)
            entities.clear() # Clear the list to free memory

    def _increment_entity_counters_for_batch(self, entities: List[Tuple]):
        """Increments internal counters for a batch of entities."""
        for entity in entities:
            entity_type = entity[0] # entity_type is the first element of the tuple
            self.total_entities_processed += 1
            self.entity_counts[entity_type] = self.entity_counts.get(entity_type, 0) + 1