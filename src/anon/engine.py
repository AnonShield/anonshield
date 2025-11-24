# src/anon/engine.py

import hashlib
import hmac
import re
from typing import Dict, List, Optional, Union
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
from .database import DatabaseContext
from .cache_manager import CacheManager
from .hash_generator import HashGenerator
from .strategies import strategy_factory
from .entity_detector import EntityDetector


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

        slug_length = params.get("slug_length")
        
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
        regex=r"(?:password=|passwd=|pwd=|secret=|api_key=|apikey=|access_key=|client_secret=)([^\s,;\"']+)\b",
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
    Secure and Optimized Anonymization Orchestrator.
    Combines Transformer models (via SpaCy) with high-performance Regex.
    """

    def __init__(self, 
                 lang: str, 
                 db_context: Optional[DatabaseContext],
                 allow_list: List[str], 
                 entities_to_preserve: List[str], 
                 slug_length: int | None = None, 
                 strategy: str = "presidio", 
                 use_cache: bool = True, 
                 regex_priority: bool = False, 
                 max_cache_size: int = 10000,
                 analyzer_engine: Optional[BatchAnalyzerEngine] = None,
                 anonymizer_engine: Optional[AnonymizerEngine] = None,
                 nlp_batch_size: int = 500):
        self.lang = lang
        self.db_context = db_context
        self.allow_list = set(allow_list) 
        self.entities_to_preserve = set(entities_to_preserve)
        self.slug_length = slug_length
        self.strategy_name = strategy
        self.use_cache = use_cache # Keep for passing to CacheManager
        self.regex_priority = regex_priority
        self.nlp_batch_size = nlp_batch_size
        self.total_entities_processed = 0
        self.entity_counts: Dict[str, int] = {}
        
        self.cache_manager = CacheManager(use_cache, max_cache_size)
        self.hash_generator = HashGenerator()
        
        logging.debug(f"AnonymizationOrchestrator initialized with: lang='{lang}', strategy='{strategy}', use_cache={use_cache}, max_cache_size={max_cache_size}, regex_priority={regex_priority}, slug_length={slug_length}.")
        logging.debug(f"Allow list: {self.allow_list}, Entities to preserve: {self.entities_to_preserve}")

        if analyzer_engine and anonymizer_engine:
            self.analyzer_engine = analyzer_engine
            self.anonymizer_engine = anonymizer_engine
            logging.debug("Using pre-provided analyzer and anonymizer engines.")
        else:
            self.analyzer_engine, self.anonymizer_engine = self._setup_engines()
        
        compiled_patterns = []
        custom_recognizers = load_custom_recognizers([self.lang], regex_priority=self.regex_priority)
        
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
                except re.error:
                    logging.warning(f"Invalid regex pattern skipped: {pattern.regex}")
        logging.debug(f"Loaded {len(custom_recognizers)} custom recognizers and compiled {len(compiled_patterns)} regex patterns.")
        
        self.entity_detector = EntityDetector(
            compiled_patterns=compiled_patterns,
            entities_to_preserve=self.entities_to_preserve,
            allow_list=self.allow_list
        )
        self.anonymization_strategy = strategy_factory(strategy, self)


    def _setup_engines(self) -> tuple[BatchAnalyzerEngine, AnonymizerEngine]:
        """Initializes the Presidio engines, keeping the XLM-Roberta model and security settings."""
        logging.info("Setting up Presidio analyzer and anonymizer engines.")
        lang_model_map = {"pt": "pt_core_news_lg", "en": "en_core_web_lg"}
        supported_langs = set(["en", self.lang])

        trf_model_config = []
        for lang_code in supported_langs:
            spacy_model_name = lang_model_map.get(lang_code, f"{lang_code}_core_news_lg")
            trf_model_config.append(
                {"lang_code": lang_code, "model_name": {"spacy": spacy_model_name, "transformers": TRANSFORMER_MODEL}}
            )
        logging.debug(f"Transformer model config: {trf_model_config}")

        ner_config = NerModelConfiguration(
            model_to_presidio_entity_mapping=ENTITY_MAPPING, 
            aggregation_strategy="max", 
            labels_to_ignore=["O"]
        )
        logging.debug(f"NER model configuration: {ner_config}")
        
        nlp_engine = TransformersNlpEngine(models=trf_model_config, ner_model_configuration=ner_config)
        core_analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=list(supported_langs))
        
        for recognizer in load_custom_recognizers(langs=core_analyzer.supported_languages, regex_priority=self.regex_priority):
            core_analyzer.registry.add_recognizer(recognizer)
        
        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=core_analyzer)
        anonymizer = AnonymizerEngine()
        anonymizer.add_anonymizer(CustomSlugAnonymizer)
        
        logging.info("Presidio engines setup complete.")
        return batch_analyzer, anonymizer

    def anonymize_text(self, text: str, forced_entity_type: Optional[Union[str, List[str]]] = None) -> str:
        if not isinstance(text, str) or not text.strip():
            return text
        return self.anonymize_texts([text], forced_entity_type=forced_entity_type)[0]

    def _get_core_entities(self) -> List[str]:
        """Returns a curated list of entities supported by our core recognizers (NLP + Custom Regex)."""
        core_entities = set(ENTITY_MAPPING.values())
        for recognizer in load_custom_recognizers(langs=[self.lang]):
            core_entities.update(recognizer.supported_entities)
        return list(core_entities)

    def anonymize_texts(self, texts: List[str], forced_entity_type: Optional[Union[str, List[str]]] = None) -> List[str]:
        """
        Anonymizes a list of texts and saves the generated entity mappings to the database.

        This method dispatches to the appropriate internal method, collects all generated
        entities, and then uses the injected DatabaseContext to persist them.
        """
        entity_collector: List = []
        operator_params = {
            "entity_collector": entity_collector,
            "hash_generator": self.hash_generator,
            "slug_length": self.slug_length
        }

        logging.debug(f"Anonymizing {len(texts)} texts using strategy: '{self.strategy_name}'. Forced entity type: '{forced_entity_type}'")
        
        if isinstance(forced_entity_type, list):
            logging.debug("Dispatching to _anonymize_texts_pick_one strategy.")
            results = self._anonymize_texts_pick_one(texts, forced_entity_type, operator_params)
        elif isinstance(forced_entity_type, str):
            logging.debug("Dispatching to _anonymize_texts_forced_type strategy.")
            results = self._anonymize_texts_forced_type(texts, forced_entity_type, operator_params)
        else:
            results = self.anonymization_strategy.anonymize(texts, operator_params)

        # --- FALLBACK ARCHITECTURE ---
        if len(results) != len(texts):
            logging.warning(
                "Batch integrity failure detected (Input: %d vs Output: %d). "
                "Triggering Safe Fallback Mechanism.",
                len(texts), len(results)
            )
            # The fallback will manage its own entity collection and saving.
            results = self._safe_fallback_processing(texts, operator_params, forced_entity_type)

        # --- DATABASE PERSISTENCE ---
        if self.db_context and entity_collector:
            self.db_context.save_entities(entity_collector)
            logging.debug(f"Saved {len(entity_collector)} entities to the database.")

        return results

    def _safe_fallback_processing(self, texts: List[str], operator_params: Optional[Dict], forced_entity_type: Optional[Union[str, List[str]]]) -> List[str]:
        """
        Fallback Method: Processes item by item to ensure atomicity and alignment,
        with a circuit breaker to prevent runaway failures.
        """
        fallback_results = []
        failure_count = 0
        # Circuit breaker activates if more than 20% of the batch fails, with a minimum of 5 failures.
        failure_threshold = max(5, int(len(texts) * 0.2))

        for text in texts:
            try:
                # We manage a separate collector inside the loop to save entities per item
                # to avoid data loss if a subsequent item fails.
                single_item_collector: List = []
                single_item_params = {
                    "entity_collector": single_item_collector,
                    "hash_generator": self.hash_generator,
                    "slug_length": self.slug_length
                }
                single_result_list = []
                
                # Re-use existing dispatch logic to keep it DRY
                if isinstance(forced_entity_type, list):
                    single_result_list = self._anonymize_texts_pick_one([text], forced_entity_type, single_item_params)
                elif isinstance(forced_entity_type, str):
                    single_result_list = self._anonymize_texts_forced_type([text], forced_entity_type, single_item_params)
                else:
                    # Use the strategy for the single text
                    single_result_list = self.anonymization_strategy.anonymize([text], single_item_params)

                if self.db_context and single_item_collector:
                    self.db_context.save_entities(single_item_collector)

                if not single_result_list:
                    fallback_results.append(text) 
                else:
                    fallback_results.append(single_result_list[0])

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
            cached_value = self.cache_manager.get(cache_key) # Use CacheManager
            if cached_value:
                anonymized_list.append(cached_value)
                continue

            display_hash, full_hash = self.hash_generator.generate_slug(clean_text, self.slug_length)

            if entity_collector is not None:
                entity_collector.append((entity_type, clean_text, display_hash, full_hash))
            
            anonymized_text = f"[{entity_type}_{display_hash}]"
            self.cache_manager.add(cache_key, anonymized_text) # Use CacheManager
            anonymized_list.append(anonymized_text)
        return anonymized_list

    def _generate_anonymized_text(self, original_doc_text: str, merged_entities: List[Dict], entity_collector: Optional[List]) -> str:
        """Generates the anonymized text based on merged entities."""
        new_text_parts = []
        current_idx = 0
        for ent in merged_entities:
            self.total_entities_processed += 1
            self.entity_counts[ent["label"]] = self.entity_counts.get(ent["label"], 0) + 1
            new_text_parts.append(original_doc_text[current_idx:ent["start"]])
            clean_text = " ".join(ent["text"].split()).strip()
            
            display_hash, full_hash = self.hash_generator.generate_slug(clean_text, self.slug_length)

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

            cached_value = self.cache_manager.get(text)
            if cached_value:
                anonymized_results.append(cached_value)
            else:
                anonymized_results.append(None) # Placeholder for now
                texts_to_process_in_batch.append(text)
                indices_map.append(i)

        if not texts_to_process_in_batch:
            return [res if res is not None else "" for res in anonymized_results]

        logging.debug(f"Processing batch of {len(texts_to_process_in_batch)} texts in fast path.")

        if operator_params is None: operator_params = {}
        entity_collector = operator_params.get("entity_collector")
        nlp_engine = self.analyzer_engine.analyzer_engine.nlp_engine
        nlp_model = nlp_engine.nlp[self.lang] 
        docs = nlp_model.pipe(texts_to_process_in_batch, batch_size=self.nlp_batch_size)

        processed_texts = []
        for doc in docs:
            original_doc_text = doc.text
            
            detected_entities = self.entity_detector.extract_entities(doc, original_doc_text)
            merged_entities = self.entity_detector.merge_overlapping_entities(detected_entities)
            
            anonymized_text = self._generate_anonymized_text(original_doc_text, merged_entities, entity_collector)

            self.cache_manager.add(original_doc_text, anonymized_text)
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
        logging.debug(f"[_anonymize_texts_presidio] Entities to use for analysis: {entities_to_use}")
        
        if operator_params is None: operator_params = {}
        # Ensure the essential params are always present for the operator
        operator_params["hash_generator"] = self.hash_generator
        operator_params["slug_length"] = self.slug_length
        if "total_entities_counter" not in operator_params: operator_params["total_entities_counter"] = self
        if "entity_counts" not in operator_params: operator_params["entity_counts"] = self.entity_counts

        
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

            cached_value = self.cache_manager.get(text)
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
            self.cache_manager.add(text, anonymized_text)
            final_anonymized_list.append(anonymized_text)
            logging.debug(f"[_anonymize_texts_presidio]   Final anonymized text: '{anonymized_text}'")
        
        return final_anonymized_list

    def _get_entities_to_anonymize(self) -> List[str]:
        all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
        return [ent for ent in all_entities if ent not in self.entities_to_preserve]

    def detect_entities(self, texts: List[str]) -> List[dict]:
        if not texts: return []

        logging.debug(f"Detecting entities for {len(texts)} texts.")
        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        unique_texts_to_process = sorted(list(set(t for t in original_texts if t)))

        if not unique_texts_to_process: return []

        nlp_engine = self.analyzer_engine.analyzer_engine.nlp_engine
        nlp_model = nlp_engine.nlp[self.lang]
        docs = nlp_model.pipe(unique_texts_to_process, batch_size=self.nlp_batch_size)
        
        return self.entity_detector.detect_entities_in_docs(docs)
