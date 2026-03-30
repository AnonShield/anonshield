# Architecture Reference

## System Architecture

The tool is designed with a modular, layered architecture to separate responsibilities and allow for extensibility.

```mermaid
graph TD
    A[User] -- "uv run anon.py <file> [args]" --> B(anon.py CLI);

    subgraph "1. Orchestration & File Processing"
        B -- "Instantiates" --> Orch(AnonymizationOrchestrator);
        B -- "Gets Processor" --> F(ProcessorRegistry);
        F -- "e.g., .pdf" --> P_PDF(PdfFileProcessor);
        P_PDF -- "Extracts" --> RawText(Raw Text Content);
    end

    subgraph "2. Anonymization Core"
        RawText -- "orchestrator.anonymize()" --> Orch;
        Orch -- "Selects Strategy (--strategy)" --> STR_CHOICE{Strategy};
        STR_CHOICE -- "'presidio', 'filtered', 'hybrid', 'standalone'" --> PRESIDIO_STR(Traditional Strategy);
        STR_CHOICE -- "'slm'" --> SLM_STR(SLM Strategy);
    end

    subgraph "3. Traditional Engine (Presidio/Regex)"
        PRESIDIO_STR -- "Uses" --> Presidio(Presidio Engine);
        Presidio -- "Loads Models" --> Models(NLP Models);
        Presidio -- "Uses Recognizers" --> Regex(Custom Recognizers);
        Presidio -- "Generates Slug" --> Anonymizer(CustomSlugAnonymizer);
        Anonymizer -- "HMAC + DB" --> DB[(entities.db)];
        Anonymizer -- "Replaces PII" --> AnonymizedText[Anonymized Text];
    end

    subgraph "3b. SLM Engine (Ollama)"
        SLM_STR -- "Queries" --> Ollama(OllamaClient);
        Ollama -- "Local LLM inference" --> AnonymizedText;
    end

    subgraph "4. Output Generation"
        AnonymizedText --> P_PDF;
        P_PDF -- "Writes File" --> OUT(output/anon_file...);
        B -- "Writes Report" --> LOG(logs/report.txt);
    end
```

---

## Technology Stack

