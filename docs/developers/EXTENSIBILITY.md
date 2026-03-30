# AnonShield Extensibility Guide

This guide documents every extension point in AnonShield. Each section covers one interface or mechanism: what it does, exactly what must be implemented, how to register the extension, and a worked example.

---

## Table of Contents

1. [Extension Points Overview](#1-extension-points-overview)
2. [Anonymization Strategies](#2-anonymization-strategies)
3. [File Processors](#3-file-processors)
4. [Entity Types and Regex Patterns](#4-entity-types-and-regex-patterns)
5. [Transformer Models](#5-transformer-models)
6. [Cache Backend](#6-cache-backend)
7. [Hashing / Pseudonym Generation](#7-hashing--pseudonym-generation)
8. [Entity Storage](#8-entity-storage)
9. [Secret Manager](#9-secret-manager)
10. [Entity Detector](#10-entity-detector)
11. [SLM Client](#11-slm-client)
12. [SLM Prompts](#12-slm-prompts)
13. [Model Provider](#13-model-provider)
14. [Dependency Injection Reference](#14-dependency-injection-reference)

---

## 1. Extension Points Overview

AnonShield is designed around three complementary patterns:

- **Strategy pattern** — anonymization algorithms are interchangeable (`AnonymizationStrategy`).
- **Template Method pattern** — file-format handling uses a shared pipeline with format-specific hooks (`FileProcessor`).
- **Protocol-based dependency inversion** — core services (cache, hash, storage, secrets) are interfaces defined in [`src/anon/core/protocols.py`](../../src/anon/core/protocols.py), injected into the orchestrator at construction time.

| Extension Point | Interface / Base | Location | How to register |
|---|---|---|---|
| Anonymization strategy | `AnonymizationStrategy` (ABC) | `src/anon/strategies.py` | Add case to `strategy_factory()` + CLI choice |
| File format processor | `FileProcessor` (ABC) | `src/anon/processors.py` | `ProcessorRegistry.register()` |
| Entity storage backend | `EntityStorage` (Protocol) | `src/anon/core/protocols.py` | Pass to `AnonymizationOrchestrator.__init__()` |
| Cache backend | `CacheStrategy` (Protocol) | `src/anon/core/protocols.py` | Pass to `AnonymizationOrchestrator.__init__()` |
| Hashing strategy | `HashingStrategy` (Protocol) | `src/anon/core/protocols.py` | Pass to `AnonymizationOrchestrator.__init__()` |
| Secret manager | `SecretManager` (Protocol) | `src/anon/core/protocols.py` | Swap `SecretManagerImpl` at construction |
| Entity detector | `EntityDetector` (class) | `src/anon/entity_detector.py` | Pass to `AnonymizationOrchestrator.__init__()` |
| SLM client | `SLMClient` (Protocol) | `src/anon/slm/client.py` | Pass to `SLMEntityDetector` / `SLMFullAnonymizer` |
| SLM prompts | `PromptManager` (class) | `src/anon/slm/prompts.py` | Pass to SLM detectors/anonymizers |
| Model provider | `ModelProvider` (Protocol) | `src/anon/model_manager.py` | `ModelManager.register_provider()` |
| Regex patterns | `RegexPatterns` (class) | `src/anon/engine.py` | Add attribute + entry in `load_custom_recognizers()` |
| Entity type mapping | `ENTITY_MAPPING` dict | `src/anon/config.py` | Add key-value pair |
| Transformer model | string identifier | `--transformer-model` CLI flag | Add mapping in `_setup_engines()` |

---

## 2. Anonymization Strategies

**Files:** `src/anon/strategies.py`, `src/anon/standalone_strategy.py`

### 2.1 Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

class AnonymizationStrategy(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def anonymize(
        self,
        texts: List[str],
        operator_params: Dict,
    ) -> Tuple[List[str], List[Tuple]]:
        """
        Anonymize a batch of texts.

        Args:
            texts:           List of raw input strings.
            operator_params: Presidio operator configuration dict.

        Returns:
            Tuple of:
              - List[str]   — anonymized texts, same length as input.
              - List[Tuple] — collected entity records:
                              (entity_type, original_text, display_hash, full_hash)
        """
        ...
```

### 2.2 Built-in implementations

| Class | File | Description |
|---|---|---|
| `FullPresidioStrategy` | `strategies.py` | Full Presidio pipeline with all recognizers |
| `FilteredPresidioStrategy` | `strategies.py` | Presidio with a curated entity scope (recommended) |
| `HybridPresidioStrategy` | `strategies.py` | Presidio detection + custom replacement logic |
| `StandaloneStrategy` | `standalone_strategy.py` | Zero Presidio dependencies; GPU-optimised NER |

### 2.3 Registration

Strategies are instantiated by `strategy_factory()` in `src/anon/engine.py`:

```python
def strategy_factory(strategy_name: str, **kwargs) -> AnonymizationStrategy:
    match strategy_name:
        case "presidio":
            return FullPresidioStrategy(...)
        case "filtered":
            return FilteredPresidioStrategy(...)
        case "hybrid":
            return HybridPresidioStrategy(...)
        case "standalone":
            return StandaloneStrategy(...)
        case _:
            raise ValueError(f"Unknown strategy: {strategy_name}")
```

To add a new strategy:

1. Create a class that inherits `AnonymizationStrategy` and implements `anonymize()`.
2. Add a `case "my_strategy":` branch in `strategy_factory()`.
3. Add `"my_strategy"` to the `--anonymization-strategy` choices in `anon.py`.

### 2.4 Example: keyword-replacement strategy

```python
class KeywordRedactStrategy(AnonymizationStrategy):
    """Replaces a fixed set of keywords with [REDACTED]."""

    def __init__(self, keywords: list[str], hash_generator, cache_manager, **kwargs):
        super().__init__()
        self.keywords = keywords
        self.hash_generator = hash_generator
        self.cache_manager = cache_manager

    def anonymize(
        self,
        texts: List[str],
        operator_params: Dict,
    ) -> Tuple[List[str], List[Tuple]]:
        results, entities = [], []
        for text in texts:
            for kw in self.keywords:
                if kw in text:
                    slug, full = self.hash_generator.generate_slug(kw)
                    text = text.replace(kw, f"[KEYWORD_{slug}]")
                    entities.append(("KEYWORD", kw, slug, full))
            results.append(text)
        return results, entities
```

---

## 3. File Processors

**File:** `src/anon/processors.py`

### 3.1 Interface

```python
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Dict, Union

class FileProcessor(ABC):
    def __init__(
        self,
        file_path: str,
        orchestrator: AnonymizationOrchestrator,
        *,
        ner_data_generation: bool = False,
        ner_include_all: bool = False,
        ner_aggregate_record: bool = False,
        anonymization_config: Optional[Dict] = None,
        min_word_length: int = DefaultSizes.DEFAULT_MIN_WORD_LENGTH,
        skip_numeric: bool = False,
        output_dir: str = "output",
        overwrite: bool = False,
        disable_gc: bool = False,
        json_stream_threshold_mb: int = ProcessingLimits.JSON_STREAM_THRESHOLD_MB,
        preserve_row_context: bool = False,
        batch_size: Union[int, str] = DefaultSizes.BATCH_SIZE,
        csv_chunk_size: int = DefaultSizes.CSV_CHUNK_SIZE,
        json_chunk_size: int = DefaultSizes.JSON_CHUNK_SIZE,
        ner_chunk_size: int = DefaultSizes.NER_CHUNK_SIZE,
        force_large_xml: bool = False,
        use_datasets: bool = False,
    ):
        ...  # stores all parameters as instance attributes

    @abstractmethod
    def _extract_texts(self) -> Iterable[str]:
        """Yield text strings from the input file, one logical unit at a time."""
        ...

    @abstractmethod
    def _get_output_extension(self) -> str:
        """Return the file extension for the anonymized output, e.g. '.txt'."""
        ...
```

The public `process()` method is implemented in the base class and orchestrates the full pipeline (GC management → text extraction → NER/anonymization → output writing). Subclasses only need to implement `_extract_texts()` and `_get_output_extension()`.

Optional hooks (override only when needed):

```python
def _extract_texts_for_ner(self) -> Iterable[str]:
    """Yield texts for NER data generation mode (defaults to _extract_texts)."""
    return self._extract_texts()

def _write_output(self, anonymized_texts: List[str]) -> str:
    """Write anonymized texts to the output file. Returns output path."""
    ...
```

### 3.2 Registration

```python
# At module level, after the class definition:
ProcessorRegistry.register([".myext", ".myext2"], MyFileProcessor)
```

`ProcessorRegistry.get_processor()` resolves the processor by file extension (case-insensitive) and passes all keyword arguments through to the constructor.

### 3.3 Built-in registrations

| Class | Extensions |
|---|---|
| `TextFileProcessor` | `.txt`, `.log` |
| `PdfFileProcessor` | `.pdf` |
| `DocxFileProcessor` | `.docx` |
| `CsvFileProcessor` | `.csv` |
| `XlsxFileProcessor` | `.xlsx` |
| `XmlFileProcessor` | `.xml` |
| `JsonFileProcessor` | `.json`, `.jsonl` |
| `ImageFileProcessor` | `.jpeg`, `.jpg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp`, `.jp2`, `.pnm` |

### 3.4 Example: YAML processor

```python
import yaml
from src.anon.processors import FileProcessor, ProcessorRegistry

class YamlFileProcessor(FileProcessor):
    def _extract_texts(self):
        with open(self.file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Flatten all string values for anonymization
        yield from self._walk_strings(data)

    def _get_output_extension(self) -> str:
        return ".yaml"

    def _walk_strings(self, node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for v in node.values():
                yield from self._walk_strings(v)
        elif isinstance(node, list):
            for item in node:
                yield from self._walk_strings(item)

ProcessorRegistry.register([".yaml", ".yml"], YamlFileProcessor)
```

---

## 4. Entity Types and Regex Patterns

**Files:** `src/anon/config.py`, `src/anon/engine.py`

### 4.1 Entity type mappings

Entity labels emitted by the transformer or spaCy are normalised through mapping dictionaries before reaching Presidio.

**Default mapping** (`config.py` → `ENTITY_MAPPING`):

```python
ENTITY_MAPPING = {
    "LOC": "LOCATION",
    "ORG": "ORGANIZATION",
    "PER": "PERSON",
    "EMAIL": "EMAIL_ADDRESS",
    "PHONE": "PHONE_NUMBER",
    "GPE": "LOCATION",
    ...
}
```

**SecureModernBERT mapping** (`config.py` → `SECURE_MODERNBERT_ENTITY_MAPPING`):

```python
SECURE_MODERNBERT_ENTITY_MAPPING = {
    "IPV4": "IP_ADDRESS",
    "IPV6": "IP_ADDRESS",
    "DOMAIN": "HOSTNAME",
    "MD5": "HASH",
    "SHA256": "HASH",
    "FILEPATH": "FILE_PATH",
    "REGISTRY-KEYS": "REGISTRY_KEY",
    "THREAT-ACTOR": "THREAT_ACTOR",
    "MALWARE": "MALWARE",
    "CVE": "CVE_ID",
    "PLATFORM": "PLATFORM",
    "TOOL": "TOOL",
    "CAMPAIGN": "CAMPAIGN",
    "MITRE_TACTIC": "MITRE_TACTIC",
    "SERVICE": "SERVICE",
    ...
}
```

To add a new entity type: add the label→canonical-name pair to the appropriate mapping dict and add a corresponding regex recognizer (see below).

### 4.2 Regex patterns

All patterns live as class attributes of `RegexPatterns` in `src/anon/engine.py`:

```python
class RegexPatterns:
    # Network
    URL          = r"(?:https?://|ftp://|www\.)\S+?..."
    IPV4         = r"\b(?:25[0-5]|...)..."
    IPV6         = r"(?:[0-9a-fA-F]{1,4}:){7}..."
    MAC_ADDRESS  = r"\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b"
    PORT         = r"\b\d{1,5}/(?:tcp|udp|sctp)\b"

    # Hashes (ordered by specificity)
    SHA512 = r"\b[0-9a-fA-F]{128}\b"
    SHA256 = r"\b[0-9a-fA-F]{64}\b(?![0-9a-fA-F])"
    SHA1   = r"\b[0-9a-fA-F]{40}\b(?![0-9a-fA-F])"
    MD5    = r"\b[0-9a-fA-F]{32}\b(?![0-9a-fA-F])"

    # Security identifiers
    CVE = r"\bCVE-\d{4}-\d{4,}\b"
    CPE = r"\bcpe:(?:/|2\.3:)[aho](?::[A-Za-z0-9\._\-~%*]+){2,}\b"

    # Authentication
    PASSWORD_CONTEXT = r"(?:password|passwd|pwd|secret|api_key)=([^\",;'\s]{4,128})\b"
    JWT              = r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"

    # PII
    EMAIL       = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
    PHONE       = r"\b(?:\+?\d{1,3}[-. ]?)?\(?\d{2,3}\)?[-. ]?\d{4,5}[-. ]?\d{4}\b"
    CPF         = r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
    CREDIT_CARD = r"\b(?:\d{4}[- ]?){3}\d{4}\b"
    UUID        = r"\b[0-9a-fA-F]{8}-...-[0-9a-fA-F]{12}\b"

    # Certificates & keys
    CERT_PEM     = r"-----BEGIN CERTIFICATE-----[A-Za-z0-9+/=\n\r]{50,8000}-----END CERTIFICATE-----"
    PRIVATE_KEY_PEM = r"-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----..."
    ...
```

### 4.3 Adding a custom recognizer

1. Add the pattern to `RegexPatterns`:

```python
class RegexPatterns:
    ...
    TICKET_ID = r"\b[A-Z]{2,6}-\d{4,8}\b"   # e.g. VULN-123456
```

2. Register a `PatternRecognizer` inside `load_custom_recognizers()` in `src/anon/engine.py`:

```python
ticket_pattern = Pattern(
    name="Ticket ID Pattern",
    regex=RegexPatterns.TICKET_ID,
    score=0.9,
)
recognizers.append(
    PatternRecognizer(
        supported_entity="TICKET_ID",
        patterns=[ticket_pattern],
        supported_language=lang,
    )
)
```

3. Optionally add `"TICKET_ID"` to the entity mapping in `config.py` if it needs label normalisation.

---

## 5. Transformer Models

**File:** `src/anon/engine.py` (`_setup_engines`)

### 5.1 How model selection works

The CLI flag `--transformer-model` accepts any HuggingFace model identifier. The engine selects the entity-label mapping based on the model name:

```python
def _setup_engines(self):
    if "SecureModernBERT-NER" in self.transformer_model:
        entity_mapping = SECURE_MODERNBERT_ENTITY_MAPPING
    else:
        entity_mapping = ENTITY_MAPPING
    # ... initialise Presidio with chosen model and mapping
```

### 5.2 Adding support for a new model

1. Define the label→canonical mapping in `config.py`:

```python
MY_MODEL_ENTITY_MAPPING = {
    "B-PER": "PERSON",
    "B-ORG": "ORGANIZATION",
    "B-LOC": "LOCATION",
    "B-MISC": "MISC",
}
```

2. Import and select the mapping in `_setup_engines()`:

```python
from src.anon.config import MY_MODEL_ENTITY_MAPPING

if "my-model-name" in self.transformer_model:
    entity_mapping = MY_MODEL_ENTITY_MAPPING
```

3. Use the model via the CLI:

```bash
uv run anon.py file.csv --transformer-model my-org/my-model-name
```

---

## 6. Cache Backend

**Protocol:** `src/anon/core/protocols.py` → `CacheStrategy`
**Default implementation:** `src/anon/cache_manager.py` → `CacheManager` (LRU, thread-safe)

### 6.1 Interface

```python
class CacheStrategy(Protocol):
    def get(self, key: str) -> Optional[str]:
        """Return cached value for key, or None if absent."""
        ...

    def add(self, key: str, value: str) -> None:
        """Store key→value in the cache."""
        ...
```

### 6.2 Injection

```python
my_cache = RedisCacheAdapter(host="localhost", port=6379)

orchestrator = AnonymizationOrchestrator(
    ...,
    cache_manager=my_cache,
)
```

### 6.3 Example: Redis-backed cache

```python
import redis
from typing import Optional

class RedisCacheAdapter:
    def __init__(self, host: str, port: int, ttl: int = 3600):
        self._client = redis.Redis(host=host, port=port, decode_responses=True)
        self._ttl = ttl

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def add(self, key: str, value: str) -> None:
        self._client.set(key, value, ex=self._ttl)
```

---

## 7. Hashing / Pseudonym Generation

**Protocol:** `src/anon/core/protocols.py` → `HashingStrategy`
**Default implementation:** `src/anon/hash_generator.py` → `HashGenerator`

### 7.1 How pseudonyms are formed

The default pipeline:

```
original text  →  HMAC-SHA256(ANON_SECRET_KEY, text)  →  64-char hex  →  first slug_length chars
```

Output token: `[ENTITY_TYPE_<display_hash>]`, e.g. `[PERSON_4af3b2c1]`.

### 7.2 Interface

```python
class HashingStrategy(Protocol):
    def generate_slug(
        self,
        text: str,
        slug_length: Optional[int] = None,
    ) -> Tuple[str, str]:
        """
        Args:
            text:        Original PII string.
            slug_length: Length of the display token. None = full hash.

        Returns:
            (display_hash, full_hash)
        """
        ...
```

### 7.3 Injection

```python
my_hasher = DeterministicTokenHasher(secret="s3cr3t")

orchestrator = AnonymizationOrchestrator(
    ...,
    hash_generator=my_hasher,
)
```

### 7.4 Example: sequential token hasher (for testing)

```python
class SequentialTokenHasher:
    """Assigns sequential IDs — deterministic across a single run but NOT across runs."""

    def __init__(self):
        self._counter: dict[str, int] = {}

    def generate_slug(self, text: str, slug_length: Optional[int] = None) -> tuple[str, str]:
        if text not in self._counter:
            self._counter[text] = len(self._counter) + 1
        token = f"{self._counter[text]:08d}"
        return token, token
```

---

## 8. Entity Storage

**Protocol:** `src/anon/core/protocols.py` → `EntityStorage`
**Default implementation:** `src/anon/database.py` → `DatabaseContext` (SQLite)

### 8.1 Interface

```python
class EntityStorage(Protocol):
    def initialize(self, synchronous: Optional[str] = None) -> None:
        """Create schema / open connection."""
        ...

    def save_entities(self, entity_list: List[Tuple]) -> None:
        """
        Persist a batch of entity records.

        Each tuple: (entity_type, original_name, display_hash, full_hash)
        """
        ...

    def shutdown(self) -> None:
        """Flush and close connection."""
        ...
```

### 8.2 Injection

```python
my_storage = PostgresEntityStorage(dsn="postgresql://...")
my_storage.initialize()

orchestrator = AnonymizationOrchestrator(
    ...,
    db_context=my_storage,
)
```

### 8.3 Example: in-memory storage (for testing)

```python
class InMemoryEntityStorage:
    def __init__(self):
        self._records: list[tuple] = []

    def initialize(self, synchronous=None) -> None:
        self._records.clear()

    def save_entities(self, entity_list: list[tuple]) -> None:
        self._records.extend(entity_list)

    def shutdown(self) -> None:
        pass  # nothing to flush

    def all(self) -> list[tuple]:
        return list(self._records)
```

---

## 9. Secret Manager

**Protocol:** `src/anon/core/protocols.py` → `SecretManager`
**Default implementation:** `src/anon/security.py` → `SecretManagerImpl`

### 9.1 Interface

```python
class SecretManager(Protocol):
    def get_secret_key(self) -> Optional[str]:
        """Return the HMAC secret key string, or None if not configured."""
        ...
```

### 9.2 Default resolution order

`SecretManagerImpl` checks, in order:

1. `ANON_SECRET_KEY_FILE` environment variable — path to a file whose content is the key.
2. `ANON_SECRET_KEY` environment variable — raw key string.
3. Returns `None` (tool will raise at hash time).

### 9.3 Example: HashiCorp Vault integration

```python
import hvac

class VaultSecretManager:
    def __init__(self, vault_url: str, token: str, secret_path: str):
        self._client = hvac.Client(url=vault_url, token=token)
        self._path = secret_path

    def get_secret_key(self) -> Optional[str]:
        response = self._client.secrets.kv.v2.read_secret_version(path=self._path)
        return response["data"]["data"].get("anon_key")
```

Pass it by providing the key directly to `HashGenerator` or by subclassing it to call your manager.

---

## 10. Entity Detector

**File:** `src/anon/entity_detector.py`

### 10.1 Role

`EntityDetector` sits between the spaCy/transformer output and the anonymization pipeline. It:

- Merges overlapping entity spans (keeps highest-score, longest match).
- Filters entities in `entities_to_preserve` or `allow_list`.
- Applies the `entity_mapping` normalisation.

### 10.2 Constructor

```python
class EntityDetector:
    def __init__(
        self,
        compiled_patterns: List[Dict],      # Pre-compiled regex pattern dicts
        entities_to_preserve: Set[str],     # Entity types to skip
        allow_list: Set[str],               # Exact strings to skip
        entity_mapping: Optional[Dict[str, str]] = None,  # Label normalisation
    ): ...
```

### 10.3 Key methods

```python
def extract_entities(self, doc, original_doc_text: str) -> List[Dict]:
    """
    Extract entities from a spaCy Doc and from compiled regex patterns.

    Returns list of dicts:
        {"start": int, "end": int, "label": str, "text": str, "score": float}
    """

def merge_overlapping_entities(self, detected_entities: List[Dict]) -> List[Dict]:
    """Sort and merge overlapping spans, keeping highest-score / longest match."""
```

### 10.4 Customisation

Subclass `EntityDetector` to override merge logic or add a pre-filter:

```python
class ContextAwareDetector(EntityDetector):
    def extract_entities(self, doc, original_doc_text: str) -> list[dict]:
        entities = super().extract_entities(doc, original_doc_text)
        # Discard entities inside quoted strings
        return [e for e in entities if not self._in_quotes(original_doc_text, e)]

    def _in_quotes(self, text: str, entity: dict) -> bool:
        before = text[:entity["start"]]
        return before.count('"') % 2 == 1
```

Inject via:

```python
orchestrator = AnonymizationOrchestrator(
    ...,
    entity_detector=ContextAwareDetector(...),
)
```

---

## 11. SLM Client

**File:** `src/anon/slm/client.py`

### 11.1 Interface

```python
class SLMClient(Protocol):
    def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> SLMResponse:
        """Send a prompt and return a structured response."""
        ...

    def query_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send a prompt and parse the JSON response body."""
        ...
```

`SLMResponse` is a dataclass with at minimum:

```python
@dataclass
class SLMResponse:
    content: str          # Raw text response
    model: str            # Model identifier
    tokens_used: int      # Total tokens consumed
    success: bool         # Whether the request succeeded
    error: Optional[str]  # Error message if not success
```

### 11.2 Default implementation: `OllamaClient`

```python
OllamaClient(
    model="llama3",
    base_url="http://localhost:11434",
    timeout=120,
    temperature=None,        # Use model default
    max_retries=3,
    auto_manage=True,        # Start/stop Ollama service automatically
    docker_image=None,       # Pull from Docker Hub if set
    container_name=None,
    gpu_enabled=True,
)
```

### 11.3 Example: OpenAI-compatible client

```python
import openai
from src.anon.slm.client import SLMResponse

class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def query(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> SLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
            )
            return SLMResponse(
                content=resp.choices[0].message.content,
                model=self._model,
                tokens_used=resp.usage.total_tokens,
                success=True,
                error=None,
            )
        except Exception as exc:
            return SLMResponse(content="", model=self._model,
                               tokens_used=0, success=False, error=str(exc))

    def query_json(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> dict:
        import json
        response = self.query(prompt, system_prompt, **kwargs)
        return json.loads(response.content)
```

Pass the client to the SLM layer:

```python
from src.anon.slm.detectors.slm_detector import SLMEntityDetector
from src.anon.slm.prompts import PromptManager

slm_client = OpenAIClient(api_key="sk-...")
prompt_mgr  = PromptManager(base_path="prompts/")

slm_detector = SLMEntityDetector(
    slm_client=slm_client,
    prompt_manager=prompt_mgr,
    entities_to_preserve={"TOOL", "PLATFORM"},
    allow_list=set(),
    confidence_threshold=0.7,
)
```

---

## 12. SLM Prompts

**File:** `src/anon/slm/prompts.py`

### 12.1 Directory layout

```
prompts/
├── entity_mapper/
│   ├── v1_en.json
│   └── v1_pt.json
├── entity_detector/
│   └── v1_en.json
└── full_anonymizer/
    └── v1_en.json
```

### 12.2 Prompt JSON format

```json
{
  "system": "You are a privacy expert. Identify all PII in the text.",
  "user": "Text: {text}\n\nIdentify all PII entities and return JSON.",
  "version": "v1",
  "language": "en"
}
```

Placeholders (`{text}`, `{entities}`, etc.) are filled by `PromptTemplate.format(**kwargs)`.

### 12.3 Adding a custom prompt

1. Create `prompts/entity_detector/v2_en.json` with your improved system/user prompts.
2. Pass `prompt_version="v2"` when constructing `SLMEntityDetector`:

```python
SLMEntityDetector(
    ...,
    prompt_version="v2",
)
```

Or via CLI:

```bash
uv run anon.py file.csv --slm-detector --slm-prompt-version v2
```

### 12.4 Adding a new task type

1. Create the directory: `prompts/my_task/v1_en.json`.
2. Use `PromptManager.get("my_task", language="en", version="v1")` in your code.

---

## 13. Model Provider

**File:** `src/anon/model_manager.py`

### 13.1 Interface

```python
class ModelProvider(Protocol):
    def is_available(self, model_name: str) -> bool:
        """Return True if the model is already present locally."""
        ...

    def download(self, model_name: str) -> bool:
        """Download the model. Return True on success."""
        ...

    def get_info(self, model_name: str) -> ModelInfo:
        """Return metadata about the model."""
        ...
```

### 13.2 Built-in providers

| Provider | Key | Models |
|---|---|---|
| `SpacyModelProvider` | `"spacy"` | spaCy language models |
| `TransformerModelProvider` | `"transformer"` | HuggingFace transformer models |
| `TesseractProvider` | `"tesseract"` | Tesseract OCR engine |

### 13.3 Registering a custom provider

```python
from src.anon.model_manager import ModelManager

manager = ModelManager()
manager.register_provider("my_provider", MyModelProvider())

# The provider will be invoked when ensure_available("my_provider", model_name) is called.
manager.ensure_available("my_provider", "my-model-v1")
```

### 13.4 Example: local-file model provider

```python
from pathlib import Path
from src.anon.model_manager import ModelInfo

class LocalFileModelProvider:
    def __init__(self, model_dir: Path):
        self._dir = model_dir

    def is_available(self, model_name: str) -> bool:
        return (self._dir / model_name).exists()

    def download(self, model_name: str) -> bool:
        # No-op: models must be placed manually
        return self.is_available(model_name)

    def get_info(self, model_name: str) -> ModelInfo:
        path = self._dir / model_name
        return ModelInfo(name=model_name, size_mb=path.stat().st_size / 1e6,
                         provider="local", location=str(path))
```

---

## 14. Dependency Injection Reference

All injectable dependencies are passed to `AnonymizationOrchestrator.__init__()`. Below is the complete constructor signature with the Protocol or ABC each parameter must satisfy.

```python
AnonymizationOrchestrator(
    # Required
    lang            = "en",                        # str — language code
    db_context      = my_storage,                  # EntityStorage Protocol (or None)
    allow_list      = {"safe_string"},             # List[str]
    entities_to_preserve = {"TOOL", "PLATFORM"},  # List[str]

    # Optional — strategy
    strategy        = None,                        # AnonymizationStrategy instance (overrides strategy_name)
    strategy_name   = "filtered",                  # str — used if strategy=None

    # Optional — pipeline components
    cache_manager   = my_cache,                    # CacheStrategy Protocol
    hash_generator  = my_hasher,                   # HashingStrategy Protocol
    entity_detector = my_detector,                 # EntityDetector instance

    # Optional — SLM
    slm_detector    = my_slm_detector,             # AnonymizationStrategy-compatible
    slm_detector_mode = "hybrid",                  # "hybrid" | "exclusive"

    # Optional — model / engine
    transformer_model = "attack-vector/SecureModernBERT-NER",
    analyzer_engine   = None,                      # Pre-built Presidio BatchAnalyzerEngine
    anonymizer_engine = None,                      # Pre-built Presidio AnonymizerEngine

    # Optional — tuning
    slug_length       = 8,
    regex_priority    = False,
    nlp_batch_size    = 32,
    parallel_workers  = 1,
    ner_data_generation = False,
)
```

If a component is not provided, the orchestrator creates a safe default (e.g. a no-op cache, the default `HashGenerator`), so you only need to supply the ones you intend to replace.
