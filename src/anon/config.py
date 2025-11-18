# /config.py

import os
import sqlite3
import datetime

# --- Global Configuration ---
SECRET_KEY = os.environ.get("ANON_SECRET_KEY")


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

def bulk_save_entities(db_path: str, entity_list: list) -> None:
    """Saves a batch of entities to the database in a single transaction."""
    if not entity_list:
        return

    now = datetime.datetime.now().isoformat()
    
    # --- CORREÇÃO ESTÁ AQUI ---
    # 1. Obter um CONJUNTO (set) de hashes únicos do lote.
    # O hash é o 4º item (índice 3) da tupla (entity_type, clean_text, display_hash, full_hash)
    unique_hashes_in_batch = {e[3] for e in entity_list}
    # --------------------------

    new_entities_map = {}
    existing_hashes_to_update = set()

    with sqlite3.connect(db_path, check_same_thread=False) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        # 2. Inserir apenas os hashes ÚNICOS na tabela temporária
        conn.execute("CREATE TEMPORARY TABLE temp_hashes (full_hash TEXT PRIMARY KEY)")
        conn.executemany("INSERT INTO temp_hashes (full_hash) VALUES (?)", [(h,) for h in unique_hashes_in_batch])

        # 3. Encontrar quais hashes já existem na tabela principal (isso está correto)
        cur = conn.execute("SELECT t.full_hash FROM temp_hashes t JOIN entities e ON t.full_hash = e.full_hash")
        existing_hashes_to_update = {row[0] for row in cur.fetchall()}
        
        conn.execute("DROP TABLE temp_hashes")

    # 4. Preparar os dados para inserção/atualização (isso também está correto)
    #    Usamos um dict para garantir que estamos inserindo apenas um registro por hash
    for entity in entity_list:
        full_hash = entity[3]
        if full_hash not in existing_hashes_to_update and full_hash not in new_entities_map:
            # (entity_type, original_name, slug_name, full_hash, first_seen, last_seen)
            new_entities_map[full_hash] = entity + (now, now)

    # 5. Executar as operações em lote (isso também está correto)
    if new_entities_map or existing_hashes_to_update:
        with sqlite3.connect(db_path, check_same_thread=False) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")

            if new_entities_map:
                conn.executemany(
                    """INSERT OR IGNORE INTO entities 
                       (entity_type, original_name, slug_name, full_hash, first_seen, last_seen) 
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    new_entities_map.values(),
                )

            if existing_hashes_to_update:
                # Usar outra tabela temporária para o UPDATE em lote é o mais eficiente
                conn.execute("CREATE TEMPORARY TABLE temp_update_hashes (full_hash TEXT PRIMARY KEY)")
                conn.executemany("INSERT INTO temp_update_hashes (full_hash) VALUES (?)", [(h,) for h in existing_hashes_to_update])
                
                conn.execute(
                    f"""UPDATE entities 
                        SET last_seen = '{now}' 
                        WHERE full_hash IN (SELECT full_hash FROM temp_update_hashes)"""
                )
                conn.execute("DROP TABLE temp_update_hashes")

            conn.commit()

# The database initialization is now handled in anon.py to ensure proper order of operations.