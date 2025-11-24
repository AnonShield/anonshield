import logging
import os
import queue
import threading
import sqlite3
import json
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
    Encapsulates the database state, including the repository, write queue, and writer thread.
    This class manages the lifecycle of the database connection and related components.
    """
    def __init__(self, mode: str = "persistent", db_dir: str = "db"):
        self.mode = mode
        self.db_dir = db_dir
        self.db_path: Optional[str] = None
        self.repository: Optional[EntityRepository] = None
        self.write_queue = queue.Queue()
        self.writer_thread: Optional[threading.Thread] = None
        self.is_initialized = False

    def initialize(self, synchronous: Optional[str] = None):
        """Initializes the repository, schema, and starts the background writer thread."""
        if self.is_initialized:
            logging.warning("DatabaseContext is already initialized.")
            return

        if self.mode == "in-memory":
            self.db_path = ":memory:"
            logging.debug(f"DB_PATH set to: {self.db_path} (in-memory mode).")
        else: # persistent
            os.makedirs(self.db_dir, exist_ok=True)
            self.db_path = os.path.join(self.db_dir, "entities.db")
            logging.debug(f"DB_PATH set to: {self.db_path} (persistent mode).")

        self.repository = EntityRepository(self.db_path)
        
        sync_mode = synchronous.upper() if synchronous else "NORMAL"
        self.repository.initialize_schema(synchronous=sync_mode)

        if not self.writer_thread or not self.writer_thread.is_alive():
            self.writer_thread = threading.Thread(target=self._writer_thread_target, daemon=True)
            self.writer_thread.start()
            logging.info("DB writer thread started.")
        
        self.is_initialized = True
        logging.info("DatabaseContext initialized.")

    def shutdown(self):
        """Signals the writer thread to shut down and cleans up resources."""
        if not self.is_initialized:
            return
            
        logging.info("Shutting down DatabaseContext.")
        self.write_queue.put(None)  # Sentinel to stop the writer thread
        
        if self.writer_thread:
            self.writer_thread.join(timeout=10)
            if self.writer_thread.is_alive():
                logging.warning("DB writer thread did not shut down in time.")
            self.writer_thread = None
        
        if not self.write_queue.empty():
            logging.info("Waiting for %d final items in DB queue to be processed...", self.write_queue.qsize())
            self.write_queue.join()

        if self.repository:
            self.repository.close_thread_connection()
            self.repository = None
            
        self.is_initialized = False
        logging.info("DatabaseContext shut down.")

    def save_entities(self, entity_list: List[Tuple]):
        """Puts a list of entities into the thread-safe queue to be saved."""
        if not entity_list:
            return
        logging.debug(f"Adding {len(entity_list)} entities to DB write queue.")
        self.write_queue.put(entity_list)

    def _writer_thread_target(self):
        """The target function for the background database writer thread."""
        if not self.repository:
            logging.critical("Repository not initialized. DB writer thread cannot start.")
            return

        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(sqlite3.OperationalError),
            before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING, exc_info=True)
        )
        def _attempt_save_batch(entities):
            self.repository.save_batch(entities)

        while True:
            try:
                # Wait for items to appear in the queue
                entity_list = self.write_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                if entity_list is None:  # The shutdown sentinel
                    logging.info("DB writer thread received shutdown signal.")
                    break
                
                _attempt_save_batch(entity_list)

            except sqlite3.OperationalError as e:
                logging.critical(f"Failed to save entity batch after multiple retries due to database locked: {e}. "
                                 f"Logging to dead_letter.log for manual recovery.")
                self._log_to_dead_letter(entity_list)
            except Exception as e:
                logging.error(f"DB Writer thread encountered an unhandled error: {e}", exc_info=True)
            finally:
                self.write_queue.task_done()
        
        if self.repository:
            self.repository.close_thread_connection()
        logging.info("DB writer thread finished.")

    def _log_to_dead_letter(self, entity_list: List[Tuple]):
        """Logs a failed batch of entities to a dead-letter file."""
        dead_letter_path = os.path.join("logs", "dead_letter.log")
        os.makedirs("logs", exist_ok=True)
        with open(dead_letter_path, "a", encoding="utf-8") as f:
            for entity in entity_list:
                try:
                    f.write(json.dumps(entity) + "\n")
                except TypeError:
                    # Fallback for entities that are not JSON serializable (e.g. tuples)
                    f.write(str(entity) + "\n")
        logging.info(f"{len(entity_list)} entities logged to dead-letter file: {dead_letter_path}")

