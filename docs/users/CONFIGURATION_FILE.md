# Configuration File — YAML Run Config

The `--config` flag lets you store all run settings in a YAML (or JSON) file and reuse them across runs. CLI arguments always override the config file — the file only fills in values you have not set on the command line.

---

## Usage

```bash
# Load config, override slug-length on the command line
uv run anon.py ./report.csv --config examples/anon_config.example.yaml --slug-length 0

# Use a pre-configured banking profile
uv run anon.py ./invoice.pdf --config examples/profiles/banking_pt.yaml
```

---

## Full Schema

Every CLI option has a matching key in the config file. Below is the complete schema with types, defaults, and descriptions. See `examples/anon_config.example.yaml` for a fully commented template.

```yaml
# ─── Language ───────────────────────────────────────────────────────────────
lang: en                     # string  — document language (ISO 639-1 code)

# ─── Anonymization strategy ─────────────────────────────────────────────────
strategy: filtered           # string  — filtered | presidio | hybrid | standalone | regex | slm

# ─── NER transformer model ──────────────────────────────────────────────────
transformer_model: Davlan/xlm-roberta-base-ner-hrl   # HuggingFace model ID

# ─── Slug length ────────────────────────────────────────────────────────────
slug_length: 8               # integer 0–64  (0 = label only, no hash)

# ─── OCR engine ─────────────────────────────────────────────────────────────
ocr_engine: tesseract        # string  — tesseract | easyocr | paddleocr | doctr | kerasocr

# ─── Entity selection ────────────────────────────────────────────────────────
# Positive selection: ONLY these types are anonymized.
# If set, preserve_entities is ignored.
entities:
  - EMAIL_ADDRESS
  - IP_ADDRESS

# Entity types to skip (exclusion list). Ignored when 'entities' is set.
preserve_entities:
  - CVE_ID
  - URL

# ─── Allow list ─────────────────────────────────────────────────────────────
allow_list:
  - ACME Corp
  - internal-tool

# ─── Word list ──────────────────────────────────────────────────────────────
word_list: examples/word_list.example.json   # path to JSON word list file

# ─── Custom regex patterns ──────────────────────────────────────────────────
# Option A: path to a YAML/JSON patterns file
custom_patterns: examples/patterns/banking_pt.yaml

# Option B: inline pattern list (can be combined with a file via CLI)
# custom_patterns:
#   - entity_type: BANK_ACCOUNT
#     pattern: '\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}'
#     score: 0.9
#   - entity_type: IBAN
#     pattern: '[A-Z]{2}\d{2}[A-Z0-9]{1,30}'
#     score: 0.85
#     flags: IGNORECASE

# ─── Field-level anonymization (structured files) ────────────────────────────
anonymization_config: examples/anonymization_config.json   # path to JSON config

# ─── Database ────────────────────────────────────────────────────────────────
db_mode: persistent          # string  — persistent | in-memory

# ─── Logging ─────────────────────────────────────────────────────────────────
log_level: WARNING           # string  — DEBUG | INFO | WARNING | ERROR | CRITICAL

# ─── Regex priority ──────────────────────────────────────────────────────────
regex_priority: false        # boolean — prefer regex over NER for overlapping spans

# ─── Token filtering ─────────────────────────────────────────────────────────
min_word_length: 0           # integer — skip tokens shorter than this
skip_numeric: false          # boolean — skip purely numeric strings

# ─── Caching ─────────────────────────────────────────────────────────────────
use_cache: true              # boolean
max_cache_size: 10000        # integer

# ─── Batching ────────────────────────────────────────────────────────────────
batch_size: auto             # integer or "auto"

# ─── File handling ───────────────────────────────────────────────────────────
overwrite: false             # boolean — overwrite existing output files

# ─── Custom NER models ───────────────────────────────────────────────────────
# Register additional transformer models with their entity label mappings.
# Each entry requires 'id' and 'entity_mapping'; 'description' is optional.
# custom_models:
#   - id: my-org/domain-ner
#     entity_mapping:
#       PER: PERSON
#       ORG: ORGANIZATION
#       LOC: LOCATION
#     description: Domain-specific NER trained on internal corpus
```

---

## Merge Semantics

The config file is applied **before** CLI argument processing. The rule is:

> **CLI argument wins.** The config file only fills in values that are absent or at their default on the command line.

| Field type | CLI default | Config applied when… |
|------------|-------------|----------------------|
| `strategy`, `lang`, `ocr_engine` | empty string | CLI value is empty / default |
| `entities`, `preserve_entities` | empty string | CLI value is empty |
| `slug_length` | unset | CLI value is unset |
| `db_mode`, `log_level`, etc. | `None` | CLI value is `None` |
| `overwrite`, `use_cache`, etc. | `None` | CLI value is `None` |

---

## Pre-configured Profiles

AnonShield ships with two example profiles in `examples/profiles/`:

### `banking_pt.yaml` — Brazilian Banking Documents

Optimized for anonymizing Brazilian banking records:
- Strategy: `regex` (no model loading — maximum speed)
- Language: `pt`
- Entities: EMAIL, PHONE, IP, CREDIT_CARD, UUID, CPF, CNPJ, PIX keys, CEP, RG, bank account/agency
- Custom patterns: `examples/patterns/banking_pt.yaml`

```bash
uv run anon.py ./extrato.pdf --config examples/profiles/banking_pt.yaml
```

---

## Custom Pattern File Format

The `custom_patterns` key (or `--custom-patterns` flag) accepts a YAML or JSON file with this schema:

```yaml
# Each entry must have entity_type and pattern.
# score (float 0.0–1.0) and flags (IGNORECASE, MULTILINE) are optional.

- entity_type: CPF
  pattern: '\d{3}\.\d{3}\.\d{3}-\d{2}'
  score: 0.95

- entity_type: EMPLOYEE_ID
  pattern: 'EMP-\d{6}'
  score: 0.9
  flags: IGNORECASE
```

The `entity_type` string becomes the label in the anonymized output: `[CPF_a1b2c3d4]`.

---

## See Also

- [`docs/users/CLI_REFERENCE.md`](CLI_REFERENCE.md) — full argument reference
- [`docs/users/OCR_ENGINES.md`](OCR_ENGINES.md) — OCR engine comparison and installation
- [`examples/anon_config.example.yaml`](../../examples/anon_config.example.yaml) — fully commented template
- [`examples/patterns/banking_pt.yaml`](../../examples/patterns/banking_pt.yaml) — Brazilian banking patterns
