import logging
import os
import queue
import threading
import sqlite3
import orjson # Added orjson
import time # Added time for sleep in flush
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
        self._shutdown_flag = threading.Event() # Event to signal thread to stop

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
            self._shutdown_flag.clear() # Ensure flag is clear on re-initialization
            self.writer_thread = threading.Thread(target=self._writer_thread_target, daemon=True)
            self.writer_thread.start()
            logging.info("DB writer thread started.")
        
        self.is_initialized = True
        logging.info("DatabaseContext initialized.")

    def shutdown(self):
        """Signals the writer thread to shut down, ensures all items are processed/logged, and cleans up resources."""
        if not self.is_initialized:
            logging.info("DatabaseContext not initialized, skipping shutdown.")
            return

        logging.info("Shutting down DatabaseContext. Signaling writer thread to stop...")
        # 1. Send sentinel to the queue to signal the writer thread to stop processing new items.
        self.write_queue.put(None)

        # 2. Wait for the writer thread to finish its current work.
        if self.writer_thread:
            self.writer_thread.join(timeout=30)  # Give the thread 30 seconds to finish.
            if self.writer_thread.is_alive():
                logging.critical("DB writer thread did not shut down gracefully in 30s. There might be unprocessed items.")
            self.writer_thread = None

        # 3. After the thread has terminated, handle any items that might be left in the queue.
        # This can happen if the thread died unexpectedly or timed out.
        if not self.write_queue.empty():
            logging.warning("Queue is not empty after writer thread shutdown. Flushing remaining items to dead-letter log.")
            self._flush_queue_to_dead_letter()

        # 4. Close the repository connection.
        if self.repository:
            self.repository.close_thread_connection()
            self.repository = None

        self.is_initialized = False
        logging.info("DatabaseContext shutdown complete.")

    def save_entities(self, entity_list: List[Tuple]):
        """Puts a list of entities into the thread-safe queue to be saved."""
        if not entity_list:
            return
        if not self.is_initialized or (self.writer_thread and not self.writer_thread.is_alive()):
            logging.warning("Database context is shutting down or writer thread is dead. Skipping save for %d entities.", len(entity_list))
            self._log_to_dead_letter(entity_list)
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
                entity_list = self.write_queue.get()

                # The sentinel value (None) signals the thread to exit.
                if entity_list is None:
                    logging.info("DB writer thread received shutdown sentinel. Exiting gracefully.")
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

        logging.info("DB writer thread finished.")

    def _flush_queue_to_dead_letter(self):
        """
        Flushes all remaining items in the write queue to the dead-letter log.
        Called when the writer thread fails to shut down gracefully or on final shutdown.
        """
        logging.warning("Flushing remaining queue items to dead-letter log.")
        while not self.write_queue.empty():
            try:
                entity_list = self.write_queue.get_nowait()
                if entity_list is None:  # Skip any lingering sentinels
                    self.write_queue.task_done()
                    continue
                self._log_to_dead_letter(entity_list)
            except queue.Empty:
                break  # The queue is empty
            except Exception as e:
                logging.error(f"Error during dead-letter flush: {e}", exc_info=True)
            finally:
                if 'entity_list' in locals(): # Ensure task_done is called even on error
                    self.write_queue.task_done()
        logging.info("Finished flushing queue to dead-letter log.")

    def _log_to_dead_letter(self, entity_list: List[Tuple]):
        """Logs a failed batch of entities to a dead-letter file, using orjson."""
        if not entity_list:
            return
        dead_letter_path = os.path.join("logs", "dead_letter.log")
        os.makedirs("logs", exist_ok=True)
        logging.info(f"Logging {len(entity_list)} entities to dead-letter file: {dead_letter_path}")
        try:
            # Use 'ab' mode to append bytes to the log file.
            with open(dead_letter_path, "ab") as f:
                for entity in entity_list:
                    # orjson.dumps returns bytes, so we write directly.
                    # Add OPT_APPEND_NEWLINE to ensure each JSON object is on a new line.
                    f.write(orjson.dumps(entity, option=orjson.OPT_APPEND_NEWLINE))
        except Exception as e:
            logging.error(f"Could not write to dead-letter log '{dead_letter_path}': {e}", exc_info=True)