- **[Presidio](https://microsoft.github.io/presidio/):** Core engine for PII identification and anonymization.
- **[spaCy](https://spacy.io/) & [Hugging Face Transformers](https://huggingface.co/docs/transformers/index):** NLP and Named Entity Recognition (NER).
- **[Pandas](https://pandas.pydata.org/):** Structured data processing (CSV, XLSX).
- **[PyMuPDF](https://pymupdf.readthedocs.io/en/latest/) & [python-docx](https://python-docx.readthedocs.io/en/latest/):** PDF and DOCX parsing.
- **[Pytesseract](https://github.com/madmaze/pytesseract):** OCR for text extraction from images.
- **[ijson](https://github.com/ICRAR/ijson):** Streaming large JSON files.
- **[orjson](https://github.com/ijl/orjson):** JSON serialization/deserialization.
- **[openpyxl](https://openpyxl.readthedocs.io/):** Excel file processing.
- **[lxml](https://lxml.de/):** XML parsing and processing.

---

## Anonymization Mechanism

For each detected entity:

1. Normalize entity text (remove extra spaces).
2. Generate an **HMAC-SHA256** hash using `ANON_SECRET_KEY`.
3. Store the full hash (64 characters) as a unique identifier in the database.
4. Replace the entity in text with a slug of configurable length (e.g., `[PERSON_a1b2c3d4]`).

The same entity always produces the same slug, maintaining referential consistency across the anonymized output.

---

## Database Schema

SQLite database at `db/entities.db`:

| Column | Type | Description |
|:-------|:-----|:------------|
| `id` | INTEGER | Primary key |
| `entity_type` | TEXT | Entity type (e.g., `PERSON`, `LOCATION`) |
| `original_name` | TEXT | Original entity text |
| `slug_name` | TEXT | Short hash displayed in anonymized output |
| `full_hash` | TEXT | Full HMAC-SHA256 hash (UNIQUE) |
| `first_seen` | TEXT | Timestamp of first detection |
| `last_seen` | TEXT | Timestamp of last detection |

---

## Core Components

### 1. CLI Layer (`anon.py`)

The composition root — parses arguments, instantiates and wires all core components (`CacheManager`, `HashGenerator`, `EntityDetector`, `DatabaseContext`), injects dependencies into `AnonymizationOrchestrator`, dispatches files to processors, and generates performance reports.

### 2. Anonymization Orchestrator (`engine.py`)

Central coordinator. Responsibilities:
- Initializes Presidio `AnalyzerEngine` and `AnonymizerEngine`.
- Selects and injects dependencies into the chosen strategy.
- Manages the batch fallback mechanism.
- Collects entity statistics for reporting.

### 3. File Processors (`processors.py`)

Template Method Pattern with a base `FileProcessor` and specialized subclasses:

| Processor | Handles |
|:----------|:--------|
| `TextFileProcessor` | `.txt`, `.log` — line-by-line |
| `ImageFileProcessor` | Images — OCR extraction |
| `DocxFileProcessor` | `.docx` — paragraphs + embedded images |
| `PdfFileProcessor` | `.pdf` — text blocks + images |
| `CsvFileProcessor` | `.csv` — column-wise with translation maps |
| `XlsxFileProcessor` | `.xlsx` — in-memory workbook processing |
| `XmlFileProcessor` | `.xml` — structure-preserving with XPath tracking |
| `JsonFileProcessor` | `.json`, `.jsonl` — hybrid streaming/in-memory |

**JSON Processing Modes:**
1. JSONL: line-by-line streaming
2. Small JSON (<100 MB): in-memory
3. Large JSON arrays: `ijson` streaming
4. Fallback to in-memory if streaming fails

### 4. Database Layer

**Repository Pattern (`repository.py`):** `EntityRepository` handles connection management (thread-local storage), schema initialization, batch insertion with `INSERT OR IGNORE`, and entity lookup by slug.

**Thread-Safe Queue (`database.py`):** All writes go through a `queue.Queue` consumed by a dedicated background writer thread, preventing DB write locks from blocking processing. Graceful shutdown ensures the queue is fully drained before exit.

---

## Processing Pipeline

### Anonymization Pipeline

1. **Should Anonymize Check:** Config-based exclusion → forced anonymization → text filters (stoplist, min length, numeric) → explicit/implicit mode.
2. **Entity Detection:** spaCy NER + Transformer (XLM-RoBERTa) + custom regex recognizers → merge and deduplicate.
3. **Hash Generation:** Normalize → HMAC-SHA256 with secret key → create slug.
4. **Database Storage:** Queue entity for async write.
5. **Text Replacement:** Replace entity with `[TYPE_hash]`.

### Structure Preservation

**JSON/XML:** Parse tree → collect strings by path → create translation map → reconstruct tree.

**CSV/XLSX:** Process unique values per column → create translation map → apply vectorized transformations → preserve headers.

---

## Memory Management

- **PDF:** Page-by-page with explicit cleanup (`page.clean_contents()`, `del page`).
- **JSON:** `ijson` streaming for large arrays; line-by-line for JSONL.
- **CSV/XLSX:** Chunked Pandas reads; XLSX iterates cells without loading full workbook.
- **GC Control:** `--disable-gc` disables automatic GC for large single files; explicit `gc.collect()` calls are placed strategically.

---

## Caching Strategy

LRU cache (`collections.OrderedDict`):
- Configurable size via `--max-cache-size` (default: 10,000 items).
- Enabled by default; disable with `--no-use-cache`.
- Caches `(original_text → anonymized_slug)` pairs to avoid redundant detection and hashing.

---

## Fallback Architecture

After batch processing, the orchestrator verifies input count == output count. On mismatch:
1. `_safe_fallback_processing` re-processes items one-by-one.
2. Errors are logged; problematic items return original text to preserve structure.
3. Prevents misaligned output in structured files (CSV, JSON, XML) and accidental PII exposure.

---

## Repository Structure

```
.
├── anon.py                          # CLI entry point
├── pyproject.toml                   # Project metadata and dependencies
├── uv.lock                          # Dependency lock file
├── run.sh                           # Docker orchestration script
│
├── examples/
│   ├── anonymization_config.json    # Default anonymization config
│   ├── anonymization_config_cve.json # CVE-specific config example
│   ├── word_list.example.json       # Word list format example
│   └── exemplo.docx / exemplo.xlsx  # Sample documents
│
├── docker/
│   ├── Dockerfile                   # Multi-stage build (CPU + GPU)
│   ├── docker-compose.yml           # Service profiles
│   └── docker-entrypoint.sh        # Container entrypoint
│
├── src/anon/                        # Core library
│   ├── config.py                    # Entity mappings, language lists
│   ├── engine.py                    # AnonymizationOrchestrator
│   ├── strategies.py                # FullPresidio, Filtered, Hybrid strategies
│   ├── standalone_strategy.py       # StandaloneStrategy
│   ├── entity_detector.py           # NER entity detection
│   ├── processors.py                # File processors
│   ├── repository.py                # EntityRepository (SQLite)
│   ├── database.py                  # Thread-safe DB writer queue
│   ├── hash_generator.py            # HMAC-SHA256 hash generation
│   ├── cache_manager.py             # LRU cache
│   ├── security.py                  # Key validation
│   ├── model_manager.py             # Model loading and management
│   ├── tqdm_handler.py              # Progress bar handler
│   ├── core/
│   │   ├── config_loader.py         # Configuration loading
│   │   └── protocols.py             # Protocol interfaces
│   ├── slm/                         # Small Language Model integration
│   │   ├── client.py                # OllamaClient (SLMClient protocol)
│   │   ├── prompts.py               # PromptManager
│   │   ├── ollama_manager.py        # Ollama process management
│   │   ├── anonymizers/
│   │   │   └── slm_anonymizer.py    # End-to-end SLM anonymization
│   │   ├── detectors/
│   │   │   └── slm_detector.py      # SLM as entity detector
│   │   └── mappers/
│   │       └── entity_mapper.py     # SLM entity mapping
│   └── evaluation/                  # Evaluation support
│       ├── ground_truth.py          # Ground truth loading
│       ├── hash_tracker.py          # Hash tracking for evaluation
│       └── metrics_calculator.py    # TP/FP/FN metrics
│
├── scripts/                         # Utility scripts
│   ├── deanonymize.py               # Controlled de-anonymization
│   ├── evaluate.py                  # Evaluation metrics
│   ├── create_ground_truth.py       # Ground truth generation
│   ├── sample.py                    # Data sampling
│   ├── generate_cve_dataset.py      # CVE dataset generation
│   ├── analyze_entity_map.py        # Entity map analysis
│   ├── cluster_entities.py          # Entity clustering (HDBSCAN)
│   ├── get_metrics.py               # Performance statistics
│   ├── export_and_clear_db.py       # DB export/clear
│   └── utils.py                     # Shared utilities
│
├── tests/                           # Test suite
├── benchmark/                       # Benchmarking suite
│   └── README.md                    # Benchmark documentation
└── docs/                            # Documentation
    └── developers/
        ├── ARCHITECTURE.md
        ├── ANONYMIZATION_STRATEGIES.md
        ├── EXTENSIBILITY.md
        ├── SLM_INTEGRATION_GUIDE.md
        └── UTILITY_SCRIPTS_GUIDE.md
```

---

### See Also

- [Extensibility Guide](EXTENSIBILITY.md) — all extension points with worked examples (strategies, processors, cache, storage, SLM client, model providers, etc.)
- [Anonymization Strategies](ANONYMIZATION_STRATEGIES.md) — detailed description of each built-in strategy
- [SLM Integration Guide](SLM_INTEGRATION_GUIDE.md) — deep dive into the SLM module architecture
