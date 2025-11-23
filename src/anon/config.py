# /config.py

import os
import sqlite3
import datetime

# --- Global Configuration ---
SECRET_KEY = os.environ.get("ANON_SECRET_KEY")


# 1. APONTE PARA A PASTA DO SEU MODELO TREINADO
# Se o script 'train_ner.py' salvou na pasta "meu_modelo_v1" na raiz:
TRANSFORMER_MODEL = "./meu_modelo_v1" 

# Ou, se você moveu a pasta "meu_modelo_v1" para dentro de "models/":
#TRANSFORMER_MODEL = "meu_modelo_v1" 

MODELS_DIR = "models"

# Se for caminho relativo (./), ele usa direto, senão tenta achar em models/
if os.path.exists(TRANSFORMER_MODEL):
    TRF_MODEL_PATH = TRANSFORMER_MODEL



ENTITY_MAPPING = dict(
    # --- NOVAS ENTIDADES (Obrigatório) ---
    # A chave (Esquerda) deve ser IGUAL à label do Doccano
    HOSTNAME="HOSTNAME",
    IP_ADDRESS="IP_ADDRESS",
    CLOUD_ID="CLOUD_ID",
    CONTAINER_IMG="CONTAINER_IMG",
    MAC_ADDRESS="MAC_ADDRESS",
    ASSET_ROLE="ASSET_ROLE",
    ASSET_TYPE="ASSET_TYPE",
    ENVIRONMENT="ENVIRONMENT",
    LOCATION="LOCATION",
    ORGANIZATION="ORGANIZATION",
    OS_NAME="OS_NAME",
    SENSITIVE_TAG="SENSITIVE_TAG",
    
    # --- LEGADO/PADRÃO (Não remova) ---
    PER="PERSON",
    PERSON="PERSON",
    LOC="LOCATION",
    ORG="ORGANIZATION",
    EMAIL="EMAIL_ADDRESS",
    PHONE="PHONE_NUMBER"
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
