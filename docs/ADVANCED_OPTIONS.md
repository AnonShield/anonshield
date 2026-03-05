# Advanced Options Reference

## Command-Line Options

### Required Arguments

- `file_path`: Path to the target file or directory to process.

### Mode Selection

- `--generate-ner-data`: Generate NER training data (JSONL format) instead of anonymizing. Does not require `ANON_SECRET_KEY`. Output format: `{"text": "...", "label": [[start, end, entity_type], ...]}`.

### General Options

| Option | Description | Default |
|:-------|:------------|:--------|
| `--lang <code>` | Document language (`en`, `pt`, etc.) | `en` |
| `--output-dir <PATH>` | Output directory | `output` |
| `--overwrite` | Overwrite existing output files | off |
| `--no-report` | Disable performance report in `logs/` | off |
| `--log-level <LEVEL>` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `WARNING` |

### Anonymization Options

| Option | Description | Default |
|:-------|:------------|:--------|
| `--preserve-entities <TYPES>` | Comma-separated entity types to skip (e.g., `LOCATION,HOSTNAME`) | — |
| `--allow-list <TERMS>` | Comma-separated terms to ignore | — |
| `--slug-length <NUM>` | Hash length in slug (0–64). `0` = entity type only | `64` |
| `--anonymization-config <PATH>` | JSON config for field-level control in structured files | — |

### Performance & Filtering Options

| Option | Description | Default |
|:-------|:------------|:--------|
| `--optimize` | Enable all optimizations (`filtered` strategy + in-memory DB + cache + `--min-word-length 3`) | off |
| `--use-cache` / `--no-use-cache` | In-memory LRU cache for repeated anonymizations | on |
| `--max-cache-size <NUM>` | Maximum items in cache | `10000` |
| `--min-word-length <NUM>` | Minimum word length to process | `0` |
| `--skip-numeric` | Skip numeric-only strings | off |
| `--technical-stoplist <TERMS>` | Custom words to add to the technical stoplist | — |
| `--preserve-row-context` | Process every CSV/XLSX cell (accurate but slower) | off |
| `--json-stream-threshold-mb <NUM>` | Streaming threshold for JSON files (MB) | `100` |
| `--anonymization-strategy <strategy>` | `presidio`, `filtered`, `hybrid`, `standalone` | `filtered` |
| `--transformer-model <model>` | NER transformer model (see table below) | `Davlan/xlm-roberta-base-ner-hrl` |
| `--regex-priority` | Boost regex recognizer scores by 0.15 over model-based | off |
| `--db-mode <MODE>` | `persistent` (saves to disk) or `in-memory` | `persistent` |
| `--db-synchronous-mode <MODE>` | SQLite synchronous PRAGMA: `OFF`, `NORMAL`, `FULL`, `EXTRA` | — |
| `--disable-gc` | Disable automatic garbage collection (useful for large single files) | off |

### Chunking & Batching Options

| Option | Default |
|:-------|:--------|
| `--batch-size <NUM>` | `1000` |
| `--csv-chunk-size <NUM>` | `1000` |
| `--json-chunk-size <NUM>` | `1000` |
| `--ner-chunk-size <NUM>` | `1500` |
| `--nlp-batch-size <NUM>` | `500` |

---

## Anonymization Strategies

| Strategy | Description | Memory |
|:---------|:------------|:-------|
| `filtered` (default) | Presidio with a curated, filtered set of recognizers | ~2 GB |
| `presidio` | Full Presidio pipeline with all recognizers | ~2 GB |
| `hybrid` | Presidio detection + manual text replacement | ~2 GB |
| `standalone` | Bypasses Presidio; loads NER models directly. Experimental. | ~1.5 GB |

All Presidio-based strategies load custom regex recognizers for cybersecurity patterns. Use `--regex-priority` to prioritize regex over model-based detection.

See [ANONYMIZATION_STRATEGIES.md](ANONYMIZATION_STRATEGIES.md) for benchmarks and technical details.

### Transformer Models

| Model | Scope | Languages |
|:------|:------|:----------|
| `Davlan/xlm-roberta-base-ner-hrl` (default) | General-purpose NER | 24 languages |
| `attack-vector/SecureModernBERT-NER` | Cybersecurity-focused NER (adds `MALWARE`, `THREAT_ACTOR`, etc.) | English |
| `dslim/bert-base-NER` | General-purpose NER, fast | English |

---

## Advanced Configuration for Structured Files

For `.json`, `.csv`, and `.xml` files, use a JSON config file (`--anonymization-config <PATH>`) to control which fields are anonymized.

### Keys

- `fields_to_exclude`: Dot-notation paths that are **never** anonymized.
- `fields_to_anonymize`: Dot-notation paths to anonymize with automatic detection. Enables **explicit mode** — only listed fields are processed.
- `force_anonymize`: Dict mapping dot-notation paths to `{"entity_type": "..."}`. Forces anonymization with a specific type, bypassing text filters.

### Modes

- **Implicit (default):** All fields are anonymized except those in `fields_to_exclude`.
- **Explicit:** Activated when `fields_to_anonymize` or `force_anonymize` is present — only listed fields are processed.

### Priority Order

1. `fields_to_exclude` — always skipped
2. `force_anonymize` — always anonymized
3. Text-based filters (stoplist, numeric, `min_word_length`)
4. Explicit vs. implicit mode

### Example

```json
{
  "fields_to_exclude": ["scan.id", "asset.tags.category"],
  "fields_to_anonymize": ["asset.tags.value", "asset.ipv4_addresses", "scan.target"],
  "force_anonymize": {
    "asset.name": { "entity_type": "CUSTOM_ASSET_NAME" }
  }
}
```

With this config: `scan.id` and `asset.tags.category` are skipped; `asset.name` is always anonymized as `CUSTOM_ASSET_NAME`; the other listed fields use automatic detection; everything else is ignored (explicit mode).

---

## Performance Optimization

### Quick (Recommended)

```bash
uv run anon.py large_dataset/ --optimize
```

Enables: `filtered` strategy + in-memory DB + caching + `--min-word-length 3`.

### Manual Tuning

```bash
# Filtered strategy
uv run anon.py file.json --anonymization-strategy filtered

# In-memory DB (no disk I/O, faster)
uv run anon.py file.xml --db-mode in-memory

# Custom cache size
uv run anon.py file.csv --use-cache --max-cache-size 50000

# Disable GC for large single files
uv run anon.py huge_file.pdf --disable-gc

# SQLite tuning
uv run anon.py dataset/ --db-synchronous-mode OFF
```

---

## NER Data Generation

Generates Named Entity Recognition training data instead of anonymizing:

```bash
uv run anon.py training_corpus/ --generate-ner-data --output-dir ner_output/
```

- Does not require `ANON_SECRET_KEY`
- Output: JSONL format, one object per line: `{"text": "...", "label": [[start, end, entity_type], ...]}`
- Useful for training custom NER models
