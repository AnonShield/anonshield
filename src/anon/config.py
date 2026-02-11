import os
from .security import SecretManagerImpl 
# --- Global Configuration ---
_secret_manager = SecretManagerImpl()
SECRET_KEY = _secret_manager.get_secret_key()

class Global:
    """Global constants for the application."""
    TECHNICAL_STOPLIST = {
        "http", "https", "tcp", "udp", "port", "high", "medium", "low", "critical",
        "cvss", "cve", "score", "severity", "description", "solution", "name",
        "id", "type", "true", "false", "null", "none", "n/a", "json", "xml",
        "string", "integer", "boolean", "date", "datetime", "timestamp"
    }
    
    # Non-PII entities that should be preserved by default
    # These are spaCy entity types that don't contain personally identifiable information
    NON_PII_ENTITIES = {
        "CARDINAL",  # Numerals that don't fall under other types
        "ORDINAL",   # First, second, etc.
        "QUANTITY",  # Measurements (weight, distance, etc.)
        "MONEY",     # Monetary values
        "PERCENT",   # Percentages
        "TIME",      # Times (smaller than a day)
        "LANGUAGE",  # Named languages
        "LAW",       # Named laws, documents, etc.
        "EVENT",     # Named events (wars, sports events, etc.)
        "WORK_OF_ART", # Titles of books, songs, etc.
        "PRODUCT",   # Objects, vehicles, foods, etc. (not services)
        "FAC",       # Buildings, airports, highways, etc.
    }

class ProcessingLimits:
    """Memory and throughput limits for file processing and other operations."""
    XML_MEMORY_THRESHOLD_MB = 200
    JSON_STREAM_THRESHOLD_MB = 100
    CIRCUIT_BREAKER_FAILURE_RATE = 0.20
    CIRCUIT_BREAKER_MIN_FAILURES = 5
    MAX_CACHE_SIZE = 10000
    MICRO_BATCH_SAVE_SIZE = 10000 # Save entities to DB in micro-batches of this size

class DefaultSizes:
    """Default chunk and batch sizes for processing."""
    BATCH_SIZE = 1000
    CSV_CHUNK_SIZE = 1000
    JSON_CHUNK_SIZE = 1000
    NER_CHUNK_SIZE = 1500
    NLP_BATCH_SIZE = 500
    SLM_MAPPER_CHUNK_SIZE = 1500
    SLM_ANONYMIZER_CHUNK_SIZE = 1500  # Max chars per chunk for SLM anonymization
    DEFAULT_SLUG_LENGTH = 64
    DEFAULT_MIN_WORD_LENGTH = 0
    DEFAULT_SLM_CONFIDENCE_THRESHOLD = 0.7
    DEFAULT_SLM_CONTEXT_WINDOW = 50

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

# Entity mappings for SecureModernBERT-NER (cybersecurity-focused entities)
SECURE_MODERNBERT_ENTITY_MAPPING = {
    # People and Organizations
    "ORG": "ORGANIZATION",
    "LOC": "LOCATION", 
    "EMAIL": "EMAIL_ADDRESS",
    
    # Technical Indicators
    "URL": "URL",
    "IPV4": "IP_ADDRESS",
    "IPV6": "IP_ADDRESS", 
    "DOMAIN": "HOSTNAME",
    "MD5": "HASH",
    "SHA1": "HASH",
    "SHA256": "HASH",
    "FILEPATH": "FILE_PATH",
    # Handle both variants from model
    "REGISTRY-KEYS": "REGISTRY_KEY",
    "THREAT-ACTOR": "THREAT_ACTOR",
    # Cybersecurity Entities (keep as-is)
    "MALWARE": "MALWARE",
    "CVE": "CVE_ID",
    "PLATFORM": "PLATFORM",
    "PRODUCT": "PRODUCT",
    "SECTOR": "SECTOR", 
    "TOOL": "TOOL",
    "CAMPAIGN": "CAMPAIGN",
    "MITRE_TACTIC": "MITRE_TACTIC",
    "SERVICE": "SERVICE",
}

# --- LLM Configuration ---
LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "ollama"), # Prepares for future providers
    "ollama": {
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        "model": os.getenv("OLLAMA_MODEL", "llama3"),
        "timeout": 120,
        "temperature": 0.05, # Lower temp for more deterministic output
    }
}
