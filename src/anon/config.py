import os

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
