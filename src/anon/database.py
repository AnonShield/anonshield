import logging
import os
import queue
import threading
import sqlite3
import orjson
from typing import Optional, List, Tuple

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .repository import EntityRepository

class DatabaseContext:
    """
    Encapsulates the database state, including the repository.
    This version is simplified to be synchronous for debugging purposes.
    """
    def __init__(self, mode: str = "persistent", db_dir: str = "db"):
        self.mode = mode
        self.db_dir = db_dir
        self.db_path: Optional[str] = None
        self.repository: Optional[EntityRepository] = None
        self.is_initialized = False

    def initialize(self, synchronous: Optional[str] = None):
        """Initializes the repository and schema."""
        if self.is_initialized:
            return

        if self.mode == "in-memory":
            self.db_path = ":memory:"
        else:
            os.makedirs(self.db_dir, exist_ok=True)
            self.db_path = os.path.join(self.db_dir, "entities.db")

        self.repository = EntityRepository(self.db_path)
        sync_mode = synchronous.upper() if synchronous else "NORMAL"
        self.repository.initialize_schema(synchronous=sync_mode)
        
        self.is_initialized = True
        logging.info("DatabaseContext initialized in synchronous mode.")

    def shutdown(self):
        """Shuts down the repository connection."""
        if not self.is_initialized:
            return
        
        if self.repository:
            self.repository.close_thread_connection()

        self.is_initialized = False
        logging.info("DatabaseContext shutdown complete.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(sqlite3.OperationalError),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING, exc_info=True)
    )
    def save_entities(self, entity_list: List[Tuple]):
        """Saves a list of entities directly to the database."""
        if not self.is_initialized or not self.repository:
            logging.error("Database not initialized, cannot save entities.")
            return

        if not entity_list:
            return
            
        try:
            self.repository.save_batch(entity_list)
        except Exception as e:
            logging.error(f"Failed to save batch directly: {e}", exc_info=True)
            self._log_to_dead_letter(entity_list)

    def _log_to_dead_letter(self, entity_list: List[Tuple]):
        """Logs a failed batch of entities to a dead-letter file."""
        if not entity_list:
            return
        dead_letter_path = os.path.join("logs", "dead_letter.log")
        os.makedirs("logs", exist_ok=True)
        try:
            with open(dead_letter_path, "ab") as f:
                for entity in entity_list:
                    f.write(orjson.dumps(entity, option=orjson.OPT_APPEND_NEWLINE))
        except Exception as e:
            logging.error(f"Could not write to dead-letter log '{dead_letter_path}': {e}", exc_info=True)
