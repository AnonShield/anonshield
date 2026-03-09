# CLI Reference — Complete Argument Guide

This document covers every command-line option available in AnonLFI. Each argument includes a plain-language description, a concrete example, and notes on when to use it.

> **How to run the tool:**
>
> | Method | Command prefix |
> |--------|---------------|
> | **Docker — from this repository** | `./docker/run.sh [OPTIONS] <file_or_folder>` |
> | **Docker — downloaded from Docker Hub** | `./run.sh [OPTIONS] <file_or_folder>` (script downloaded per DOCKERHUB_README instructions) |
> | **Local install** | `uv run anon.py [OPTIONS] <file_or_folder>` |
>
> All examples below use `./docker/run.sh`. If you downloaded the script from Docker Hub, use `./run.sh` instead. If you installed locally, use `uv run anon.py`.

---

## Table of Contents

1. [Positional Argument — The File or Folder](#1-positional-argument--the-file-or-folder)
2. [Informational Commands](#2-informational-commands)
3. [General Options](#3-general-options)
4. [Anonymization Options](#4-anonymization-options)
5. [Word List](#5-word-list)
6. [Performance and Filtering Options](#6-performance-and-filtering-options)
7. [Anonymization Strategy and Models](#7-anonymization-strategy-and-models)
8. [Database Options](#8-database-options)
9. [Chunking and Batching Options](#9-chunking-and-batching-options)
10. [NER Data Generation Options](#10-ner-data-generation-options)
11. [SLM / AI Options (Experimental)](#11-slm--ai-options-experimental)
12. [Ollama Service Options (Experimental)](#12-ollama-service-options-experimental)
13. [Quick Reference Table](#13-quick-reference-table)

---

## 1. Positional Argument — The File or Folder

### `file_path`

**What it is:** The path to the file or folder you want to anonymize. This is the only required argument.

**Accepted values:**
- A single file: `report.csv`, `./data/scan.json`, `/home/user/incident.pdf`
- A directory: `./reports/`, `/data/openvas/`

When you point to a folder, the tool processes every supported file inside it, including subdirectories.

**Supported file types:**
`.txt` `.log` `.csv` `.xlsx` `.json` `.jsonl` `.xml` `.pdf` `.docx` `.png` `.jpg` `.gif` `.bmp` `.tiff` `.webp`

**Examples:**

```bash
# Anonymize a single CSV file
./docker/run.sh ./incident_report.csv

# Anonymize an entire folder
./docker/run.sh ./openvas_reports/

# Anonymize a PDF scan report
./docker/run.sh ./nessus_scan.pdf
```

> **Note:** Unsupported file types (e.g., `.exe`, `.zip`) are silently skipped when processing a folder.

---

## 2. Informational Commands

These flags print information and exit immediately — they do not process any file.

---

### `--list-entities`

**What it does:** Prints all entity types detectable for the given strategy and model combination, then exits. The output varies by `--anonymization-strategy` and `--transformer-model` — different combinations produce different entity sets.

**When to use:** Before running on a file, to know which entity names to use with `--preserve-entities`.

```bash
# Default (filtered strategy, xlm-roberta model)
./docker/run.sh --list-entities

# See entities available with the presidio strategy (includes AU_ABN, US_SSN, IBAN, etc.)
./docker/run.sh --list-entities --anonymization-strategy presidio

# See entities for the cybersecurity-focused model
./docker/run.sh --list-entities --transformer-model attack-vector/SecureModernBERT-NER
```

Sample output (`filtered` + default model):
```
Supported entity types (strategy=filtered, model=Davlan/xlm-roberta-base-ner-hrl):
 - AUTH_TOKEN
 - CERTIFICATE
 - CERT_SERIAL
 - CPE_STRING
 - CREDIT_CARD
 - CRYPTOGRAPHIC_KEY
 - CVE_ID
 - EMAIL_ADDRESS
 - FILE_PATH
 - HASH
 - HOSTNAME
 - IP_ADDRESS
 - LOCATION
 - MAC_ADDRESS
 - OID
 - ORGANIZATION
 - PASSWORD
 - PERSON
 - PGP_BLOCK
 - PHONE_NUMBER
 - PORT
 - URL
 - USERNAME
 - UUID
```

> **Strategy differences:** `presidio` includes all Presidio built-in recognizers (~46 entities, including `AU_ABN`, `US_SSN`, `IBAN_CODE`, `UK_NHS`, etc.). All other strategies (`filtered`, `hybrid`, `standalone`) use only the curated cybersecurity recognizer set shown above.

---

### `--list-languages`

**What it does:** Prints all supported document languages, then exits.

```bash
./docker/run.sh --list-languages
```

Sample output:
```
Supported languages:
 - en: English
 - pt: Portuguese
 - es: Spanish
 - de: German
 - fr: French
 - ...
```

---

## 3. General Options

---

### `--lang <code>`

**Default:** `en`

**What it does:** Tells the tool which language the document is written in. This loads the correct spaCy linguistic model and activates language-specific NER rules.

**When to use:** Any time your document is not in English.

```bash
# Portuguese security report
./docker/run.sh ./relatorio.pdf --lang pt

# Spanish document
./docker/run.sh ./incidente.docx --lang es
```

> **Supported codes:** `en`, `pt`, `es`, `de`, `fr`, `it`, `nl`, `pl`, `ru`, `zh`, and more — run `--list-languages` for the full list.

---

### `--output-dir <path>`

**Default:** `output`

**What it does:** Sets the folder where anonymized files are saved. The tool creates the folder automatically if it does not exist.

Output filenames always follow the pattern `anon_<original_filename>.<ext>`.

```bash
# Save results to a specific folder
./docker/run.sh ./reports/ --output-dir ./anonymized_results/

# Use an absolute path
./docker/run.sh ./scan.json --output-dir /data/processed/
```

---

### `--overwrite`

**Default:** off (existing files are skipped)

**What it does:** Allows the tool to replace existing output files. Without this flag, if `anon_report.csv` already exists in the output folder, it is skipped.

```bash
./docker/run.sh ./report.csv --overwrite
```

> **Use case:** Re-running the tool with different settings on the same input file.

---

### `--no-report`

**Default:** off (a performance report is always written)

**What it does:** Disables the creation of a text performance report in the `logs/` directory after each run.

```bash
./docker/run.sh ./report.csv --no-report
```

> **Use case:** Automated pipelines where you do not need the extra log file.

---

### `--log-level <LEVEL>`

**Default:** `WARNING`

**What it does:** Controls how much information is printed to the terminal during processing.

| Level | What you see |
|-------|-------------|
| `DEBUG` | Everything — very verbose, useful for troubleshooting |
| `INFO` | Progress updates (model loading, file processing) |
| `WARNING` | Only problems and warnings (default) |
| `ERROR` | Only errors |
| `CRITICAL` | Only fatal errors |

```bash
# See progress while processing
./docker/run.sh ./report.csv --log-level INFO

# Debug a problem
./docker/run.sh ./report.csv --log-level DEBUG
```

---

## 4. Anonymization Options

---

### `--preserve-entities <TYPES>`

**Default:** none (everything is anonymized)

**What it does:** A comma-separated list of entity types that should **not** be anonymized. Useful when some entities are not sensitive in your context (e.g., you want to keep IP addresses visible for analysis but anonymize names).

```bash
# Keep IP addresses and hostnames visible
./docker/run.sh ./scan.json --preserve-entities "IP_ADDRESS,HOSTNAME"

# Keep locations and organizations visible
./docker/run.sh ./report.txt --preserve-entities "LOCATION,ORGANIZATION"
```

> **Tip:** Use `--list-entities` to see all valid entity type names.

---

### `--allow-list <TERMS>`

**Default:** none

**What it does:** A comma-separated list of specific text values that should **never** be anonymized, regardless of what the NER model detects.

**When to use:** When the tool incorrectly anonymizes a word that is not sensitive in your context — for example, product names, public organization names, or known safe identifiers.

```bash
# Never anonymize these specific values
./docker/run.sh ./report.csv --allow-list "Google,Microsoft,CVSS"

# Multiple terms with spaces — quote the whole list
./docker/run.sh ./report.txt --allow-list "John Doe,127.0.0.1,internal-only"
```

---

### `--slug-length <n>`

**Default:** `64`

**What it does:** Controls the length of the random-looking suffix added to each anonymized entity.

When the tool replaces a name like `John Smith`, it generates a tag like `[PERSON_a1b2c3d4...]`. The number after the underscore is a hash derived from the original value and your secret key — the `--slug-length` controls how many characters of that hash appear.

| Value | Output example | Notes |
|-------|---------------|-------|
| `64` (default) | `[PERSON_a1b2c3...64chars]` | Maximum uniqueness, full reversibility |
| `8` | `[PERSON_a1b2c3d4]` | Shorter, easier to read, still unique for most datasets |
| `0` | `[PERSON]` | No hash — entity type label only. **No secret key required.** |

```bash
# Short slugs for readability
./docker/run.sh ./report.txt --slug-length 8

# Label-only (no de-anonymization possible later)
./docker/run.sh ./report.txt --slug-length 0
```

> **Important:** With `--slug-length 0` you do not need `ANON_SECRET_KEY`. With any other value, the key is required and must be kept for de-anonymization.

---

### `--anonymization-config <path>`

**Default:** none

**What it does:** Points to a JSON file that gives the tool precise, field-level instructions for structured files (JSON, CSV, XML). Without this, the tool runs NER inference on every field — correct, but slow on large datasets.

**The config supports three keys:**

| Key | Effect |
|-----|--------|
| `fields_to_exclude` | These fields are **never** touched |
| `fields_to_anonymize` | Only these fields run through NER inference |
| `force_anonymize` | These fields are always anonymized as a specific entity type, skipping NER entirely |

Fields are specified using **dot notation** (e.g., `asset.ipv4_addresses`).

**Example config file (`anon_config.json`):**

```json
{
  "fields_to_exclude": ["severity", "port", "protocol", "cvss_score", "age_in_days"],
  "fields_to_anonymize": ["asset.name", "output", "description"],
  "force_anonymize": {
    "asset.ipv4_addresses": { "entity_type": "IP_ADDRESS" },
    "asset.display_fqdn":   { "entity_type": "HOSTNAME" },
    "asset.display_mac_address": { "entity_type": "MAC_ADDRESS" },
    "scan.target":          { "entity_type": "HOSTNAME" }
  }
}
```

With this config:
- `severity`, `port`, `cvss_score`, etc. are preserved as-is
- `asset.ipv4_addresses` is always pseudonymized as `IP_ADDRESS`, no matter its format
- `asset.name`, `output`, and `description` go through full NER analysis
- Everything else is ignored

```bash
./docker/run.sh ./nessus_scan.json --anonymization-config ./anon_config.json
```

> **Performance impact:** Using `force_anonymize` and `fields_to_exclude` can speed up processing by **25–134x** on large structured files by eliminating NER inference for known fields.

---

## 5. Word List

### `--word-list <path>`

**Default:** none

**What it does:** Points to a JSON file containing lists of known terms that must **always** be anonymized, even if the NER model would otherwise miss them.

This is ideal for internal terminology: internal system names, internal organization names, project codenames, or employee names that a general NER model might not recognize.

**Format:** A JSON object where each key is the **entity type label** (uppercased automatically) and each value is a list of terms. Any string key is valid — no preset mapping is required. Use the same type labels you would use in `--preserve-entities` or `force_anonymize`.

**Example word list file (`my_terms.json`):**

```json
{
  "ORGANIZATION": ["AcmeCorp", "CSIRT-BR", "ProjectPhoenix"],
  "PERSON":       ["Jane Doe", "Carlos Souza"],
  "HOSTNAME":     ["fw-edge.internal", "siem.corp.local"],
  "IP_ADDRESS":   ["10.0.0.1", "192.168.100.254"],
  "MY_SYSTEM":    ["SIEM-Alpha", "FW-CORE-01", "PROXY-DMZ"]
}
```

You can use any entity type label, including custom ones (`MY_SYSTEM`, `THREAT_ACTOR`, `CAMPAIGN`, etc.). The label becomes the entity type recorded in the anonymization database.

```bash
./docker/run.sh ./incident_report.txt --word-list ./my_terms.json
```

> **How it works:** Each term is compiled into a case-insensitive, word-boundary-aware regex pattern with a confidence score of 1.0 (maximum). This ensures these terms are always detected and anonymized, regardless of surrounding context.

> **Tip:** Combine with `--anonymization-config` on structured files for full control: use `force_anonymize` for known fields, and `--word-list` for known values that appear across free-text fields.

---

## 6. Performance and Filtering Options

---

### `--optimize`

**Default:** off

**What it does:** A single flag that enables all recommended performance settings at once. Equivalent to running with `--anonymization-strategy standalone --db-mode in-memory --use-cache --min-word-length 3`.

```bash
./docker/run.sh ./large_dataset/ --optimize
```

> **When to use:** Processing large files or directories where speed matters more than maximum accuracy. On GPU, the `standalone` strategy is 4× faster than the default.

---

### `--use-cache` / `--no-use-cache`

**Default:** `--use-cache` (caching is on)

**What it does:** Keeps an in-memory dictionary of already-anonymized values. If the same entity (e.g., the same IP address) appears many times in a large file, the tool looks it up in the cache instead of recomputing its pseudonym.

```bash
# Caching is on by default, so this is the same as not specifying it
./docker/run.sh ./report.json --use-cache

# Disable caching (useful for very large files where cache memory is a concern)
./docker/run.sh ./report.json --no-use-cache
```

---

### `--max-cache-size <n>`

**Default:** `10000`

**What it does:** The maximum number of unique entities to store in the cache. Once the cache is full, the oldest entries are evicted (LRU policy).

```bash
# Larger cache for files with many unique entities
./docker/run.sh ./large_report.csv --max-cache-size 50000

# Smaller cache to reduce memory usage
./docker/run.sh ./report.csv --max-cache-size 1000
```

---

### `--min-word-length <n>`

**Default:** `0` (no minimum — all words are considered)

**What it does:** Skips any text token shorter than `n` characters. For example, with `--min-word-length 3`, the tokens `"a"`, `"to"`, and `"ok"` are never sent for NER inference. This can significantly reduce processing time on files with many short tokens.

```bash
# Skip tokens shorter than 3 characters (recommended for most datasets)
./docker/run.sh ./report.csv --min-word-length 3
```

> **Note:** `--optimize` automatically sets `--min-word-length 3`.

---

### `--skip-numeric`

**Default:** off

**What it does:** Skips strings that consist entirely of digits (e.g., `"12345"`, `"2024"`). Useful when numeric identifiers in your dataset are not sensitive (e.g., vulnerability counts, port numbers that should not be anonymized).

```bash
./docker/run.sh ./report.csv --skip-numeric
```

> **Caution:** Do not use this if your data contains sensitive numeric strings like credit card numbers or phone numbers in pure-digit format. Use `--preserve-entities CREDIT_CARD` instead for fine-grained control.

---

### `--preserve-row-context`

**Default:** off

**What it does:** For CSV and XLSX files, the tool by default groups identical values across rows and processes each unique value only once (much faster). With `--preserve-row-context`, every cell value is processed in full, which is slower but ensures that the surrounding column context is preserved for each row.

```bash
./docker/run.sh ./dataset.csv --preserve-row-context
```

> **When to use:** When your dataset has repeated values that have different meanings depending on the row context (rare), or when you suspect unique-value grouping is causing incorrect detections.

---

### `--json-stream-threshold-mb <n>`

**Default:** `100`

**What it does:** JSON files larger than this size (in megabytes) are processed by streaming from disk instead of loading the entire file into memory. Streaming uses more processing time but prevents out-of-memory errors on very large JSON files.

```bash
# Stream JSON files larger than 50 MB
./docker/run.sh ./large_export.json --json-stream-threshold-mb 50

# Only stream files larger than 500 MB (load smaller ones into RAM for speed)
./docker/run.sh ./export.json --json-stream-threshold-mb 500
```

---

### `--regex-priority`

**Default:** off

**What it does:** Gives custom regex recognizers (e.g., the built-in cybersecurity patterns for IPs, CVEs, hashes) a score boost over the transformer model-based detections. When both a regex and a model detect the same text span, the regex result wins.

```bash
./docker/run.sh ./vuln_report.txt --regex-priority
```

> **When to use:** On cybersecurity data where you want exact pattern matching (for IP addresses, CVE IDs, hashes) to take precedence over model-based detections, which can occasionally be imprecise.

---

### `--force-large-xml`

**Default:** off

**What it does:** By default, the tool refuses to process XML files that exceed internal memory safety limits, to avoid out-of-memory crashes. This flag disables that safety check.

```bash
./docker/run.sh ./massive_nessus_export.xml --force-large-xml
```

> **Warning:** Only use this on a machine with sufficient RAM. Processing a very large XML file without enough memory will crash the process.

---

### `--disable-gc`

**Default:** off

**What it does:** Disables Python's automatic garbage collector during processing. This can boost speed for a single large file because the GC is not pausing at inopportune moments, but it increases peak memory usage since unused objects accumulate.

```bash
./docker/run.sh ./huge_file.pdf --disable-gc
```

> **When to use:** Processing one very large file on a machine with ample RAM. Do not use when processing many files in a loop — memory will grow unbounded.

---

## 7. Anonymization Strategy and Models

---

### `--anonymization-strategy <strategy>`

**Default:** `filtered`

**What it does:** Selects the internal engine used to detect and replace entities.

| Strategy | Description | Best for |
|----------|-------------|---------|
| `filtered` | Presidio pipeline with a curated, optimized recognizer set | **Default — best accuracy** |
| `presidio` | Full Presidio pipeline with all recognizers enabled | Broadest detection, more false positives |
| `hybrid` | Presidio detection + manual text replacement (no Presidio anonymizer) | When Presidio's anonymizer causes issues |
| `standalone` | Loads NER models directly, bypasses Presidio entirely | **Maximum GPU throughput (4× faster)** |
| `slm` | End-to-end anonymization using a local language model (Ollama) | Experimental / research use |

**Performance comparison — GPU (NVIDIA RTX 5060 Ti, 551 MB JSON, 70,951 records):**

| Strategy | CSV (KB/s) | JSON (KB/s) |
|----------|-----------|------------|
| `standalone` | 732 | 1,250 |
| `hybrid` | 248 | 632 |
| `filtered` (default) | 240 | 627 |
| `presidio` | 171 | 575 |

**Accuracy comparison (67 annotated vulnerability records, SecureModernBERT model):**

| Strategy | Precision | Recall | F1 |
|----------|-----------|--------|----|
| `filtered` (default) | 91.9 % | 96.7 % | **94.2 %** |
| `hybrid` | 91.9 % | 96.7 % | **94.2 %** |
| `standalone` | 87.9 % | 94.5 % | 91.1 % |
| `presidio` | 71.6 % | 96.7 % | 82.3 % |

```bash
# Best accuracy (default — no flag needed)
./docker/run.sh ./report.csv

# Maximum GPU throughput
./docker/run.sh ./large_dataset.json --anonymization-strategy standalone

# Experimental: use a local LLM (requires Ollama)
./docker/run.sh ./report.txt --anonymization-strategy slm
```

> **Recommendation:** Use `filtered` for accuracy. Use `standalone` on GPU when processing large datasets where speed is the priority.

---

### `--transformer-model <model>`

**Default:** `Davlan/xlm-roberta-base-ner-hrl`

**What it does:** Selects the transformer model used for Named Entity Recognition (NER). The model is downloaded automatically on first use and cached locally.

| Model | Scope | Languages | Notes |
|-------|-------|-----------|-------|
| `Davlan/xlm-roberta-base-ner-hrl` | General-purpose NER | 24 languages | **Default** |
| `attack-vector/SecureModernBERT-NER` | Cybersecurity-focused NER | English only | Adds `MALWARE`, `THREAT_ACTOR`, `ATTACK_PATTERN`, etc. |
| `dslim/bert-base-NER` | General-purpose NER, fast | English only | Smaller, faster |

```bash
# Cybersecurity-focused model (recommended for security reports)
./docker/run.sh ./vuln_report.txt --transformer-model attack-vector/SecureModernBERT-NER

# Fast English model
./docker/run.sh ./report.txt --transformer-model dslim/bert-base-NER
```

> **First run:** The model is downloaded from HuggingFace (~1 GB for the default, ~400 MB for SecureModernBERT) and cached in `./anon/models/` for all subsequent runs.

---

## 8. Database Options

The tool uses a SQLite database to store entity mappings (original value → pseudonym). This database is what makes de-anonymization possible later.

---

### `--db-mode <mode>`

**Default:** `persistent`

**What it does:** Controls where the database lives.

| Mode | Behavior |
|------|---------|
| `persistent` | Saved to disk in `--db-dir`. Can be used for de-anonymization later. |
| `in-memory` | Lives only in RAM during the run. Faster, but mappings are lost when the tool finishes. |

```bash
# Save mappings to disk (default — keep for de-anonymization)
./docker/run.sh ./report.csv --db-mode persistent

# Temporary run, no de-anonymization needed
./docker/run.sh ./report.csv --db-mode in-memory
```

> **Note:** `--optimize` sets `--db-mode in-memory` automatically. Only use `in-memory` if you do not need to reverse the anonymization later.

---

### `--db-dir <path>`

**Default:** `db`

**What it does:** The directory where the persistent SQLite database file is stored.

```bash
./docker/run.sh ./report.csv --db-dir /secure/storage/anondb/
```

---

### `--db-synchronous-mode <mode>`

**Default:** none (SQLite default, which is `NORMAL`)

**What it does:** Sets SQLite's `synchronous` PRAGMA, which controls how aggressively SQLite flushes data to disk. Lower synchronous modes are faster but less safe in case of a power failure.

| Mode | Speed | Safety |
|------|-------|--------|
| `EXTRA` | Slowest | Maximum |
| `FULL` | Slow | High |
| `NORMAL` | Balanced | Good (default) |
| `OFF` | Fastest | Risk of corruption on crash |

```bash
# Maximum speed (acceptable for one-time batch runs)
./docker/run.sh ./large_dataset/ --db-synchronous-mode OFF

# Maximum safety (for production environments)
./docker/run.sh ./report.csv --db-synchronous-mode FULL
```

---

## 9. Chunking and Batching Options

These options control how large files are split into pieces for processing. The defaults are sensible for most use cases. Only adjust these if you are experiencing memory issues or want to fine-tune performance.

---

### `--batch-size <n>`

**Default:** `1000`

**What it does:** The number of text chunks processed in each batch by the NER pipeline.

```bash
./docker/run.sh ./report.csv --batch-size 500

# Use adaptive sizing based on file characteristics
./docker/run.sh ./report.csv --batch-size auto
```

---

### `--csv-chunk-size <n>`

**Default:** `1000`

**What it does:** The number of rows read from a CSV file at a time using pandas. Lower values reduce memory usage; higher values may be faster.

```bash
./docker/run.sh ./large.csv --csv-chunk-size 500
```

---

### `--json-chunk-size <n>`

**Default:** `1000`

**What it does:** The number of JSON array items processed per streaming batch on large JSON files.

```bash
./docker/run.sh ./export.json --json-chunk-size 500
```

---

### `--ner-chunk-size <n>`

**Default:** `1500`

**What it does:** Maximum character length of each text chunk sent to the NER model. Text longer than this is automatically split. Larger chunks provide more context to the model; smaller chunks reduce memory usage.

```bash
./docker/run.sh ./report.txt --ner-chunk-size 2000
```

---

### `--nlp-batch-size <n>`

**Default:** `500`

**What it does:** Batch size for spaCy's `nlp.pipe()` processing. Larger values speed up spaCy on GPU; smaller values reduce memory pressure.

```bash
./docker/run.sh ./corpus/ --nlp-batch-size 1000
```

---

### `--use-datasets`

**Default:** off

**What it does:** Uses HuggingFace `datasets` for batch NER processing instead of standard Python iteration. This eliminates the "running pipelines sequentially on GPU" warning and improves GPU utilization. Recommended for files larger than 50 MB.

```bash
./docker/run.sh ./large_corpus/ --use-datasets
```

---

## 10. NER Data Generation Options

These options switch the tool from *anonymization mode* into *NER training data generation mode*. In this mode, the tool detects entities but instead of replacing them, it writes a JSONL file recording what was found — ready to use as training data for a custom NER model.

> **No secret key required** in NER data generation mode.

---

### `--generate-ner-data`

**What it does:** Activates NER data generation mode. Output is one JSONL file per input file, where each line is:

```json
{"text": "The attacker at 192.168.1.1 used CVE-2021-44228.", "label": [[16, 29, "IP_ADDRESS"], [35, 50, "CVE_ID"]]}
```

```bash
./docker/run.sh ./corpus/ --generate-ner-data --output-dir ./ner_training_data/
```

---

### `--ner-include-all`

**Default:** off (only texts with at least one detected entity are included)

**What it does:** Includes all texts in the NER output, even those where no entities were detected. Useful when training a model that also needs to learn "there is nothing to detect here."

```bash
./docker/run.sh ./corpus/ --generate-ner-data --ner-include-all
```

---

### `--ner-aggregate-record`

**Default:** off

**What it does:** For JSON and JSONL files, instead of extracting each field separately, this option merges all fields of each record into a single text line before running NER. Useful when you want to preserve the full context of each record.

```bash
./docker/run.sh ./logs.jsonl --generate-ner-data --ner-aggregate-record
```

---

## 11. SLM / AI Options (Experimental)

These options use a **Small Language Model (SLM)** running locally via [Ollama](https://ollama.com/) to assist with entity detection or anonymization. They are experimental and intended for research use.

> **Prerequisite:** Ollama must be installed and running, or the tool must be allowed to manage an Ollama Docker container (`--no-auto-ollama` disabled).

---

### `--slm-map-entities`

**What it does:** Uses the SLM to scan a file and produce a detailed report of all potential entities, including confidence scores and the model's reasoning for each detection. **Does not anonymize** — only maps and reports.

Output files:
- `<name>_entity_map.jsonl` — one JSON object per entity
- `<name>_entity_map.csv` — same data in spreadsheet format

```bash
./docker/run.sh ./report.txt --slm-map-entities --output-dir ./entity_analysis/
```

---

### `--slm-detector`

**What it does:** Adds the SLM as an additional entity detector alongside the standard transformer NER model. The SLM results are merged with the traditional NER results.

```bash
./docker/run.sh ./report.txt --slm-detector
```

---

### `--slm-detector-mode <mode>`

**Default:** `hybrid`

**What it does:** Controls how SLM detections are combined with traditional NER results.

| Mode | Behavior |
|------|---------|
| `hybrid` | Merges SLM and traditional NER results (more detections) |
| `exclusive` | Uses only SLM results, ignoring the transformer model |

```bash
./docker/run.sh ./report.txt --slm-detector --slm-detector-mode exclusive
```

---

### `--slm-prompt-version <version>`

**Default:** `v1`

**What it does:** Selects which prompt template version to use for SLM tasks.

```bash
./docker/run.sh ./report.txt --slm-map-entities --slm-prompt-version v2
```

---

### `--slm-chunk-size <n>`

**Default:** `2000` (characters)

**What it does:** Maximum character length of each text chunk sent to the SLM mapper.

```bash
./docker/run.sh ./report.txt --slm-map-entities --slm-chunk-size 1500
```

---

### `--slm-anonymizer-chunk-size <n>`

**Default:** `3000` (characters)

**What it does:** Maximum character length of each text chunk sent to the SLM anonymizer (used with `--anonymization-strategy slm`).

```bash
./docker/run.sh ./report.txt --anonymization-strategy slm --slm-anonymizer-chunk-size 2000
```

---

### `--slm-confidence-threshold <n>`

**Default:** `0.7`

**What it does:** Minimum confidence score (0.0–1.0) for an entity detected by the SLM to be accepted. Entities with lower confidence are discarded.

```bash
# Only accept very high-confidence detections
./docker/run.sh ./report.txt --slm-map-entities --slm-confidence-threshold 0.9
```

---

### `--slm-context-window <n>`

**Default:** `200` (characters)

**What it does:** The number of characters before and after each detected entity to include as context in the SLM mapper output. Larger windows give more surrounding context.

```bash
./docker/run.sh ./report.txt --slm-map-entities --slm-context-window 400
```

---

### `--slm-temperature <n>`

**Default:** `0.0`

**What it does:** Controls the randomness of the SLM's output. `0.0` is fully deterministic (best for structured tasks). Higher values produce more varied output.

```bash
./docker/run.sh ./report.txt --slm-map-entities --slm-temperature 0.1
```

---

## 12. Ollama Service Options (Experimental)

These options control how the tool manages the Ollama service that runs the local SLM.

---

### `--no-auto-ollama`

**Default:** off (auto-management is enabled)

**What it does:** Disables automatic Ollama Docker container management. By default, the tool starts an Ollama container if one is not already running. With this flag, you must start Ollama manually before running the tool.

```bash
# You started Ollama yourself; tell the tool not to touch it
./docker/run.sh ./report.txt --slm-map-entities --no-auto-ollama
```

---

### `--ollama-docker-image <image>`

**Default:** `ollama/ollama:latest`

**What it does:** Specifies which Docker image to use when the tool starts an Ollama container automatically.

```bash
./docker/run.sh ./report.txt --slm-map-entities --ollama-docker-image ollama/ollama:0.3.0
```

---

### `--ollama-container-name <name>`

**Default:** `ollama-anon`

**What it does:** Sets the name of the Ollama Docker container managed by the tool.

```bash
./docker/run.sh ./report.txt --slm-map-entities --ollama-container-name my-ollama
```

---

### `--ollama-no-gpu`

**Default:** off (GPU is used if available)

**What it does:** Disables GPU support when starting the Ollama Docker container. Use this if your GPU is not compatible or you want the SLM to run on CPU.

```bash
./docker/run.sh ./report.txt --slm-map-entities --ollama-no-gpu
```

---

## 13. Quick Reference Table

| Argument | Default | Description |
|----------|---------|-------------|
| `file_path` | — | File or folder to anonymize **(required)** |
| `--list-entities` | — | Print all supported entity types and exit |
| `--list-languages` | — | Print all supported languages and exit |
| `--lang` | `en` | Document language code |
| `--output-dir` | `output` | Where to save anonymized files |
| `--overwrite` | off | Overwrite existing output files |
| `--no-report` | off | Skip the performance report in `logs/` |
| `--log-level` | `WARNING` | Verbosity: `DEBUG` `INFO` `WARNING` `ERROR` `CRITICAL` |
| `--preserve-entities` | — | Comma-separated entity types to skip |
| `--allow-list` | — | Comma-separated terms to never anonymize |
| `--slug-length` | `64` | Length of the hash suffix in pseudonyms (0–64) |
| `--anonymization-config` | — | Path to JSON config for field-level control |
| `--word-list` | — | Path to JSON file of known terms to always anonymize |
| `--preserve-row-context` | off | Process every CSV/XLSX cell individually |
| `--json-stream-threshold-mb` | `100` | Stream JSON files larger than this many MB |
| `--optimize` | off | Enable all performance optimizations |
| `--use-cache` / `--no-use-cache` | on | Enable/disable in-memory result cache |
| `--max-cache-size` | `10000` | Maximum entries in the cache |
| `--min-word-length` | `0` | Skip tokens shorter than this (characters) |
| `--skip-numeric` | off | Skip purely numeric strings |
| `--regex-priority` | off | Prioritize regex over model detections |
| `--force-large-xml` | off | Override XML memory safety limits |
| `--disable-gc` | off | Disable Python garbage collection |
| `--anonymization-strategy` | `filtered` | Detection engine: `filtered` `presidio` `hybrid` `standalone` `slm` |
| `--transformer-model` | `Davlan/xlm-roberta-base-ner-hrl` | NER model to use |
| `--db-mode` | `persistent` | Database mode: `persistent` or `in-memory` |
| `--db-dir` | `db` | Directory for the database file |
| `--db-synchronous-mode` | — | SQLite sync PRAGMA: `OFF` `NORMAL` `FULL` `EXTRA` |
| `--batch-size` | `1000` | Processing batch size (or `auto`) |
| `--csv-chunk-size` | `1000` | Rows per CSV read chunk |
| `--json-chunk-size` | `1000` | Items per JSON streaming chunk |
| `--ner-chunk-size` | `1500` | Max characters per NER text chunk |
| `--nlp-batch-size` | `500` | Batch size for spaCy's pipe |
| `--use-datasets` | off | Use HuggingFace datasets for GPU batch processing |
| `--generate-ner-data` | off | Generate NER training data instead of anonymizing |
| `--ner-include-all` | off | Include texts with no detected entities in NER output |
| `--ner-aggregate-record` | off | Merge JSON/JSONL record fields into one text line |
| `--slm-map-entities` | off | Map entities with SLM (no anonymization) |
| `--slm-detector` | off | Use SLM as an additional entity detector |
| `--slm-detector-mode` | `hybrid` | `hybrid` or `exclusive` |
| `--slm-prompt-version` | `v1` | Prompt template version for SLM |
| `--slm-chunk-size` | `2000` | Max chars per SLM mapper chunk |
| `--slm-anonymizer-chunk-size` | `3000` | Max chars per SLM anonymizer chunk |
| `--slm-confidence-threshold` | `0.7` | Minimum SLM confidence to accept an entity |
| `--slm-context-window` | `200` | Context characters around each entity in SLM output |
| `--slm-temperature` | `0.0` | SLM output randomness (0 = deterministic) |
| `--no-auto-ollama` | off | Disable automatic Ollama Docker management |
| `--ollama-docker-image` | `ollama/ollama:latest` | Ollama Docker image |
| `--ollama-container-name` | `ollama-anon` | Ollama container name |
| `--ollama-no-gpu` | off | Disable GPU for Ollama container |
