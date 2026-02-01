# AnonLFI 3.0: Extensible Architecture for PII Pseudonymization in CSIRTs

AnonLFI 3.0 is a modular pseudonymization framework for CSIRTs that resolves the conflict between data confidentiality (GDPR/LGPD) and analytical utility. It uses HMAC-SHA256 to generate strong, reversible pseudonyms, natively preserves XML and JSON structures, and integrates an OCR pipeline and specialized technical recognizers to handle PII in complex security artifacts.

## Tags

| Tag | Base | Description |
|-----|------|-------------|
| `latest` | `python:3.12-slim` | CPU-only runtime. Works on any machine. |
| `gpu` | `nvidia/cuda:12.1.1` | NVIDIA GPU accelerated. Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html). |

## Quick Start

```bash
docker pull kapelinsky/anon

docker run --rm \
  -e ANON_SECRET_KEY="your-secret-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/input.txt
```

Output is written to `/data/output/` by default.

## Key Features

- **Structure-Preserving Processing:** Natively processes `.json`, `.xml`, `.csv`, `.txt`, `.pdf`, `.docx`, and `.xlsx` files preserving their original hierarchy.
- **OCR for Images:** Extracts and anonymizes text from images in PDF/DOCX files and standalone image files (`.png`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`).
- **Advanced Entity Recognition:** Uses Presidio + Transformer models (`Davlan/xlm-roberta-base-ner-hrl`) for high-accuracy entity detection.
- **SLM-Powered Anonymization:** Integrates Small Language Models (SLMs) via Ollama for context-aware entity detection and anonymization.
- **Cybersecurity-Focused Recognizers:** Detects IP addresses, URLs, hostnames, hashes, UUIDs, CVE IDs, CPE strings, certificate serials, MAC addresses, PGP blocks, and more.
- **Consistent & Secure Anonymization:** HMAC-SHA256-based slugs ensure the same entity always maps to the same pseudonym.
- **Controlled De-anonymization:** Reverse anonymization protected by the same secret key.
- **24 Languages Supported:** Including English, Portuguese, Spanish, French, German, Italian, and more.

## Usage Examples

### Anonymize a text file
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/document.txt
```

### Anonymize a CSV with language selection
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/data.csv --lang pt
```

### Anonymize a JSON with custom config
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  -v $(pwd)/my_config.json:/app/anonymization_config.json \
  kapelinsky/anon /data/data.json --anonymization-config /app/anonymization_config.json
```

### Process an entire directory
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd)/docs:/data \
  kapelinsky/anon /data/
```

### GPU mode
```bash
docker run --rm --gpus all \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  kapelinsky/anon:gpu /data/document.txt
```

### SLM mode (with Ollama)
```bash
# Start Ollama first, then:
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -e OLLAMA_BASE_URL="http://host.docker.internal:11434" \
  -v $(pwd):/data \
  kapelinsky/anon /data/report.txt --slm-detector --slm-detector-mode hybrid
```

### Persist models across runs
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  -v anon-models:/app/models \
  kapelinsky/anon /data/document.txt
```

### Persist database (for de-anonymization)
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  -v anon-db:/app/db \
  kapelinsky/anon /data/document.txt --db-mode persistent --db-dir /app/db
```

### Custom slug length
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/report.pdf --slug-length 12
```

### Fast mode with optimizations
```bash
docker run --rm \
  -e ANON_SECRET_KEY="my-key" \
  -v $(pwd):/data \
  kapelinsky/anon /data/large_dataset/ --optimize
```

### Generate NER training data (no secret key needed)
```bash
docker run --rm \
  -v $(pwd):/data \
  kapelinsky/anon /data/corpus/ --generate-ner-data --output-dir /data/ner_output/
```

## Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `ANON_SECRET_KEY` | **Yes** (for anonymization) | Encryption key for HMAC-SHA256 pseudonym generation. | — |
| `ANON_LAZY_LOADING` | No | Download ML models on first use. | `1` |
| `ANON_PRELOAD` | No | Comma-separated models to preload (e.g. `spacy:en_core_web_lg`). | — |
| `OLLAMA_BASE_URL` | No | Ollama service URL for SLM features. | `http://ollama:11434` |

## Volumes

| Path | Description |
|------|-------------|
| `/app/models` | Cached ML models (spaCy, transformers). Mount to persist across runs. |
| `/app/output` | Default output directory for anonymized files. |
| `/app/db` | SQLite database for entity mapping (needed for de-anonymization). |

## Supported Entities

`PERSON`, `ORGANIZATION`, `LOCATION`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `IP_ADDRESS`, `URL`, `HOSTNAME`, `MAC_ADDRESS`, `HASH`, `UUID`, `CVE_ID`, `CPE_STRING`, `CERT_SERIAL`, `PGP_BLOCK`, `AUTH_TOKEN`, `PASSWORD`, `USERNAME`, `FILE_PATH`, and more.

Run `docker run --rm kapelinsky/anon --list-entities` for the full list.

## Supported Languages (24)

`ca` Catalan, `zh` Chinese, `hr` Croatian, `da` Danish, `nl` Dutch, `en` English, `fi` Finnish, `fr` French, `de` German, `el` Greek, `it` Italian, `ja` Japanese, `ko` Korean, `lt` Lithuanian, `mk` Macedonian, `nb` Norwegian, `pl` Polish, `pt` Portuguese, `ro` Romanian, `ru` Russian, `sl` Slovenian, `es` Spanish, `sv` Swedish, `uk` Ukrainian.

## Anonymization Strategies

| Strategy | Command | Description |
|----------|---------|-------------|
| `presidio` | `--anonymization-strategy presidio` | Full analysis with all recognizers. Highest accuracy. **(Default)** |
| `fast` | `--anonymization-strategy fast` | Transformer + regex only. Fastest. |
| `balanced` | `--anonymization-strategy balanced` | Curated subset of recognizers. Good balance. |
| `slm` | `--anonymization-strategy slm` | End-to-end LLM-based anonymization via Ollama. |

## Common Flags

```
--lang LANG                     Language code (en, pt, es, ...). Default: en
--output-dir DIR                Output directory. Default: ./output
--anonymization-strategy STR    presidio | fast | balanced | slm
--transformer-model MODEL       NER model (default: Davlan/xlm-roberta-base-ner-hrl)
--preserve-entities TYPES       Comma-separated entity types to skip
--allow-list TERMS              Comma-separated terms to never anonymize
--slug-length N                 Length of anonymized slugs (1-64)
--optimize                      Enable all performance optimizations
--generate-ner-data             Generate NER training data instead of anonymizing
--db-mode MODE                  persistent | in-memory
--slm-detector                  Use SLM as additional entity detector
--slm-detector-mode MODE        hybrid | exclusive
--help                          Show all options
```

## Docker Compose Usage

For more complex setups (GPU, SLM with Ollama), use the provided `docker-compose.yml`:

```bash
# CPU profile
docker compose -f docker/docker-compose.yml --profile cpu run --rm anon /data/input/file.txt

# GPU profile
docker compose -f docker/docker-compose.yml --profile gpu run --rm anon-gpu /data/input/file.txt

# SLM profile (auto-starts Ollama)
docker compose -f docker/docker-compose.yml --profile slm run --rm anon /data/input/file.txt --slm-detector
```

Or use the `run.sh` wrapper for automatic profile detection:

```bash
./run.sh /data/input/file.txt                      # CPU
./run.sh /data/input/file.txt --slm-detector       # CPU + Ollama
./run.sh --gpu /data/input/file.txt                # GPU
./run.sh --gpu /data/input/file.txt --slm-detector # GPU + Ollama
```

## Source Code

[github.com/AnonShield/AnonLFI3.0](https://github.com/AnonShield/AnonLFI3.0)
