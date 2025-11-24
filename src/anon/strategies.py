from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from .engine import AnonymizationOrchestrator

class AnonymizationStrategy(ABC):
    """Abstract base class for different anonymization strategies."""

    def __init__(self, orchestrator: "AnonymizationOrchestrator"):
        self.orchestrator = orchestrator
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def anonymize(self, texts: List[str], operator_params: Dict) -> List[str]:
        """Anonymize a list of texts."""
        pass

class PresidioStrategy(AnonymizationStrategy):
    """Comprehensive analysis using the full Presidio pipeline."""

    def anonymize(self, texts: List[str], operator_params: Dict) -> List[str]:
        self.logger.debug("Executing PresidioStrategy")
        entities_to_anonymize = self.orchestrator._get_entities_to_anonymize()
        return self.orchestrator._anonymize_texts_presidio(
            texts, operator_params, entities=entities_to_anonymize
        )

class FastStrategy(AnonymizationStrategy):
    """Optimized path that bypasses the full Presidio AnalyzerEngine."""

    def anonymize(self, texts: List[str], operator_params: Dict) -> List[str]:
        self.logger.debug("Executing FastStrategy")
        return self.orchestrator._anonymize_texts_fast_path(texts, operator_params)

class BalancedStrategy(AnonymizationStrategy):
    """
    A balance between speed and accuracy, using Presidio with a limited set of recognizers.
    """

    def anonymize(self, texts: List[str], operator_params: Dict) -> List[str]:
        self.logger.debug("Executing BalancedStrategy")
        core_entities = self.orchestrator._get_core_entities()
        entities_to_anonymize = [e for e in core_entities if e not in self.orchestrator.entities_to_preserve]
        return self.orchestrator._anonymize_texts_presidio(
            texts, operator_params, entities=entities_to_anonymize
        )

def strategy_factory(strategy_name: str, orchestrator: "AnonymizationOrchestrator") -> AnonymizationStrategy:
    """Factory to create an anonymization strategy instance."""
    strategies = {
        "presidio": PresidioStrategy,
        "fast": FastStrategy,
        "balanced": BalancedStrategy,
    }
    strategy_class = strategies.get(strategy_name.lower())
    if not strategy_class:
        raise ValueError(f"Unknown anonymization strategy: {strategy_name}")
    return strategy_class(orchestrator)
