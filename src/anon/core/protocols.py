"""
Core Architectural Protocols for the Anonymization Engine

This module defines the interfaces (via typing.Protocol) for the core components
of the system. Using protocols allows for dependency inversion and makes the system
more modular, testable, and extensible.
"""
from typing import Protocol, List, Tuple, Optional, Dict, Any

# Forward declaration for type hinting circular dependencies
class AnonymizationOrchestrator:
    """Forward declaration used for type hints; the real class lives in engine.py."""
    pass

class EntityStorage(Protocol):
    """
    Protocol for classes that handle the persistence of anonymized entities.
    """
    def initialize(self, synchronous: Optional[str] = None) -> None:
        """Initialize the storage backend (e.g. create tables, open connections)."""
        ...

    def save_entities(self, entity_list: List[Tuple]) -> None:
        """Persist a list of entity tuples to storage.

        Args:
            entity_list: Each tuple contains (entity_type, original_name,
                slug_name, full_hash) for one detected entity.
        """
        ...

    def shutdown(self) -> None:
        """Flush pending writes and close the storage backend cleanly."""
        ...

class CacheStrategy(Protocol):
    """
    Protocol for in-memory caching strategies (e.g., LRU cache).
    """
    def get(self, key: str) -> Optional[str]:
        """Return the cached value for key, or None if not present.

        Args:
            key: The original entity text used as cache key.

        Returns:
            The cached pseudonym string, or None on a cache miss.
        """
        ...

    def add(self, key: str, value: str) -> None:
        """Insert or update a key-value pair in the cache.

        Args:
            key: The original entity text.
            value: The pseudonym to store.
        """
        ...

class HashingStrategy(Protocol):
    """
    Protocol for classes that generate hashes/slugs from text.
    """
    def generate_slug(self, text: str, slug_length: Optional[int] = None) -> Tuple[str, str]:
        """Compute an HMAC-based pseudonym for the given text.

        Args:
            text: Normalized entity text to hash.
            slug_length: Number of hex characters for the display slug.
                If None, the implementation default is used.

        Returns:
            A tuple of (display_slug, full_hash) where display_slug is the
            truncated identifier shown in output and full_hash is the full
            HMAC-SHA256 hex digest stored in the database.
        """
        ...

class AnonymizationStrategy(Protocol):
    """
    Protocol for different anonymization strategies (e.g., Presidio-based, fast path).
    """
    def anonymize(self, texts: List[str], operator_params: Dict) -> Tuple[List[str], List[Tuple]]:
        """Anonymize a batch of texts.

        Args:
            texts: Raw input strings to be anonymized.
            operator_params: Configuration passed to the underlying operator
                (e.g. hash_generator, slug_length, entity_collector).

        Returns:
            A tuple of (anonymized_texts, collected_entities) where
            anonymized_texts mirrors the input list with PII replaced and
            collected_entities is a list of entity tuples for persistence.
        """
        ...

class ConfigLoader(Protocol):
    """
    Protocol for loading configuration from external files (e.g., YAML, JSON).
    """
    def load_stoplist(self, file_path: str) -> set[str]:
        """Load a set of stop-words from a configuration file.

        Args:
            file_path: Path to the stop-list file (YAML or JSON).

        Returns:
            A set of strings that should be excluded from anonymization.
        """
        ...

class SecretManager(Protocol):
    """
    Protocol for securely retrieving secrets.
    """
    def get_secret_key(self) -> Optional[str]:
        """Retrieve the HMAC secret key.

        Returns:
            The secret key string, or None if no key is configured.
        """
        ...
