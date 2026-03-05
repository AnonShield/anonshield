# AnonLFI 3.0: PII Pseudonymization Framework for CSIRTs

AnonLFI 3.0 is a modular pseudonymization framework for CSIRTs that resolves the conflict between data confidentiality (GDPR/LGPD) and analytical utility. It uses HMAC-SHA256 to generate stable, reversible pseudonyms, natively preserves XML and JSON structures, and integrates OCR and specialized cybersecurity recognizers to handle PII in complex security artifacts.

---

## Requirements

### Docker (Recommended)

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)
- **GPU only:** NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

All other dependencies (Python, Tesseract, spaCy, transformer models) are handled automatically inside the container. Models are downloaded on first use and cached in Docker volumes for subsequent runs.

### Local

- Python 3.12 with [`uv`](https://astral.sh/uv):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Tesseract OCR (for PDF/image/DOCX files):
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
chmod +x run.sh
```

**Local (CPU):**
```bash
uv sync
```

**Local (GPU):** after `uv sync`, replace torch with the CUDA 12.8 build and install CuPy:
```bash
uv sync
.venv/bin/pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install cupy-cuda12x==12.3.0
```

---

## Setting the Secret Key

The secret key is **required** for anonymization and de-anonymization. The tool will not run without it.

```bash
export ANON_SECRET_KEY='your-super-secret-key-here'
```

Keep this key safe — it is needed to de-anonymize output later.

---

## Anonymizing a File

### Local

```bash
# Single file → output saved to output/anon_<filename>.<ext>
uv run anon.py path/to/your/file.txt

# Entire directory (recursive)
uv run anon.py path/to/your/directory/
```

### Docker

The `run.sh` script mounts `../data` (relative to the project root) as `/data` inside the container. Place your input files there:

```bash
# From the project root (AnonLFI3.0/)
mkdir -p ../data
cp /path/to/your/file.txt ../data/

# Or point to a custom directory
export DATA_DIR=/absolute/path/to/your/data
```

**CPU (builds the image locally on first run):**
```bash
./run.sh /data/file.txt
```

**GPU (pulls the pre-built image `kapelinsky/anon:gpu` from Docker Hub):**
```bash
./run.sh --gpu /data/file.txt
```

> On first run, spaCy and transformer models (~1–2 GB) are downloaded automatically and cached in Docker volumes. GPU runs also pull the CUDA-enabled image (~5 GB) on first use.

**Retrieving the output** (output is stored in a Docker volume):
```bash
# After a CPU run
docker cp anon-cpu:/app/output ./output

# After a GPU run
docker cp anon-gpu:/app/output ./output
```

Output files are named `anon_<original_filename>.<ext>`.

---

## De-anonymization

To recover an original entity from a slug, use the same `ANON_SECRET_KEY`:

```bash
uv run scripts/deanonymize.py "[PERSON_a1b2c3d4]"
```

---

## Common Options

| Option | Description | Default |
|:-------|:------------|:--------|
| `--lang <code>` | Document language (e.g., `en`, `pt`) | `en` |
| `--output-dir <PATH>` | Output directory | `output/` |
| `--preserve-entities <TYPES>` | Entity types to skip (e.g., `LOCATION,HOSTNAME`) | — |
| `--allow-list <TERMS>` | Terms to ignore during anonymization | — |
| `--slug-length <NUM>` | Hash length in slug (0–64) | `64` |
| `--anonymization-strategy <s>` | `filtered` (default), `presidio`, `hybrid`, `standalone` | `filtered` |
| `--anonymization-config <PATH>` | JSON config for field-level control in structured files | — |
| `--optimize` | Enable all performance optimizations | off |

For the full options reference, performance tuning, and advanced configuration for structured files (JSON/XML/CSV), see [docs/ADVANCED_OPTIONS.md](docs/ADVANCED_OPTIONS.md).

---

## Supported File Formats

`.txt` `.log` `.csv` `.xlsx` `.json` `.jsonl` `.xml` `.pdf` `.docx` `.png` `.jpg` `.gif` `.bmp` `.tiff` `.webp`

## Detected Entity Types

**Standard PII:**
`PERSON`, `LOCATION`, `ORGANIZATION`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `USERNAME`, `PASSWORD`

**Cybersecurity (custom recognizers):**
`IP_ADDRESS`, `URL`, `HOSTNAME`, `MAC_ADDRESS`, `FILE_PATH`, `HASH`, `AUTH_TOKEN`, `CVE_ID`, `CPE_STRING`, `CERT_SERIAL`, `CERTIFICATE`, `CRYPTOGRAPHIC_KEY`, `UUID`, `PGP_BLOCK`, `PORT`, `OID`

Run `uv run anon.py --list-entities` for the full list, or `--list-languages` for the 24 supported languages.

---

## Running Tests

```bash
uv run python -m unittest discover tests/
```

---

## Documentation

- [docs/ADVANCED_OPTIONS.md](docs/ADVANCED_OPTIONS.md) — Full CLI reference, performance tuning, and advanced configuration for structured files
- [docs/ANONYMIZATION_STRATEGIES.md](docs/ANONYMIZATION_STRATEGIES.md) — Strategy selection, regex patterns, and benchmark comparisons
- [docs/EVALUATION_GUIDE.md](docs/EVALUATION_GUIDE.md) — Evaluation workflow with ground truth annotation and metrics
- [docs/UTILITY_SCRIPTS_GUIDE.md](docs/UTILITY_SCRIPTS_GUIDE.md) — Helper scripts (de-anonymization, evaluation, dataset generation)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — System architecture, components, DB schema, and design patterns
- [benchmark/README.md](benchmark/README.md) — Benchmarking suite documentation

## License
