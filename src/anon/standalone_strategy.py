"""
Standalone Strategy - Zero Presidio Dependencies.

This module implements a pure Python NLP pipeline for entity detection and anonymization
without any Presidio dependencies. It loads models directly and handles all processing manually.

Author: AnonShield Team
Architecture: SOLID principles, minimal dependencies, maximum performance
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, TYPE_CHECKING, Optional, Set, Tuple
import logging
import pandas as pd

# Module-level pipeline cache, keyed by (model_id, device).
# Avoids reloading the transformer model on every job.
_PIPELINE_CACHE: dict[str, object] = {}

if TYPE_CHECKING:
    from .core.protocols import CacheStrategy, HashingStrategy
    from .entity_detector import EntityDetector


# Standalone base class - NO Presidio imports
class StandaloneAnonymizationStrategy(ABC):
    """Abstract base class for standalone anonymization strategies (Presidio-free)."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        """Anonymize a list of texts and return anonymized texts and collected entities."""
        pass


class StandaloneStrategy(StandaloneAnonymizationStrategy):
    """
    Standalone strategy with zero Presidio dependencies - pure Python NLP pipeline.
    
    Architecture:
    - Detection: Direct spaCy + Transformer + Custom Regex (no Presidio wrapper)
    - Replacement: Manual Python implementation
    
    Performance: FASTEST* (eliminates ALL Presidio overhead)
    Accuracy: HIGH (same models, direct execution)
    Dependencies: Minimal (transformers, spacy, custom regex only)
    
    *Theoretical best performance - trades Presidio's mature ecosystem for raw speed.
    Use case: When you need absolute maximum performance and don't need Presidio features.
    
    Quality Assurance Notes:
    - Edge case: Overlapping entities must be handled correctly (merge logic critical)
    - Security: Direct model loading - ensure model sources are trusted
    - Maintainability: Updates to transformer API require manual adaptation
    """
    
    def __init__(self,
                 transformer_model: str,
                 entity_detector: EntityDetector,
                 hash_generator: HashingStrategy,
                 cache_manager: CacheStrategy,
                 lang: str,
                 entities_to_preserve: Set[str],
                 slm_detector: Optional['SLMEntityDetector'] = None,
                 slm_detector_mode: str = "hybrid",
                 score_threshold: Optional[float] = None,
                 aggregation_strategy: Optional[str] = None):
        super().__init__()
        from .config import NerDefaults
        from .model_registry import get_entity_mapping
        self.transformer_model = transformer_model
        self.entity_detector = entity_detector
        self.hash_generator = hash_generator
        self.cache_manager = cache_manager
        self.lang = lang
        self.entities_to_preserve = entities_to_preserve
        self.slm_detector = slm_detector
        self.slm_detector_mode = slm_detector_mode
        self.score_threshold = score_threshold if score_threshold is not None else NerDefaults.SCORE_THRESHOLD
        self.aggregation_strategy = aggregation_strategy or NerDefaults.AGGREGATION_STRATEGY
        self.entity_mapping = get_entity_mapping(self.transformer_model)
        
        # Load models directly (no Presidio). The regexes come from the shared
        # EntityDetector: the run's built-in recognizers for the language plus
        # the word list and custom patterns, with the allow list applied.
        self._load_models()
        
    def _load_models(self):
        """Load Transformer and spaCy models directly."""
        from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
        import torch
        import spacy
        
        from .device import cuda_usable

        # Detect GPU availability (and that this torch build can run on it)
        if cuda_usable():
            device = 0  # Use first GPU
            self.logger.info(f"GPU detected: {torch.cuda.get_device_name(0)}")
        else:
            device = -1  # CPU fallback
            self.logger.info("No GPU detected, using CPU")
        
        self.logger.info(f"Loading Transformer model directly: {self.transformer_model}")

        cache_key = f"{self.transformer_model}:{device}:{self.aggregation_strategy}"
        if cache_key in _PIPELINE_CACHE:
            self.logger.info("Pipeline cache hit for '%s'; skipping model load.", self.transformer_model)
            self.ner_pipeline = _PIPELINE_CACHE[cache_key]
        else:
            try:
                # Load transformer NER pipeline with GPU support
                self.ner_pipeline = pipeline(
                    "ner",
                    model=self.transformer_model,
                    tokenizer=self.transformer_model,
                    aggregation_strategy=self.aggregation_strategy,
                    device=device
                )
                _PIPELINE_CACHE[cache_key] = self.ner_pipeline
                self.logger.info(f"Transformer model loaded successfully on {'GPU' if device >= 0 else 'CPU'}")
            except Exception as e:
                self.logger.error(f"Failed to load transformer model: {e}")
                raise
        
        # Load spaCy for tokenization/sentence splitting if needed
        try:
            self.nlp = spacy.blank(self.lang if self.lang in ["en", "pt", "es", "fr", "de"] else "en")
            self.logger.info(f"spaCy blank model loaded for language: {self.lang}")
        except Exception as e:
            self.logger.warning(f"Could not load spaCy: {e}. Continuing without spaCy support.")
            self.nlp = None
    
    def _detect_entities(self, text: str) -> List[Dict]:
        """
        Detect entities using direct model execution (no Presidio).
        
        Quality Assurance:
        - Handles transformer tokenization misalignment gracefully
        - Validates entity boundaries against original text
        - Applies filtering based on entities_to_preserve
        """
        from .engine import chunked_ner
        entities = []
        
        # 1. Transformer-based NER, over the whole text (the model alone stops
        # at its 512-token window).
        if not (self.slm_detector and self.slm_detector_mode == 'exclusive'):
            try:
                ner_results = chunked_ner(self.ner_pipeline, text)
                for result in ner_results:
                    if float(result["score"]) < self.score_threshold:
                        continue
                    entity_type = self.entity_mapping.get(
                        result["entity_group"], 
                        result["entity_group"]
                    )
                    
                    # Offsets of SentencePiece tokens include the leading space;
                    # replacing it would glue the pseudonym to the previous word.
                    start, end = result["start"], result["end"]
                    while start < end and text[start].isspace():
                        start += 1
                    while end > start and text[end - 1].isspace():
                        end -= 1
                    span = text[start:end]
                    if not span:
                        continue
                    
                    entities.append({
                        "start": start,
                        "end": end,
                        "label": entity_type,
                        "text": span,
                        "score": float(result["score"])
                    })
            except Exception as e:
                self.logger.error(f"Transformer NER failed: {e}")
                raise
        
        # 2. Regex-based recognition (pure Python - no Presidio)
        entities.extend(self.entity_detector.extract_regex_entities(text))
        
        # 3. SLM detector (if enabled)
        if self.slm_detector:
            try:
                slm_results = self.slm_detector.detect_entities([text], language=self.lang)
                for result in slm_results:
                    for start, end, label in result.get("label", []):
                        entities.append({
                            "start": start,
                            "end": end,
                            "label": label,
                            "text": text[start:end],
                            "score": 0.85
                        })
            except Exception as e:
                self.logger.warning(f"SLM detector failed: {e}")
        
        return entities
    
    def _generate_anonymized_text(
        self, text: str, entities: List[Dict], operator_params: Dict
    ) -> Tuple[str, List[Tuple]]:
        """
        Generate anonymized text with collected entities.
        
        Quality Assurance:
        - Ensures entities are processed in order (critical for offset management)
        - Validates that entity boundaries don't corrupt text
        - Handles empty or overlapping entities gracefully
        """
        new_text_parts = []
        current_idx = 0
        collected_entities: List[Tuple] = []
        slug_length = operator_params.get("custom_slug_length", 64)
        
        # Sort entities by start position (critical for correctness)
        sorted_entities = sorted(entities, key=lambda e: e["start"])
        
        for ent in sorted_entities:
            # Add text before entity
            new_text_parts.append(text[current_idx:ent["start"]])
            
            # Clean entity text
            clean_text = " ".join(ent["text"].split()).strip()
            
            # Generate slug
            display_hash, full_hash = self.hash_generator.generate_slug(
                clean_text, slug_length
            )
            
            # Collect entity
            should_persist = slug_length > 0
            collected_entities.append((
                ent["label"], clean_text, display_hash, full_hash, should_persist
            ))
            
            # Add anonymized replacement
            if slug_length == 0:
                new_text_parts.append(f"[{ent['label']}]")
            else:
                new_text_parts.append(f"[{ent['label']}_{display_hash}]")
            
            current_idx = ent["end"]
        
        # Add remaining text
        new_text_parts.append(text[current_idx:])
        
        return "".join(new_text_parts), collected_entities
    
    def anonymize(
        self, texts: List[str], operator_params: Dict
    ) -> Tuple[List[str], List[Tuple]]:
        """
        Anonymize texts using standalone pipeline (no Presidio).
        
        Quality Assurance:
        - Handles empty input gracefully
        - Preserves input order in output
        - Manages cache consistency
        - Fails closed: a text that cannot be processed raises instead of
          passing through unchanged
        """
        self.logger.debug("Executing StandaloneStrategy (zero Presidio dependencies)")
        
        if not texts:
            return [], []
        
        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        anonymized_results = ["" for _ in original_texts]
        collected_entities_total: List[Tuple] = []
        
        for idx, text in enumerate(original_texts):
            if not text:
                continue
            
            # Check cache
            cached_value = self.cache_manager.get(text)
            if cached_value:
                anonymized_results[idx] = cached_value
                continue
            
            try:
                # Detect entities
                detected_entities = self._detect_entities(text)
                
                # Drop preserved / allow-listed spans, merge overlaps
                merged_entities = self.entity_detector.finalize(text, detected_entities)
                
                # Generate anonymized text
                anonymized_text, collected = self._generate_anonymized_text(
                    text, merged_entities, operator_params
                )
                
                # Cache and collect
                self.cache_manager.add(text, anonymized_text)
                anonymized_results[idx] = anonymized_text
                collected_entities_total.extend(collected)
                
            except Exception as e:
                # Fail closed: writing the original text here would put raw PII
                # in an output that looks anonymized.
                self.logger.error(f"Failed to anonymize text at index {idx}: {e}")
                raise
        
        return anonymized_results, collected_entities_total


class RegexOnlyStrategy(StandaloneAnonymizationStrategy):
    """
    Pure regex anonymization with zero NLP/ML overhead.

    Detection: compiled regex patterns only (no spaCy, no Transformers)
    Replacement: same slug-based logic as StandaloneStrategy
    Performance: FASTEST of all strategies (no model loading whatsoever)
    Use case: high-throughput pipelines where regex coverage is sufficient
              (emails, IPs, CVEs, hashes, CPF, credit cards, etc.)
    """

    def __init__(
        self,
        entity_detector,
        hash_generator,
        cache_manager,
        entities_to_preserve: set,
    ):
        super().__init__()
        self.entity_detector = entity_detector
        self.hash_generator = hash_generator
        self.cache_manager = cache_manager
        self.entities_to_preserve = entities_to_preserve

    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        self.logger.debug("Executing RegexOnlyStrategy (zero NLP dependencies)")
        if not texts:
            return [], []

        original_texts = [str(t) if pd.notna(t) else "" for t in texts]
        anonymized_results = [""] * len(original_texts)
        collected_entities_total: List[Tuple] = []

        slug_length = operator_params.get("custom_slug_length", 64)

        for idx, text in enumerate(original_texts):
            if not text:
                continue
            cached = self.cache_manager.get(text)
            if cached:
                anonymized_results[idx] = cached
                continue
            try:
                detected = self.entity_detector.extract_regex_entities(text)
                merged = self.entity_detector.finalize(text, detected)

                parts: List[str] = []
                cur = 0
                collected: List[Tuple] = []
                for ent in merged:
                    parts.append(text[cur:ent["start"]])
                    clean = " ".join(ent["text"].split()).strip()
                    display_hash, full_hash = self.hash_generator.generate_slug(clean, slug_length)
                    collected.append((ent["label"], clean, display_hash, full_hash, slug_length > 0))
                    parts.append(f"[{ent['label']}]" if slug_length == 0 else f"[{ent['label']}_{display_hash}]")
                    cur = ent["end"]
                parts.append(text[cur:])

                anonymized_text = "".join(parts)
                self.cache_manager.add(text, anonymized_text)
                anonymized_results[idx] = anonymized_text
                collected_entities_total.extend(collected)
            except Exception as e:
                # Fail closed (see StandaloneStrategy.anonymize).
                self.logger.error(f"RegexOnlyStrategy failed at index {idx}: {e}")
                raise

        return anonymized_results, collected_entities_total
