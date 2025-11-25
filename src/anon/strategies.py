from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, TYPE_CHECKING, Optional, Set, Tuple
import logging
import pandas as pd
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

class PresidioStrategy(AnonymizationStrategy):
    """Comprehensive analysis using the full Presidio pipeline."""
    def __init__(self, 
                 analyzer_engine: BatchAnalyzerEngine, 
                 anonymizer_engine: AnonymizerEngine,
                 cache_manager: CacheStrategy,
                 lang: str,
                 entities_to_preserve: Set[str],
                 allow_list: Set[str]):
        super().__init__()
        self.analyzer_engine = analyzer_engine
        self.anonymizer_engine = anonymizer_engine
        self.cache_manager = cache_manager
        self.lang = lang
        self.entities_to_preserve = entities_to_preserve
        self.allow_list = allow_list

    def _get_entities_to_anonymize(self, entities: Optional[List[str]] = None) -> List[str]:
        """Determines the list of entities to be analyzed."""
        if entities is not None:
            return entities
        
        all_entities = self.analyzer_engine.analyzer_engine.get_supported_entities()
        return [ent for ent in all_entities if ent not in self.entities_to_preserve]

    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        self.logger.debug("Executing PresidioStrategy")
        if not texts: return [], []

        original_texts = [str(text) if pd.notna(text) else "" for text in texts]
        final_anonymized_list = []
        collected_entities: List[Tuple] = [] # Initialize collected entities for this batch
        
        # Pass the collected_entities list for the CustomSlugAnonymizer to append to
        operator_params_with_collector = operator_params.copy()
        operator_params_with_collector["entity_collector"] = collected_entities

        entities_to_use = self._get_entities_to_anonymize(operator_params.get("entities"))
        self.logger.debug(f"Entities to use for analysis: {entities_to_use}")

        analyzer_results_iterator = self.analyzer_engine.analyze_iterator(
            original_texts, language=self.lang,
            entities=entities_to_use, score_threshold=0.6,
            allow_list=self.allow_list
        )
        
        analyzer_results_list = list(analyzer_results_iterator)

        if len(analyzer_results_list) != len(original_texts):
            self.logger.error(f"Mismatch between original_texts and analyzer_results_list! Input: {len(original_texts)}, Analyzer Results: {len(analyzer_results_list)}. This will lead to batch integrity failure.")
            # Return empty lists to trigger the fallback mechanism in the orchestrator
            return [], []

        for text, analyzer_results in zip(original_texts, analyzer_results_list):
            cached_value = self.cache_manager.get(text)
            if cached_value:
                final_anonymized_list.append(cached_value)
                continue

            anonymizer_result = self.anonymizer_engine.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators={"DEFAULT": OperatorConfig("custom_slug", operator_params_with_collector)},
            )
            
            anonymized_text = anonymizer_result.text
            self.cache_manager.add(text, anonymized_text)
            final_anonymized_list.append(anonymized_text)
        
        return final_anonymized_list, collected_entities

