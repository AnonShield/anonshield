import os
import sqlite3

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
DB_PATH = None # Global variable to hold the dynamic DB path

def initialize_db(mode: str = "persistent"):
    """
    Initializes the SQLite database and sets the global DB_PATH.

    Args:
        mode (str): 'persistent' (default) to save to a file,
                    'in-memory' to use a non-persistent in-memory database.
    """
    global DB_PATH
    
    if mode == "in-memory":
        DB_PATH = ":memory:"
        print("[*] Using in-memory database (data will not be saved).")
    else: # persistent
        os.makedirs(DB_DIR, exist_ok=True)
        DB_PATH = os.path.join(DB_DIR, "entities.db")

    with sqlite3.connect(DB_PATH, check_same_thread=False) as conn:
        # Performance and safety pragmas
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-10000;") # Advise 10MB cache
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



def bulk_save_to_db(entity_list):
    """Saves a list of entities to the database in a performant way."""
    if not entity_list:
        return

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        query = """
            INSERT OR IGNORE INTO entities
            (entity_type, original_name, slug_name, full_hash, first_seen, last_seen)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """
        conn.executemany(query, entity_list)
        conn.commit()

