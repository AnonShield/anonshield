import logging
import os
import queue
import threading
from typing import Optional

from .repository import EntityRepository

# --- Global Configuration ---
SECRET_KEY = os.environ.get("ANON_SECRET_KEY")
TECHNICAL_STOPLIST = {
    "http", "https", "tcp", "udp", "port", "high", "medium", "low", "critical",
    "cvss", "cve", "score", "severity", "description", "solution", "name",
    "id", "type", "true", "false", "null", "none", "n/a", "json", "xml",
    "string", "integer", "boolean", "date", "datetime", "timestamp"
}

# --- Model Configuration ---
TRANSFORMER_MODEL = "Davlan/xlm-roberta-base-ner-hrl"
MODELS_DIR = "models"
TRF_MODEL_PATH = os.path.join(MODELS_DIR, TRANSFORMER_MODEL)

# Entity mappings between the transformer model's labels and Presidio's entities
ENTITY_MAPPING = dict(
    LOC="LOCATION",
    ORG="ORGANIZATION",
    PER="PERSON",
    EMAIL="EMAIL_ADDRESS",
    PHONE="PHONE_NUMBER",
    PERSON="PERSON",
    LOCATION="LOCATION",
    GPE="LOCATION",
    ORGANIZATION="ORGANIZATION",
)

# --- Database Configuration & State ---
DB_DIR = os.path.join(os.getcwd(), "db")
DB_PATH: Optional[str] = None
DB_WRITE_QUEUE = queue.Queue()
DB_WRITER_THREAD: Optional[threading.Thread] = None
ENTITY_REPOSITORY: Optional[EntityRepository] = None

def _db_writer():
    """
    A dedicated thread that consumes entities from a queue and uses the repository to save them.
    This is the only thread that performs database writes.
    """
    if not ENTITY_REPOSITORY:
        logging.critical("Repository not initialized. DB writer thread cannot start.")
        return

    while True:
        try:
            entity_list = DB_WRITE_QUEUE.get(timeout=0.5)
        except queue.Empty:
            continue

        try:
            if entity_list is None:  # Sentinel for shutdown
                logging.info("DB writer thread received shutdown signal.")
                break

            ENTITY_REPOSITORY.save_batch(entity_list)

        except Exception as e:
            # The repository handles its own logging, but we log here too for thread context
            logging.error(f"DB Writer thread encountered an unhandled error: {e}", exc_info=True)
        finally:
            DB_WRITE_QUEUE.task_done()

    logging.info("DB writer thread finished.")

def initialize_db(mode: str = "persistent", synchronous: Optional[str] = None):
    """
    Initializes the database repository, schema, and starts the writer thread.
    """
    global DB_PATH, ENTITY_REPOSITORY, DB_WRITER_THREAD
    
    if mode == "in-memory":
        DB_PATH = ":memory:"
    else: # persistent
        os.makedirs(DB_DIR, exist_ok=True)
        DB_PATH = os.path.join(DB_DIR, "entities.db")

    # 1. Initialize the repository
    ENTITY_REPOSITORY = EntityRepository(DB_PATH)
    
    # 2. Set up the database schema
    sync_mode = synchronous.upper() if synchronous else "NORMAL"
    ENTITY_REPOSITORY.initialize_schema(synchronous=sync_mode)

    # 3. Start the writer thread if it's not already running
    if not DB_WRITER_THREAD or not DB_WRITER_THREAD.is_alive():
        DB_WRITER_THREAD = threading.Thread(target=_db_writer, daemon=True)
        DB_WRITER_THREAD.start()
        logging.info("DB writer thread started.")

    return DB_PATH

def shutdown_db_writer():
    """
    Signals the database writer thread to shut down gracefully and closes the repository.
    """
    global DB_WRITER_THREAD, ENTITY_REPOSITORY
    
    # Signal the thread to stop
    DB_WRITE_QUEUE.put(None)
    
    if DB_WRITER_THREAD:
        logging.info("Waiting for DB writer thread to finish...")
        DB_WRITER_THREAD.join(timeout=10)
        if DB_WRITER_THREAD.is_alive():
            logging.warning("DB writer thread did not shut down in time.")
        DB_WRITER_THREAD = None
    
    # Wait for all items in the queue to be processed
    if not DB_WRITE_QUEUE.empty():
        logging.info("Waiting for %d final items in DB queue to be processed...", DB_WRITE_QUEUE.qsize())
        DB_WRITE_QUEUE.join()

    # Close the repository connection
    if ENTITY_REPOSITORY:
        ENTITY_REPOSITORY.close()
        ENTITY_REPOSITORY = None

def bulk_save_to_db(entity_list):
    """Puts a list of entities into the thread-safe queue to be saved by the writer thread."""
    if not entity_list:
        return
    DB_WRITE_QUEUE.put(entity_list)
