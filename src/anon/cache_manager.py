import logging
from collections import OrderedDict
from typing import Optional
import threading # Added for RLock

class CacheManager:
    """
    Manages an in-memory Least Recently Used (LRU) cache for anonymization results.
    It is thread-safe using an RLock.
    """
    def __init__(self, use_cache: bool, max_cache_size: int):
        self.use_cache = use_cache
        self.max_cache_size = max_cache_size
        self.cache: OrderedDict[str, str] = OrderedDict()
        self._lock = threading.RLock() # Added RLock for thread-safety
        logging.debug(f"CacheManager initialized with use_cache={use_cache}, max_cache_size={max_cache_size}.")

    def get(self, key: str) -> Optional[str]:
        """Retrieves an item from the cache, moving it to the front (most recently used)."""
        if not self.use_cache:
            return None
        with self._lock: # Protect critical section
            if key in self.cache:
                value = self.cache.pop(key) # Remove and re-insert to mark as recently used
                self.cache[key] = value
                logging.debug(f"Cache hit for key: '{key}'")
                return value
        logging.debug(f"Cache miss for key: '{key}'")
        return None

    def add(self, key: str, value: str):
        """Adds an item to the cache, implementing LRU eviction if size limit is exceeded."""
        if not self.use_cache:
            return
        with self._lock: # Protect critical section
            if key in self.cache:
                self.cache.pop(key) # Update value and mark as recently used
                logging.debug(f"Updating cache for existing key: '{key}'")
            elif len(self.cache) >= self.max_cache_size:
                lru_key = self.cache.popitem(last=False)[0] # Remove LRU item
                logging.debug(f"Cache full (max size {self.max_cache_size}), evicting LRU item: '{lru_key}' to add key: '{key}'")
            else:
                logging.debug(f"Adding new item to cache for key: '{key}'")
            self.cache[key] = value
