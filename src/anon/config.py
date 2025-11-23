import logging
import os
import sqlite3
from typing import Optional
import queue
import sys
import threading
import time

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

# --- Database Configuration ---
DB_DIR = os.path.join(os.getcwd(), "db")
DB_PATH = None  # Global variable to hold the dynamic DB path
DB_SYNC_MODE = "NORMAL"  # Global variable to hold the synchronous mode
DB_WRITE_QUEUE = queue.Queue()
DB_WRITER_THREAD = None
DB_CONNECTION = None
DB_LOCK = threading.Lock()

def _db_writer():
    """A dedicated thread to write entities to the database from a queue."""
    # This connection is local to the thread
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(f"PRAGMA synchronous={DB_SYNC_MODE};")

    while True:
        try:
            entity_list = DB_WRITE_QUEUE.get(timeout=0.5)
        except queue.Empty:
            continue  # Go back to waiting for an item

        try:
            if entity_list is None:  # Sentinel for shutdown
                break  # Exit loop

            conn.executemany(
                """
                INSERT OR IGNORE INTO entities
                (entity_type, original_name, slug_name, full_hash, first_seen, last_seen)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                entity_list
            )
            conn.commit()
            logging.info("%d entities written to database.", len(entity_list))

        except Exception as e:
            logging.error(f"DB Writer thread error processing batch: {e}", exc_info=True)
        finally:
            DB_WRITE_QUEUE.task_done()  # Crucial: always mark task as done

    conn.close()
    logging.info("DB writer thread finished.")


def initialize_db(mode: str = "persistent", synchronous: Optional[str] = None):
    """
    Initializes the SQLite database, sets the global DB_PATH, and starts the writer thread.
    """
    global DB_PATH, DB_SYNC_MODE, DB_WRITER_THREAD
    
    if mode == "in-memory":
        DB_PATH = ":memory:"
        logging.info("Using in-memory database (data will not be saved).")
    else: # persistent
        os.makedirs(DB_DIR, exist_ok=True)
        DB_PATH = os.path.join(DB_DIR, "entities.db")

    # Create a temporary connection just to initialize the schema
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        
        sync_mode = synchronous.upper() if synchronous else "NORMAL"
        DB_SYNC_MODE = sync_mode
        conn.execute(f"PRAGMA synchronous={DB_SYNC_MODE};")
        logging.info(f"SQLite synchronous mode set to: {DB_SYNC_MODE}")

        conn.execute("PRAGMA cache_size=-10000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                original_name TEXT NOT NULL,
                slug_name TEXT NOT NULL,
                full_hash TEXT NOT NULL UNIQUE,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_full_hash ON entities(full_hash);")
        conn.commit()

    if not DB_WRITER_THREAD or not DB_WRITER_THREAD.is_alive():
        DB_WRITER_THREAD = threading.Thread(target=_db_writer, daemon=True)
        DB_WRITER_THREAD.start()

    return DB_PATH

def shutdown_db_writer():
    """Signals the database writer thread to shut down gracefully."""
    global DB_WRITER_THREAD
    
    if not DB_WRITE_QUEUE.empty():
        logging.info("Waiting for %d items in DB queue to be written...", DB_WRITE_QUEUE.qsize())
        DB_WRITE_QUEUE.join()

    DB_WRITE_QUEUE.put(None)
    if DB_WRITER_THREAD:
        DB_WRITER_THREAD.join(timeout=10)
        if DB_WRITER_THREAD.is_alive():
            logging.warning("DB writer thread did not shut down in time.")
        DB_WRITER_THREAD = None

def bulk_save_to_db(entity_list):
    """Puts a list of entities into the thread-safe queue to be saved."""
    if not entity_list:
        return
    DB_WRITE_QUEUE.put(entity_list)