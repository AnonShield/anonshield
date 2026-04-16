# AnonShield: Scalable On-Premise Pseudonymization

AnonShield is a pseudonymization framework designed for secure and compliant data sharing. It replaces Personally Identifiable Information (PII) and sensitive indicators with cryptographically secure, deterministic pseudonyms (HMAC-SHA256), preserving referential integrity across documents while ensuring GDPR/LGPD compliance.

## Key Features

- **Multi-Format Support**: Process JSON, CSV, XML, PDF, DOCX, XLSX, and plain text.
- **GPU-Accelerated NER**: Fast entity detection using state-of-the-art transformer models.
- **Scalable Architecture**: O(n) streaming processors for handling large files (tested up to 550 MB+).
- **Referential Integrity**: Uses HMAC-SHA256 to ensure the same entity always receives the same pseudonym across different files and runs.
- **Schema-Aware Configuration**: Fine-grained control over which fields to anonymize in structured files.
- **On-Premise**: Process sensitive data entirely locally without external API dependencies.
- **Multiple Anonymization Strategies**: `filtered`, `presidio`, `hybrid`, `standalone`, and `regex` (zero NLP overhead — pure regex, fastest of all).
- **Multi-Engine OCR**: Choose from Tesseract, EasyOCR, PaddleOCR, DocTR, or Keras-OCR via `--ocr-engine`.
- **Image Preprocessing**: Apply a configurable pipeline before OCR — grayscale, 300-DPI upscale, CLAHE contrast, Gaussian denoise, auto-deskew, adaptive binarization, morphological cleanup, and border padding. Pre-built presets for scanned documents, camera photos, and fax/low-quality images.
- **YAML Config Profiles**: Persist all run settings in a YAML file (`--config`); pre-built profiles for banking documents.
- **Custom Regex Patterns**: Add domain-specific detectors (CPF, CNPJ, IBAN, employee IDs…) without modifying source code (`--custom-patterns`).
- **Entity Selection**: Anonymize only the exact types you specify (`--entities`), complementing the existing exclusion list (`--preserve-entities`).
- **Web Interface**: Full-featured browser UI with drag-and-drop upload, real-time progress, batch processing, and per-session entity selection.
- **Specialized NER Models**: Choose from 8 pre-configured transformer models covering general, clinical, financial, biomedical, and cybersecurity domains.

## Installation

### Local Setup (Linux)

1. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and Install**:
   ```bash
   git clone https://github.com/AnonShield/tool.git
   cd tool
   uv sync
   ```

3. **Set your Secret Key**:
   ```bash
   export ANON_SECRET_KEY=$(openssl rand -hex 32)
   ```

### Docker (Recommended)

Run AnonShield without installing Python dependencies:

```bash
chmod +x run.sh
export ANON_SECRET_KEY=$(openssl rand -hex 32)
./run.sh ./your_file.csv
```

## Quick Start

Anonymize a file using the default settings:

```bash
uv run anon.py path/to/your/file.txt
```

Regex-only mode (no model loading — fastest):

```bash
uv run anon.py ./banking_docs/ \
  --anonymization-strategy regex \
  --custom-patterns examples/patterns/banking_pt.yaml \
  --entities "CPF,EMAIL_ADDRESS,CREDIT_CARD"
```

Apply preprocessing before OCR (scanned documents):

```bash
# Use a named preset
uv run anon.py ./scanned_invoice.pdf --ocr-preprocess-preset scan

# Or select steps explicitly
uv run anon.py ./photo.jpg \
  --ocr-preprocess "grayscale,upscale,clahe,denoise,deskew,binarize,border"
```

Use a pre-configured profile:

```bash
uv run anon.py ./invoice.pdf --config examples/profiles/banking_pt.yaml
```

List all supported entity types:

```bash
uv run anon.py --list-entities
```

## Reproducing the Paper Experiments

A single script provisions the environment, downloads the datasets (XFUND-pt, BID Sample), runs the full OCR preprocess ablation sweep, and prints the consolidated ranking:

```bash
./run_experiments.sh            # full run (100 samples × 9 preprocess configs × 5 engines)
./run_experiments.sh --quick    # fast smoke test (20 samples, 4 classical engines)
./run_experiments.sh --web      # same as full, and also launches the web UI
```

Outputs:

- `benchmark/ocr/results/<config>/ocr_benchmark_summary.csv` — per-config metrics
- `benchmark/ocr/results/ablation_consolidated.csv` — engine × preprocess pivot
- `benchmark/ocr/REPORT.md` — narrative summary with headline ranking
- `benchmark/ocr/METHODOLOGY.md` — metrics, statistical tests, normalization
- `benchmark/ocr/RESULTS_AUDIT.md` — fairness audit and sample I/O pairs

Partial results are usable mid-run: each configuration is independently resumable (per-doc keys in `run_state.json`), so stopping/restarting the script picks up where it left off.

## Web Interface

AnonShield includes a full-featured web application (SvelteKit + FastAPI) for browser-based processing.

**Quick start (production):**
```bash
cd web
echo "ANON_SECRET_KEY=$(openssl rand -hex 32)" > .env
# Edit web/Caddyfile — set your domain
docker compose -f docker-compose.prod.yml up -d
```

See [docs/web/SETUP.md](docs/web/SETUP.md) for the complete guide (production + development, environment variables, model download sizes, data privacy guarantees).

## Usage & Configuration

Detailed guides are available in the `docs/` directory:

- [Web Setup](docs/web/SETUP.md) — production deploy (Docker + Caddy) and local dev mode
- [CLI Reference](docs/users/CLI_REFERENCE.md) — every flag, with examples
- [Configuration File](docs/users/CONFIGURATION_FILE.md) — YAML config file schema and profiles
- [OCR Engines](docs/users/OCR_ENGINES.md) — comparison of all 13 OCR engines (classical, deep-learning, VLM)
- [Architecture Overview](docs/developers/ARCHITECTURE.md)
- [Extensibility Guide](docs/developers/EXTENSIBILITY.md) — how to add strategies, OCR engines, models, patterns
- [Anonymization Strategies](docs/developers/ANONYMIZATION_STRATEGIES.md)
- [SLM Integration Guide](docs/developers/SLM_INTEGRATION_GUIDE.md)

## Security

- **Deterministic**: Pseudonyms are derived from your `ANON_SECRET_KEY`. Keep this key safe to maintain (or regain) the ability to de-anonymize data.
- **Local-Only**: No data leaves your machine. All detection and processing happen strictly on-premise.

## License

This project is licensed under the **GNU General Public License v3.0**.
