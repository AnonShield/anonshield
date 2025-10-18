# /config.py

import os
import sqlite3
import datetime

# --- Global Configuration ---
SECRET_KEY = os.environ.get("ANON_SECRET_KEY")
DEFAULT_ALLOW_LIST = ["TCP", "UDP", "HTTP", "HTTPS", "admin", "localhost"]

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
DB_PATH = os.path.join(DB_DIR, "entities.db")

def initialize_db():
    """Initializes the SQLite database and creates the entities table if it doesn't exist."""
    os.makedirs(DB_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=10000;")
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
    return DB_PATH

def save_entity(db_path: str, entity_type: str, original_name: str, slug_name: str, full_hash: str) -> None:
    """Saves or updates an entity in the database."""
    now = datetime.datetime.now().isoformat()
    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        cur = conn.execute("SELECT id FROM entities WHERE full_hash=?", (full_hash,))
        row = cur.fetchone()
        
        if row:
            conn.execute("UPDATE entities SET last_seen=? WHERE id=?", (now, row[0]))
        else:
            conn.execute(
                """INSERT OR IGNORE INTO entities 
                   (entity_type, original_name, slug_name, full_hash, first_seen, last_seen) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (entity_type, original_name.strip(), slug_name, full_hash, now, now),
            )
        conn.commit()

# Initialize the database when the config is loaded
initialize_db()