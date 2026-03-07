# AnonLFI 3.0 — PII Pseudonymization for CSIRTs

AnonLFI 3.0 is a modular pseudonymization framework for Cybersecurity Incident Response Teams (CSIRTs). It anonymizes personally identifiable information (PII) and cybersecurity indicators using HMAC-SHA256, generating stable and reversible pseudonyms. It natively preserves the structure of JSON, XML, and CSV files, integrates OCR for PDFs and images, and ships with specialized recognizers for cybersecurity artifacts (IP addresses, CVE IDs, hashes, URLs, and more).

Designed to help teams share incident data, comply with GDPR/LGPD, and feed anonymized datasets into security tools — without sacrificing analytical utility.

---

## Requirements

### Docker (Recommended)

The only prerequisite is [Docker](https://docs.docker.com/get-docker/). All other dependencies — Python, Tesseract, spaCy, and transformer models — are bundled inside the container and managed automatically.

- **GPU:** Also requires an NVIDIA GPU and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

### Local Installation

- Python 3.12 with [`uv`](https://astral.sh/uv):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Tesseract OCR (required for PDF, image, and DOCX files):
  - Ubuntu/Debian: `sudo apt update && sudo apt install tesseract-ocr`
  - macOS: `brew install tesseract`
  - Windows: [Tesseract documentation](https://github.com/tesseract-ocr/tesseract#installing-tesseract)
- **GPU only:** NVIDIA drivers compatible with CUDA 12.8+

---

## Setup

```bash
git clone https://github.com/AnonShield/AnonLFI3.0.git
cd AnonLFI3.0
```

**Docker:**
```bash
chmod +x docker/run.sh
```

**Local (CPU):**
```bash
uv sync
```

**Local (GPU):** after `uv sync`, install the CUDA 12.8 PyTorch build and CuPy:
```bash
uv sync
.venv/bin/pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install cupy-cuda12x==12.3.0
```

---

## Setting the Secret Key

The secret key is **required** for anonymization (except when using `--slug-length 0`). It is used to generate pseudonyms and must be kept safe — you will need it again to de-anonymize output later.

**Linux / macOS:**
```bash
export ANON_SECRET_KEY=$(openssl rand -hex 32)
# To persist across sessions:
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.bashrc
```

**Windows (PowerShell):**
```powershell
$env:ANON_SECRET_KEY = [System.BitConverter]::ToString([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).Replace("-","").ToLower()
```

---

## Anonymizing a File

### Local

```bash
# Single file — output saved to output/anon_<filename>.<ext>
uv run anon.py path/to/your/file.txt

# Entire directory (recursive)
uv run anon.py path/to/your/directory/
```

### Docker

> The pre-built image is available on [Docker Hub](https://hub.docker.com/repository/docker/anonshield/anon/general). For end-users installing via Docker Hub, follow the quick-start steps there (download wrapper script → set key → anonymize).

Pass any local file or folder path directly — the script handles volume mounting automatically:

**CPU:**
```bash
./docker/run.sh ./your_file.csv
```

**GPU:**
```bash
./docker/run.sh --gpu ./your_file.csv
```

**Entire folder:**
```bash
./docker/run.sh ./reports/
```

Output lands in `./anon/output/` (created automatically). On first run, NER models (~1–2 GB) are downloaded and cached in `./anon/models/` for all subsequent runs.

Output files are named `anon_<original_filename>.<ext>`.

---

## De-anonymization

To recover the original value for a pseudonymized slug, you need the **database** (`db/entities.db`) that was created during the anonymization run. No secret key is required for lookup — the mapping is stored directly in the database.

```bash
uv run scripts/deanonymize.py "[PERSON_a1b2c3d4]"
```

> Keep the `db/` folder safe — it is the only way to reverse the anonymization.

---

## Common Options

| Option | Description | Default |
|:-------|:------------|:--------|
| `--lang <code>` | Document language (e.g., `en`, `pt`, `es`) | `en` |
| `--output-dir <path>` | Output directory for anonymized files | `output/` |
| `--preserve-entities <types>` | Comma-separated entity types to skip (e.g., `LOCATION,IP_ADDRESS`) | — |
| `--allow-list <terms>` | Comma-separated terms to never anonymize | — |
| `--slug-length <n>` | Hash length in the pseudonym (0–64). `0` = type label only, no key needed. | `64` |
| `--word-list <path>` | Path to a JSON file of known terms to always anonymize | — |
| `--anonymization-strategy <s>` | Detection engine: `filtered` (default), `presidio`, `hybrid`, `standalone` | `filtered` |
| `--anonymization-config <path>` | JSON config for field-level control in structured files | — |
| `--optimize` | Enable all performance optimizations at once | off |

For the complete argument reference with examples for every option, see **[docs/users/CLI_REFERENCE.md](docs/users/CLI_REFERENCE.md)**.

---

## Supported File Formats

`.txt` `.log` `.csv` `.xlsx` `.json` `.jsonl` `.xml` `.pdf` `.docx` `.png` `.jpg` `.gif` `.bmp` `.tiff` `.webp`

---

## Detected Entity Types

**Standard PII:**
`PERSON`, `LOCATION`, `ORGANIZATION`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `USERNAME`, `PASSWORD`

**Cybersecurity (custom recognizers):**
`IP_ADDRESS`, `URL`, `HOSTNAME`, `MAC_ADDRESS`, `FILE_PATH`, `HASH`, `AUTH_TOKEN`, `CVE_ID`, `CPE_STRING`, `CERT_SERIAL`, `CERTIFICATE`, `CRYPTOGRAPHIC_KEY`, `UUID`, `PGP_BLOCK`, `PORT`, `OID`

Run `uv run anon.py --list-entities` for the full list, or `--list-languages` for the 24 supported languages.

---

## Anonymization Strategies

Choose with `--anonymization-strategy <name>`:

| Strategy | F1 (accuracy) | GPU throughput | Description |
|----------|:-------------:|:--------------:|-------------|
| `filtered` (default) | **94.2 %** | 627 KB/s | Best accuracy. Curated Presidio recognizer set. |
| `hybrid` | **94.2 %** | 632 KB/s | Same accuracy, manual text replacement. |
| `standalone` | 91.1 % | **1,250 KB/s** | Fastest on GPU. Bypasses Presidio entirely. |
| `presidio` | 82.3 % | 575 KB/s | Full Presidio pipeline, more false positives. |

> On GPU, `standalone` is **~4× faster** than `presidio`. On CPU the gap is ~15 %. Use `filtered` for accuracy, `standalone` for maximum GPU throughput.

See [docs/developers/ANONYMIZATION_STRATEGIES.md](docs/developers/ANONYMIZATION_STRATEGIES.md) for full benchmarks.

---

## Running Tests

```bash
uv run python -m unittest discover tests/
```

---

## Documentation

**For users:**

| Document | Description |
|----------|-------------|
| [docs/users/CLI_REFERENCE.md](docs/users/CLI_REFERENCE.md) | **Complete CLI reference** — every argument explained with examples |

**For developers:**

| Document | Description |
|----------|-------------|
| [docs/developers/ARCHITECTURE.md](docs/developers/ARCHITECTURE.md) | System architecture, components, DB schema, and design patterns |
| [docs/developers/ANONYMIZATION_STRATEGIES.md](docs/developers/ANONYMIZATION_STRATEGIES.md) | Strategy internals, regex patterns, and benchmark comparisons |
| [docs/developers/UTILITY_SCRIPTS_GUIDE.md](docs/developers/UTILITY_SCRIPTS_GUIDE.md) | Helper scripts (de-anonymization, DB export, metrics) |
| [docs/developers/EVALUATION_GUIDE.md](docs/developers/EVALUATION_GUIDE.md) | Evaluation workflow with ground truth annotation and metrics |
| [docs/developers/SLM_INTEGRATION_GUIDE.md](docs/developers/SLM_INTEGRATION_GUIDE.md) | SLM/Ollama integration and experimental features |
| [benchmark/README.md](benchmark/README.md) | Benchmarking suite documentation |

## License
