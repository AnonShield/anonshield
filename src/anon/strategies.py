from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, TYPE_CHECKING, Optional, Set, Tuple
import logging
import pandas as pd
import spacy
from presidio_analyzer import RecognizerResult
from presidio_anonymizer import OperatorConfig

from .entity_selection import is_entity_excluded

if TYPE_CHECKING:
    from .core.protocols import CacheStrategy
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

# Recognizers that report transformer/spaCy NER results. --ner-score-threshold
# is documented as the NER cut-off; applying it to the regex recognizers too made
# a threshold of 0.9 drop every IP address (regex score 0.85) into the output.
_NER_RECOGNIZERS = {"SpacyRecognizer", "TransformersRecognizer", "StanzaRecognizer"}


def analysis_floor(ner_threshold: float) -> float:
    """Score floor for Presidio analysis: NER results are cut later, by
    filter_ner_threshold, while the other recognizers keep the default floor."""
    from .config import NerDefaults
    return min(ner_threshold, NerDefaults.SCORE_THRESHOLD)


def filter_ner_threshold(analyzer_results, ner_threshold: float) -> list:
    from .config import NerDefaults
    kept = []
    for r in analyzer_results:
        name = (getattr(r, "recognition_metadata", None) or {}).get("recognizer_name", "")
        floor = ner_threshold if name in _NER_RECOGNIZERS else NerDefaults.SCORE_THRESHOLD
        if r.score >= floor:
            kept.append(r)
    return kept


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
                 score_threshold: Optional[float] = None,
                 entities_to_anonymize: Optional[Set[str]] = None,
                 entity_detector: Optional[EntityDetector] = None):
        super().__init__()
        self.analyzer_engine = analyzer_engine
        self.anonymizer_engine = anonymizer_engine
        self.cache_manager = cache_manager
        self.lang = lang
        self.nlp_batch_size = nlp_batch_size
        self.entities_to_preserve = entities_to_preserve
        self.entities_to_anonymize = entities_to_anonymize
        self.allow_list = allow_list
        # Source of the word-list / custom patterns, which are not in the
        # (shared, cached) Presidio registry.
        self.entity_detector = entity_detector
        from .config import NerDefaults
        self.score_threshold = score_threshold if score_threshold is not None else NerDefaults.SCORE_THRESHOLD

    def _get_entities_to_anonymize(self, entities: Optional[List[str]] = None) -> List[str]:
        """Determines the list of entities to be analyzed.

        Preserved types are analyzed too: they keep their span in _final_results.
        """
        if entities is not None:
            return entities
        
        return list(self.analyzer_engine.analyzer_engine.get_supported_entities())

    def _final_results(self, text: str, analyzer_results) -> List[RecognizerResult]:
        """Presidio results plus word-list/custom matches, with exclusions applied
        and overlaps resolved (see EntityDetector.finalize)."""
        detected = [{"start": r.start, "end": r.end, "label": r.entity_type, "score": r.score,
                     "text": text[r.start:r.end]}
                    for r in filter_ner_threshold(analyzer_results, self.score_threshold)]
        if self.entity_detector is not None:
            detected += self.entity_detector.extract_custom_entities(text)
            detected = self.entity_detector.finalize(text, detected)
        else:
            detected = [d for d in detected
                        if not is_entity_excluded(d["label"], self.entities_to_preserve, self.entities_to_anonymize)
                        and d["text"] not in self.allow_list]
        return [RecognizerResult(entity_type=d["label"], start=d["start"], end=d["end"], score=d["score"])
                for d in detected]

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
            entities=entities_to_use, score_threshold=analysis_floor(self.score_threshold),
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
                analyzer_results=self._final_results(text, analyzer_results),
                operators={"DEFAULT": OperatorConfig("custom_slug", operator_params_with_collector)},
            )
            
            anonymized_text = anonymizer_result.text
            self.cache_manager.add(text, anonymized_text)
            anonymized_results[original_idx] = anonymized_text
        
        return anonymized_results, collected_entities

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
        return list(self.core_entities)


def strategy_factory(strategy_name: str, **kwargs) -> AnonymizationStrategy:
    """
    Factory to create an anonymization strategy instance by injecting dependencies.
    
    Strategy naming convention (semantic architecture):
    - FullPresidio: Complete Presidio pipeline, no filtering (slowest, highest coverage)
    - FilteredPresidio: Complete Presidio pipeline with filtered scope (FASTEST, RECOMMENDED)
    - Standalone: Zero Presidio dependencies (theoretical maximum performance)
    
    Args:
        strategy_name: The name of the strategy to create
                      ('presidio', 'filtered', 'standalone', 'regex'; a retired
                      name runs its replacement, see strategy_names.py)
        **kwargs: Dependencies required by the strategies.
    
    Returns:
        AnonymizationStrategy instance
        
    Raises:
        ValueError: If strategy_name is unknown
    """
    from .strategy_names import canonical_strategy
    strategy_name = canonical_strategy(strategy_name)

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
            entities_to_anonymize=kwargs.get("entities_to_anonymize"),
            entity_detector=kwargs.get("entity_detector"),
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
            entities_to_anonymize=kwargs.get("entities_to_anonymize"),
            entity_detector=kwargs.get("entity_detector"),
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
            score_threshold=kwargs.get("score_threshold"),
            aggregation_strategy=kwargs.get("aggregation_strategy"),
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
            f"Available strategies: 'presidio', 'filtered' (recommended), 'standalone', 'regex'."
        )


