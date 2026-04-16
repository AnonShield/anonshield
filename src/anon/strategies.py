from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, TYPE_CHECKING, Optional, Set, Tuple
import logging
import pandas as pd
import spacy
from presidio_anonymizer import OperatorConfig

if TYPE_CHECKING:
    from .core.protocols import CacheStrategy, HashingStrategy
    from .entity_detector import EntityDetector
    from presidio_analyzer.batch_analyzer_engine import BatchAnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    from presidio_analyzer.nlp_engine import NlpEngine

class AnonymizationStrategy(ABC):
    """Abstract base class for different anonymization strategies."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        """Anonymize a list of texts and return anonymized texts and collected entities."""
        pass

class FullPresidioStrategy(AnonymizationStrategy):
    """
    Comprehensive strategy using the complete Presidio pipeline without filtering.
    
    Architecture:
    - Detection: Presidio AnalyzerEngine with ALL available recognizers
    - Replacement: Presidio AnonymizerEngine (battle-tested)
    
    Performance: SLOWEST (processes hundreds of recognizers)
    Accuracy: HIGHEST (maximum entity coverage)
    Use case: When you need maximum entity detection, regardless of performance
    """
    def __init__(self,
                 analyzer_engine: BatchAnalyzerEngine,
                 anonymizer_engine: AnonymizerEngine,
                 cache_manager: CacheStrategy,
                 lang: str,
                 entities_to_preserve: Set[str],
                 allow_list: Set[str],
                 nlp_batch_size: int = 8,
                 score_threshold: Optional[float] = None):
        super().__init__()
        self.analyzer_engine = analyzer_engine
        self.anonymizer_engine = anonymizer_engine
        self.cache_manager = cache_manager
        self.lang = lang
        self.nlp_batch_size = nlp_batch_size
        self.entities_to_preserve = entities_to_preserve
        self.allow_list = allow_list
        from .config import NerDefaults
        self.score_threshold = score_threshold if score_threshold is not None else NerDefaults.SCORE_THRESHOLD

    def _get_entities_to_anonymize(self, entities: Optional[List[str]] = None) -> List[str]:
        """Determines the list of entities to be analyzed."""
        if entities is not None:
            return entities
        
        all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
        return [ent for ent in all_entities if ent not in self.entities_to_preserve]

    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        """Anonymize a batch of texts using the full Presidio pipeline.

        Checks the LRU cache first, then runs Presidio analysis and
        anonymization on uncached texts, collecting entity mappings for
        database persistence.

        Args:
            texts: Raw input strings to anonymize.
            operator_params: Presidio operator configuration including
                hash_generator and custom_slug_length.

        Returns:
            A tuple of (anonymized_texts, collected_entities).
        """
        self.logger.debug("Executing PresidioStrategy")
        if not texts: return [], []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        collected_entities: List[Tuple] = [] # Initialize collected entities for this batch
        
        # Pass the collected_entities list for the CustomSlugAnonymizer to append to
        operator_params_with_collector = operator_params.copy()
        operator_params_with_collector["entity_collector"] = collected_entities

        entities_to_use = self._get_entities_to_anonymize(operator_params.get("entities"))
        self.logger.debug(f"Entities to use for analysis: {entities_to_use}")

        # PHASE 1: Check cache and filter texts that need processing
        anonymized_results = ["" for _ in original_texts]
        texts_to_process = []
        indices_to_process = []
        
        for idx, text in enumerate(original_texts):
            cached_value = self.cache_manager.get(text)
            if cached_value:
                anonymized_results[idx] = cached_value
            else:
                texts_to_process.append(text)
                indices_to_process.append(idx)
        
        # If all texts were cached, return early
        if not texts_to_process:
            self.logger.debug(f"All {len(original_texts)} texts found in cache")
            return anonymized_results, collected_entities

        self.logger.debug(f"Processing {len(texts_to_process)}/{len(original_texts)} uncached texts")

        # PHASE 2: Analyze only uncached texts
        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            texts_to_process, language=self.lang,
            entities=entities_to_use, score_threshold=self.score_threshold,
            allow_list=self.allow_list,
            batch_size=self.nlp_batch_size
        )
        
        analyzer_results_list = list(analyzer_results_iterator)

        if len(analyzer_results_list) != len(texts_to_process):
            self.logger.error(f"Mismatch between texts_to_process and analyzer_results_list! Input: {len(texts_to_process)}, Analyzer Results: {len(analyzer_results_list)}. This will lead to batch integrity failure.")
            # Return empty lists to trigger the fallback mechanism in the orchestrator
            return [], []

        # PHASE 3: Anonymize and cache results
        for text, analyzer_results, original_idx in zip(texts_to_process, analyzer_results_list, indices_to_process):
            anonymizer_result = self.anonymizer_engine.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators={"DEFAULT": OperatorConfig("custom_slug", operator_params_with_collector)},
            )
            
            anonymized_text = anonymizer_result.text
            self.cache_manager.add(text, anonymized_text)
            anonymized_results[original_idx] = anonymized_text
        
        return anonymized_results, collected_entities

class HybridPresidioStrategy(AnonymizationStrategy):
    """
    Hybrid strategy using Presidio for detection with custom text replacement.
    
    Architecture:
    - Detection: Presidio AnalyzerEngine with filtered entity scope (same as Filtered)
    - Replacement: Manual Python implementation (custom logic)
    
    Performance: FAST (filtered detection + lightweight replacement)
    Accuracy: HIGH (same detection scope as FilteredPresidio)
    Trade-off: Avoids Presidio's AnonymizerEngine overhead but loses its battle-tested logic
    Use case: When you need control over the replacement logic
    """
    def __init__(self, 
                 nlp_engine,  # TransformersNlpEngine with xlm-roberta + spaCy
                 entity_detector: EntityDetector,
                 hash_generator: HashingStrategy,
                 cache_manager: CacheStrategy,
                 lang: str,
                 nlp_batch_size: int,
                 transformer_model: str,
                 entities_to_preserve: Set[str],
                 slm_detector: Optional['SLMEntityDetector'] = None,
                 slm_detector_mode: str = "hybrid",
                 score_threshold: Optional[float] = None):
        super().__init__()
        self.nlp_engine = nlp_engine
        self.entity_detector = entity_detector
        self.hash_generator = hash_generator
        self.cache_manager = cache_manager
        self.lang = lang
        self.nlp_batch_size = nlp_batch_size
        self.transformer_model = transformer_model
        self.entities_to_preserve = entities_to_preserve
        self.slm_detector = slm_detector
        self.slm_detector_mode = slm_detector_mode
        from .config import NerDefaults
        self.score_threshold = score_threshold if score_threshold is not None else NerDefaults.SCORE_THRESHOLD
        self.core_entities = self._get_core_entities()
    
    def _get_core_entities(self) -> List[str]:
        """Returns a curated list of entities supported by our core recognizers (NLP + Custom Regex)."""
        from .engine import load_custom_recognizers
        from .model_registry import get_entity_mapping

        entity_mapping = get_entity_mapping(self.transformer_model)
        core_entities = set(entity_mapping.values())
        for recognizer in load_custom_recognizers(langs=[self.lang]):
            core_entities.update(recognizer.supported_entities)
        return list(core_entities)
    
    def _get_entities_to_anonymize(self) -> List[str]:
        """Returns the list of entities to be analyzed, excluding those to preserve."""
        return [e for e in self.core_entities if e not in self.entities_to_preserve]
    
    def _generate_anonymized_text_and_collect_entities(self, original_doc_text: str, merged_entities: List[Dict], operator_params: Dict) -> Tuple[str, List[Tuple]]:
        """Generates the anonymized text and collects entities based on merged entities."""
        new_text_parts = []
        current_idx = 0
        collected_entities_for_text: List[Tuple] = []
        slug_length = operator_params.get("custom_slug_length", 64)

        for ent in merged_entities:
            new_text_parts.append(original_doc_text[current_idx:ent["start"]])
            clean_text = " ".join(ent["text"].split()).strip()
            
            display_hash, full_hash = self.hash_generator.generate_slug(clean_text, slug_length)

            # Sempre coleta a entidade para estatísticas (com slug_length como flag)
            # Tupla: (entity_type, text, display_hash, full_hash, should_persist)
            should_persist = slug_length > 0
            collected_entities_for_text.append((ent["label"], clean_text, display_hash, full_hash, should_persist))

            if slug_length == 0:
                new_text_parts.append(f"[{ent['label']}]")
            else:
                new_text_parts.append(f"[{ent['label']}_{display_hash}]")
            current_idx = ent["end"]
        
        new_text_parts.append(original_doc_text[current_idx:])
        return "".join(new_text_parts), collected_entities_for_text

    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        """Anonymize a batch of texts using the filtered/hybrid NER pipeline.

        Uses a filtered entity scope and a custom replacement loop instead of
        Presidio's AnonymizerEngine. Optionally merges SLM-detected entities
        in hybrid mode or replaces standard detection entirely in exclusive mode.

        Args:
            texts: Raw input strings to anonymize.
            operator_params: Configuration including hash_generator and
                custom_slug_length.

        Returns:
            A tuple of (anonymized_texts, collected_entities).
        """
        self.logger.debug(f"Executing FastStrategy with SLM mode: {self.slm_detector_mode if self.slm_detector else 'off'}")
        if not texts: return [], []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        
        anonymized_results = ["" for _ in original_texts]
        collected_entities_total: List[Tuple] = []
        texts_to_process_in_batch = []
        indices_map = [] 

        for i, text in enumerate(original_texts):
            if not text:
                continue

            cached_value = self.cache_manager.get(text)
            if cached_value:
                anonymized_results[i] = cached_value
            else:
                texts_to_process_in_batch.append(text)
                indices_map.append(i)

        if not texts_to_process_in_batch:
            return anonymized_results, collected_entities_total

        self.logger.debug(f"Processing batch of {len(texts_to_process_in_batch)} texts in fast path.")

        # Get the filtered list of entities to analyze
        entities_to_use = self._get_entities_to_anonymize()
        self.logger.debug(f"Entities to use for analysis: {entities_to_use}")

        # Detect entities using xlm-roberta transformer via Presidio's batch analyzer
        # Now with entity filtering to reduce unnecessary processing
        analyzer_results_iterator = self.nlp_engine.analyze_iterator(
            texts_to_process_in_batch, language=self.lang,
            entities=entities_to_use, score_threshold=self.score_threshold,
            batch_size=self.nlp_batch_size
        )
        
        analyzer_results_list = list(analyzer_results_iterator)

        for idx, (original_doc_text, analyzer_results) in enumerate(zip(texts_to_process_in_batch, analyzer_results_list)):
            
            # --- Hybrid/Exclusive Detection Logic ---
            detected_entities = []
            
            # Add transformer-detected entities (xlm-roberta)
            if not (self.slm_detector and self.slm_detector_mode == 'exclusive'):
                self.logger.debug("Running xlm-roberta entity detector.")
                
                # Convert Presidio results to entity format
                for result in analyzer_results:
                    detected_entities.append({
                        "start": result.start,
                        "end": result.end,
                        "label": result.entity_type,
                        "text": original_doc_text[result.start:result.end],
                        "score": result.score
                    })

            # Run SLM detector if enabled
            if self.slm_detector:
                self.logger.debug(f"SLM detector enabled in '{self.slm_detector_mode}' mode.")
                slm_results = self.slm_detector.detect_entities([original_doc_text], language=self.lang)
                
                # Convert SLM results to the same format as traditional results
                for result in slm_results:
                    for start, end, label in result.get("label", []):
                        detected_entities.append({
                            "start": start,
                            "end": end,
                            "label": label,
                            "text": original_doc_text[start:end],
                            "score": 0.85 # Assign a confident score for SLM entities
                        })
            
            # Merge all collected entities
            merged_entities = self.entity_detector.merge_overlapping_entities(detected_entities)
            
            anonymized_text, collected_entities_for_text = self._generate_anonymized_text_and_collect_entities(original_doc_text, merged_entities, operator_params)
            collected_entities_total.extend(collected_entities_for_text)

            self.cache_manager.add(original_doc_text, anonymized_text)
            
            original_index = indices_map[idx]
            anonymized_results[original_index] = anonymized_text
        
        return anonymized_results, collected_entities_total


class FilteredPresidioStrategy(FullPresidioStrategy):
    """
    Optimized strategy using complete Presidio pipeline with filtered entity scope.
    
    Architecture:
    - Detection: Presidio AnalyzerEngine with FILTERED recognizers (only relevant entities)
    - Replacement: Presidio AnonymizerEngine (battle-tested, optimized)
    
    Performance: FASTEST (filtered scope drastically reduces detection overhead)
    Accuracy: HIGH (focuses on relevant entities for CSIRT context)
    Recommended: YES - Best balance of speed and reliability
    
    This is the recommended strategy for production use. It achieves optimal performance
    by filtering out irrelevant Presidio recognizers (passports, SSNs, etc.) while
    maintaining the robust and well-tested Presidio anonymization pipeline.
    """
    def __init__(self, transformer_model: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transformer_model = transformer_model
        self.core_entities = self._get_core_entities()

    def _get_core_entities(self) -> List[str]:
        """Returns a curated list of entities supported by our core recognizers (NLP + Custom Regex)."""
        from .engine import load_custom_recognizers
        from .model_registry import get_entity_mapping

        entity_mapping = get_entity_mapping(self.transformer_model)
        core_entities = set(entity_mapping.values())
        for recognizer in load_custom_recognizers(langs=[self.lang]):
            core_entities.update(recognizer.supported_entities)
        return list(core_entities)

    def _get_entities_to_anonymize(self, entities: Optional[List[str]] = None) -> List[str]:
        """Overrides the parent method to use only the core entities."""
        return [e for e in self.core_entities if e not in self.entities_to_preserve]


def strategy_factory(strategy_name: str, **kwargs) -> AnonymizationStrategy:
    """
    Factory to create an anonymization strategy instance by injecting dependencies.
    
    Strategy naming convention (semantic architecture):
    - FullPresidio: Complete Presidio pipeline, no filtering (slowest, highest coverage)
    - FilteredPresidio: Complete Presidio pipeline with filtered scope (FASTEST, RECOMMENDED)
    - HybridPresidio: Presidio detection + manual replacement (fast, custom logic)
    - Standalone: Zero Presidio dependencies (theoretical maximum performance)
    
    Args:
        strategy_name: The name of the strategy to create
                      ('presidio', 'filtered', 'hybrid', 'standalone')
        **kwargs: Dependencies required by the strategies.
    
    Returns:
        AnonymizationStrategy instance
        
    Raises:
        ValueError: If strategy_name is unknown
    """
    strategy_name = strategy_name.lower()

    if strategy_name == "presidio":
        # Full Presidio: Complete pipeline without filtering
        return FullPresidioStrategy(
            analyzer_engine=kwargs["analyzer_engine"],
            anonymizer_engine=kwargs["anonymizer_engine"],
            cache_manager=kwargs["cache_manager"],
            lang=kwargs["lang"],
            entities_to_preserve=kwargs["entities_to_preserve"],
            allow_list=kwargs["allow_list"],
            nlp_batch_size=kwargs["nlp_batch_size"],
            score_threshold=kwargs.get("score_threshold"),
        )

    elif strategy_name == "filtered":
        # Filtered Presidio: Complete pipeline with filtered entity scope (RECOMMENDED)
        return FilteredPresidioStrategy(
            transformer_model=kwargs["transformer_model"],
            analyzer_engine=kwargs["analyzer_engine"],
            anonymizer_engine=kwargs["anonymizer_engine"],
            cache_manager=kwargs["cache_manager"],
            lang=kwargs["lang"],
            entities_to_preserve=kwargs["entities_to_preserve"],
            allow_list=kwargs["allow_list"],
            nlp_batch_size=kwargs["nlp_batch_size"],
            score_threshold=kwargs.get("score_threshold"),
        )

    elif strategy_name == "hybrid":
        # Hybrid: Presidio detection + manual text replacement
        return HybridPresidioStrategy(
            nlp_engine=kwargs["analyzer_engine"],
            entity_detector=kwargs["entity_detector"],
            slm_detector=kwargs.get("slm_detector"),
            slm_detector_mode=kwargs.get("slm_detector_mode", "hybrid"),
            hash_generator=kwargs["hash_generator"],
            cache_manager=kwargs["cache_manager"],
            lang=kwargs["lang"],
            nlp_batch_size=kwargs["nlp_batch_size"],
            transformer_model=kwargs["transformer_model"],
            entities_to_preserve=kwargs["entities_to_preserve"],
            score_threshold=kwargs.get("score_threshold"),
        )
    
    elif strategy_name == "standalone":
        # Standalone: Zero Presidio dependencies
        from .standalone_strategy import StandaloneStrategy
        return StandaloneStrategy(
            transformer_model=kwargs["transformer_model"],
            entity_detector=kwargs["entity_detector"],
            hash_generator=kwargs["hash_generator"],
            cache_manager=kwargs["cache_manager"],
            lang=kwargs["lang"],
            entities_to_preserve=kwargs["entities_to_preserve"],
            slm_detector=kwargs.get("slm_detector"),
            slm_detector_mode=kwargs.get("slm_detector_mode", "hybrid")
        )

    elif strategy_name == "regex":
        # Regex-only: pure regex matching, zero ML/NLP overhead (fastest possible)
        from .standalone_strategy import RegexOnlyStrategy
        return RegexOnlyStrategy(
            entity_detector=kwargs["entity_detector"],
            hash_generator=kwargs["hash_generator"],
            cache_manager=kwargs["cache_manager"],
            entities_to_preserve=kwargs["entities_to_preserve"],
        )

    else:
        raise ValueError(
            f"Unknown anonymization strategy: {strategy_name}. "
            f"Available strategies: 'presidio', 'filtered' (recommended), 'hybrid', 'standalone', 'regex'."
        )