class FastStrategy(AnonymizationStrategy):
    """Optimized path that bypasses the full Presidio AnalyzerEngine."""
    def __init__(self, 
                 nlp_engine: NlpEngine, 
                 entity_detector: EntityDetector,
                 hash_generator: HashingStrategy,
                 cache_manager: CacheStrategy,
                 lang: str,
                 nlp_batch_size: int):
        super().__init__()
        self.nlp_engine = nlp_engine
        self.entity_detector = entity_detector
        self.hash_generator = hash_generator
        self.cache_manager = cache_manager
        self.lang = lang
        self.nlp_batch_size = nlp_batch_size
    
    def _generate_anonymized_text_and_collect_entities(self, original_doc_text: str, merged_entities: List[Dict], operator_params: Dict) -> Tuple[str, List[Tuple]]:
        """Generates the anonymized text and collects entities based on merged entities."""
        new_text_parts = []
        current_idx = 0
        collected_entities_for_text: List[Tuple] = []
        slug_length = operator_params.get("slug_length")

        for ent in merged_entities:
            new_text_parts.append(original_doc_text[current_idx:ent["start"]])
            clean_text = " ".join(ent["text"].split()).strip()
            
            display_hash, full_hash = self.hash_generator.generate_slug(clean_text, slug_length)

            collected_entities_for_text.append((ent["label"], clean_text, display_hash, full_hash))
            new_text_parts.append(f"[{ent['label']}_{display_hash}]")
            current_idx = ent["end"]
        
        new_text_parts.append(original_doc_text[current_idx:])
        return "".join(new_text_parts), collected_entities_for_text

    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        self.logger.debug("Executing FastStrategy")
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

        nlp_model = self.nlp_engine.nlp[self.lang] 
        docs = nlp_model.pipe(texts_to_process_in_batch, batch_size=self.nlp_batch_size)

        for i, doc in enumerate(docs):
            original_doc_text = doc.text
            
            detected_entities = self.entity_detector.extract_entities(doc, original_doc_text)
            merged_entities = self.entity_detector.merge_overlapping_entities(detected_entities)
            
            anonymized_text, collected_entities_for_text = self._generate_anonymized_text_and_collect_entities(original_doc_text, merged_entities, operator_params)
            collected_entities_total.extend(collected_entities_for_text)

            self.cache_manager.add(original_doc_text, anonymized_text)
            
            original_index = indices_map[i]
            anonymized_results[original_index] = anonymized_text
        
        return anonymized_results, collected_entities_total


class BalancedStrategy(PresidioStrategy):
    """
    A balance between speed and accuracy, using Presidio with a limited set of recognizers.
    It inherits from PresidioStrategy and overrides the entity selection logic.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.core_entities = self._get_core_entities()

    def _get_core_entities(self) -> List[str]:
        """Returns a curated list of entities supported by our core recognizers (NLP + Custom Regex)."""
        from .engine import load_custom_recognizers
        from .config import ENTITY_MAPPING
        
        core_entities = set(ENTITY_MAPPING.values())
        for recognizer in load_custom_recognizers(langs=[self.lang]):
            core_entities.update(recognizer.supported_entities)
        return list(core_entities)

    def _get_entities_to_anonymize(self, entities: Optional[List[str]] = None) -> List[str]:
        """Overrides the parent method to use only the core entities."""
        return [e for e in self.core_entities if e not in self.entities_to_preserve]


def strategy_factory(strategy_name: str, **kwargs) -> AnonymizationStrategy:
    """
    Factory to create an anonymization strategy instance by injecting dependencies.
    
    Args:
        strategy_name: The name of the strategy to create.
        **kwargs: Dependencies required by the strategies.
    """
    strategy_name = strategy_name.lower()
    
    if strategy_name == "presidio":
        return PresidioStrategy(
            analyzer_engine=kwargs["analyzer_engine"],
            anonymizer_engine=kwargs["anonymizer_engine"],
            cache_manager=kwargs["cache_manager"],
            lang=kwargs["lang"],
            entities_to_preserve=kwargs["entities_to_preserve"],
            allow_list=kwargs["allow_list"]
        )
    elif strategy_name == "fast":
        return FastStrategy(
            nlp_engine=kwargs["analyzer_engine"].analyzer_engine.nlp_engine,
            entity_detector=kwargs["entity_detector"],
            hash_generator=kwargs["hash_generator"],
            cache_manager=kwargs["cache_manager"],
            lang=kwargs["lang"],
            nlp_batch_size=kwargs["nlp_batch_size"]
        )
    elif strategy_name == "balanced":
        return BalancedStrategy(
            analyzer_engine=kwargs["analyzer_engine"],
            anonymizer_engine=kwargs["anonymizer_engine"],
            cache_manager=kwargs["cache_manager"],
            lang=kwargs["lang"],
            entities_to_preserve=kwargs["entities_to_preserve"],
            allow_list=kwargs["allow_list"]
        )
    else:
        raise ValueError(f"Unknown anonymization strategy: {strategy_name}")

