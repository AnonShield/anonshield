"""
Core Architectural Protocols for the Anonymization Engine

This module defines the interfaces (via typing.Protocol) for the core components
of the system. Using protocols allows for dependency inversion and makes the system
more modular, testable, and extensible.
"""
from typing import Protocol, List, Tuple, Optional, Dict, Any

# Forward declaration for type hinting circular dependencies
class AnonymizationOrchestrator:
    pass

class EntityStorage(Protocol):
    """
    Protocol for classes that handle the persistence of anonymized entities.
    """
    def initialize(self, synchronous: Optional[str] = None) -> None:
        ...

    def save_entities(self, entity_list: List[Tuple]) -> None:
        ...

    def shutdown(self) -> None:
        ...

class CacheStrategy(Protocol):
    """
    Protocol for in-memory caching strategies (e.g., LRU cache).
    """
    def get(self, key: str) -> Optional[str]:
        ...

    def add(self, key: str, value: str) -> None:
        ...

class HashingStrategy(Protocol):
    """
    Protocol for classes that generate hashes/slugs from text.
    """
    def generate_slug(self, text: str, slug_length: Optional[int] = None) -> Tuple[str, str]:
        ...

class AnonymizationStrategy(Protocol):
    """
    Protocol for different anonymization strategies (e.g., Presidio-based, fast path).
    """
    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        ...

class ConfigLoader(Protocol):
    """
    Protocol for loading configuration from external files (e.g., YAML, JSON).
    """
    def load_stoplist(self, file_path: str) -> set[str]:
        ...

class SecretManager(Protocol):
    """
    Protocol for securely retrieving secrets.
    """
    def get_secret_key(self) -> Optional[str]:
        ...
