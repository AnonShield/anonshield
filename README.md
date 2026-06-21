# AnonShield

[![Best Artifact at SBRC 2026](https://img.shields.io/badge/SBRC%202026-Best%20Artifact-gold)](https://doc-artefatos.github.io/sbrc2026/results.html#trabalhos-com-selos-atribu%C3%ADdos)
[![DOI](https://img.shields.io/badge/DOI-10.5753%2Fsbrc__estendido.2026.23154-blue)](https://doi.org/10.5753/sbrc_estendido.2026.23154)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

**Scalable, on-premise pseudonymization for CSIRT network vulnerability data and other sensitive documents.**

AnonShield replaces personally identifiable information (PII) and network-specific identifiers (IP addresses, hostnames, TLS certificates, service fingerprints, CVE references) with cryptographically secure, **deterministic** pseudonyms based on HMAC-SHA256. Because the same input always maps to the same pseudonym, **referential integrity is preserved across documents and runs**, so a Computer Security Incident Response Team (CSIRT) can share vulnerability scans and incident data under GDPR and LGPD without losing analytical utility. Nothing leaves the host: detection, replacement, and the mapping store all run locally.

> This is the **active development** repository. The frozen artifact that backs the SBRC 2026 paper (selected **Best Artifact**) lives at [AnonShield/tool](https://github.com/AnonShield/tool) and is the version to use for reproducing the published experiments.

---

## Table of contents

- [Why AnonShield](#why-anonshield)
- [Highlights](#highlights)
- [How it works](#how-it-works)
- [Anonymization strategies](#anonymization-strategies)
- [NER models](#ner-models)
- [Supported formats and entities](#supported-formats-and-entities)
- [Installation](#installation)
- [Quick start (CLI)](#quick-start-cli)
- [Configuration](#configuration)
- [Web application](#web-application)
- [Deployment](#deployment)
- [Reproducing the paper](#reproducing-the-paper)
- [Research lineage](#research-lineage)
- [Performance](#performance)
- [Security](#security)
- [Citation](#citation)
- [Contributing](#contributing)
- [License](#license)

---

## Why AnonShield

Vulnerability scan reports (OpenVAS, Tenable, and similar) and security incident tickets are full of identifiers that, taken together, map an organization's network topology and attack surface: IP ranges, hostnames, certificates, service banners, CVE references, e-mail addresses, and personal names. Sharing this data with partners, researchers, or training pipelines is exactly what makes collective defense work, yet it is precisely what privacy regulation restricts.

AnonShield solves this with **pseudonymization rather than redaction**. Instead of deleting sensitive values (which destroys the structure analysts depend on), it substitutes each value with a stable pseudonym, keeping the document usable for correlation, statistics, and machine learning, while the original values stay protected and can be restored on the host with the secret key (controlled re-identification).

It is built for **operational CSIRT scale**: evaluated on datasets up to **550 MB / 70,951 vulnerability records**, it brings processing that previously took over **92 hours down to under 10 minutes** (up to **738x** faster) while reaching **F1 = 94.2%** and **Recall = 96.4%** on a specialist-annotated validation set.

## Highlights

- **Deterministic pseudonyms (HMAC-SHA256).** The same entity always receives the same pseudonym across files and runs, so cross-document references stay intact. Reversible on the host with the secret key.
- **On-premise by design.** No external API calls and no telemetry. Sensitive data never leaves your network.
- **Five anonymization strategies** spanning pure regex (no model load) to full Presidio NER, so you trade off speed against coverage per job (see [below](#anonymization-strategies)).
- **Two focused NER models:** a multilingual general model and a cybersecurity-tuned model.
- **Schema-aware control.** For structured files (CSV, XLSX, JSON, XML) you can force, skip, or auto-detect anonymization per field.
- **Entity selection.** Anonymize only the exact entity types you choose, preserve specific types, and keep an allow-list of terms that must never be touched.
- **Custom regex recognizers** for domain-specific identifiers (CPF, CNPJ, IBAN, employee IDs, internal asset tags) without changing source code.
- **Multi-format input,** including text, CSV, JSON/JSONL, XML, PDF, DOCX, XLSX, ZIP archives, and scanned documents and images through Tesseract OCR.
- **Built for scale:** O(n) streaming processors, an LRU entity cache, and a configurable mapping database.
- **Two ways to run:** a full-featured command-line tool (`anon.py`) and a web application (drag-and-drop upload, real-time progress, batch processing, per-job entity selection, and a metrics dashboard).

## How it works

```
input file ──► extract text (incl. Tesseract OCR for PDF/images)
            └► detect entities ── NER model + regex recognizers + Presidio
                                 (which detectors run depends on the strategy)
                       └► for each detected value:
                            HMAC-SHA256(value, secret key) ──► stable pseudonym
                            record value <─> pseudonym in the mapping store
                       └► write anonymized file + a performance report
```

1. **Extraction.** Each format has a dedicated processor (streaming where it helps for large files). Scanned PDFs and images go through Tesseract OCR.
2. **Detection.** Entities are found by a transformer NER model, Presidio recognizers, and regular-expression recognizers (including any custom patterns you supply). The active anonymization **strategy** decides which of these run and how aggressively.
3. **Replacement.** Every detected value is hashed with HMAC-SHA256 using your secret key and replaced by a deterministic pseudonym of configurable length. Identical values always produce identical pseudonyms.
4. **Mapping and caching.** The value-to-pseudonym mapping is stored (persistent SQLite by default, or in-memory), and an LRU cache keeps hot entities in memory for throughput. The mapping store is what makes **controlled re-identification** possible later.

## Anonymization strategies

Choose with `--anonymization-strategy` (CLI) or the strategy selector (web).

| Strategy | What it does | When to use |
|---|---|---|
| **`filtered`** (default) | Presidio pipeline with a curated recognizer scope (transformer NER + regex), tuned for CSIRT data | Best balance of accuracy and performance; the recommended default |
| **`hybrid`** | Filtered detection plus a lightweight replacement path | Same detection accuracy as `filtered` with lower overhead |
| **`standalone`** | Direct transformer inference | Highest throughput for large batches |
| **`presidio`** | The full Presidio pipeline | Maximum entity coverage |
| **`regex`** | Pure regular expressions, no model is loaded | Fastest path; ideal for structured data and CI pipelines |
| **`slm`** (experimental) | Small language model via a local Ollama container | Research and experimentation |

## NER models

Select with `--transformer-model`. Two models ship configured:

| Model | Focus |
|---|---|
| `Davlan/xlm-roberta-base-ner-hrl` (default) | General, multilingual named-entity recognition |
| `attack-vector/SecureModernBERT-NER` | Cybersecurity-tuned recognition (network and threat artifacts) |

Models are downloaded on first use and cached locally. The build uses **CPU PyTorch** so it runs on hosts without a GPU.

## Supported formats and entities

**Formats:** plain text, CSV, JSON, JSONL, XML, PDF, DOCX, XLSX, ZIP archives, and common image formats (PNG, JPG, TIFF) through Tesseract OCR.

**Entity types** include `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `IP_ADDRESS`, `MAC_ADDRESS`, `HOSTNAME`, `URL`, `LOCATION`, `ORGANIZATION`, `DATE_TIME`, `CREDIT_CARD`, `IBAN_CODE`, `CVE`, plus Brazilian identifiers such as `BR_CPF` and `BR_CNPJ`. Run the command below for the full, version-accurate list:

```bash
uv run anon.py --list-entities
uv run anon.py --list-languages
```

## Installation

Requires **Linux**, **Python 3.12**, and [`uv`](https://astral.sh/uv).

```bash
# 1. Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and install dependencies
git clone https://github.com/AnonShield/anonshield.git
cd anonshield
uv sync

# 3. Set the HMAC secret key (required; keep it stable so pseudonyms stay consistent)
export ANON_SECRET_KEY=$(openssl rand -hex 32)
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.bashrc

# 4. (optional) Tesseract is only needed to OCR scanned PDFs and images
sudo apt install tesseract-ocr
```

## Quick start (CLI)

```bash
# Anonymize a single file with the default (filtered) strategy
uv run anon.py report.csv

# Pick a strategy and language
uv run anon.py report.xml --anonymization-strategy regex --lang pt

# Anonymize only specific entity types, and never touch a few terms
uv run anon.py incidents.json --entities PERSON,EMAIL_ADDRESS,IP_ADDRESS --allow-list "localhost,example.com"

# Use the cybersecurity NER model on a vulnerability scan
uv run anon.py scan.csv --transformer-model attack-vector/SecureModernBERT-NER

# Process an entire directory
uv run anon.py ./reports/ --output-dir ./anonymized/
```

Anonymized files are written to `output/` (configurable with `--output-dir`), and a per-run performance report is produced unless you pass `--no-report`.

### Useful flags

| Flag | Purpose |
|---|---|
| `--anonymization-strategy` | `filtered` (default), `hybrid`, `standalone`, `presidio`, `regex`, `slm` |
| `--transformer-model` | NER model to load |
| `--entities` / `--preserve-entities` | Anonymize only these types / keep these types untouched |
| `--allow-list` | Terms that must never be anonymized |
| `--anonymization-config` | JSON file with per-field rules for structured data |
| `--custom-patterns` | JSON file adding domain-specific regex recognizers |
| `--config` | YAML file persisting all run settings |
| `--slug-length` | Length of the generated pseudonym |
| `--ner-score-threshold` | Minimum NER confidence to keep a detection |
| `--db-mode` | `persistent` (default) or `in-memory` mapping store |
| `--lang` | Document language (default `en`) |

Run `uv run anon.py --help` for the complete reference.

## Configuration

- **`ANON_SECRET_KEY`** (required): the HMAC key. Keep it stable and protected; it is what links pseudonyms across runs and what allows controlled re-identification. Losing it makes de-anonymization impossible.
- **Schema-aware rules (`--anonymization-config`)**: a JSON file that, per field of a structured file, can force a value to be treated as a given entity, exclude a field entirely, or fall back to automatic detection. Bypassing detection for known fields is also the fastest path at scale.
- **Custom recognizers (`--custom-patterns`)**: add regular-expression detectors for identifiers specific to your environment.
- **YAML profiles (`--config`)**: capture an entire run configuration in one file for reproducibility.

## Web application

A browser front end for non-CLI users and for sharing the tool within a team.

- **Frontend:** SvelteKit single-page app with drag-and-drop upload, real-time progress, batch processing, per-job entity and strategy selection, and a metrics dashboard (throughput by file format and by strategy, entity-type distribution, jobs over time, file-size versus throughput, and latency percentiles).
- **Backend:** FastAPI API plus Celery workers and Redis for asynchronous jobs.

Run the whole stack locally in containers (CPU, no host reverse proxy):

```bash
cd web
ANON_SECRET_KEY=$(openssl rand -hex 32) PUBLIC_API_URL=http://localhost:18000 \
  docker compose -f docker-compose.prod.yml -f docker-compose.host.yml up --build
# frontend on http://localhost:13000 , API on http://localhost:18000
```

For frontend development with hot reload, run the dev servers directly instead:

```bash
docker run -d -p 6379:6379 redis:7-alpine                       # Redis for the job queue
cd web/backend && uv run uvicorn main:app --reload --port 8000  # API
cd web/backend && uv run celery -A workers.celery_app worker -Q fast --loglevel=info  # worker
cd web/frontend && npm install && npm run dev                   # UI on http://localhost:5173
```

## Deployment

Production deployment is one command and is fully scripted. From a developer machine:

```bash
./scripts/deploy.sh <host>           # sync, build, start, and warm the cache on the given ssh host
```

On the host (`web/` directory) everything else is a `make` target:

```bash
make            # list all commands
make deploy     # build, start, warm the cache, show status
make status     # container status and health
make logs       # follow logs (make logs SVC=backend to filter)
make restart    # restart the stack
make warm       # preload the NER model so the first request is fast
make down       # stop everything
```

See [`web/RUNBOOK.md`](web/RUNBOOK.md) for deploy, maintenance, modify-and-redeploy, configuration, and troubleshooting. The stack runs behind a reverse proxy (Caddy); the host override lives in `web/docker-compose.host.yml`.

## Reproducing the paper

The experiments, datasets, and step-by-step reproduction guide that earned the **SBRC 2026 Best Artifact** seals (Available, Functional, Sustainable, Reproducible) are in the frozen artifact repository: [AnonShield/tool](https://github.com/AnonShield/tool). Use that repository to reproduce the published numbers exactly.

## Research lineage

AnonShield is the third generation of a peer-reviewed line of on-premise pseudonymization tools for CSIRTs.

| Generation | Venue | Contribution | Key results |
|---|---|---|---|
| **AnonLFI v1.0** | SBSeg 2025 | Anonymizing natural-language incident reports for safe LLM use with controlled re-identification | 100% precision, 97.38% efficacy over 763 incidents ([paper](https://sol.sbc.org.br/index.php/sbseg/article/view/36614)) |
| **AnonLFI v2.0** | WRSeg / ERRC 2025 | Reversible pseudonymization (HMAC-SHA256) with OCR and technical recognizers, preserving XML and JSON structure | 100% precision, F1 92.13% (XML) and 76.5% (OCR) ([paper](https://sol.sbc.org.br/index.php/errc/article/view/39186)) |
| **AnonShield** | SBRC 2026 | High-throughput, streaming pseudonymization of network vulnerability scans at scale | F1 94.2%, Recall 96.4%, 738x faster ([paper](https://sol.sbc.org.br/index.php/sbrc_estendido/article/view/42580)) |

## Performance

On the AnonShield evaluation (network vulnerability scan reports):

- **F1 = 94.2%**, **Recall = 96.4%** on a specialist-annotated validation set (`filtered` / `hybrid` strategies).
- **Over 92 hours reduced to under 10 minutes**, up to **738x** faster than the unaccelerated baseline.
- Evaluated on datasets up to **550 MB** and **70,951 vulnerability records**.

## Security

- All processing is **local**: no data is transmitted to external services.
- The mapping database stores the value-to-pseudonym table; keep it secure, since losing it (or the key) makes de-anonymization impossible.
- Protect `ANON_SECRET_KEY`: it is required to correlate pseudonyms across runs and to re-identify.

See [SECURITY.md](.github/SECURITY.md) to report a vulnerability.

## Citation

If you use AnonShield in your research, please cite the SBRC 2026 paper:

```bibtex
@inproceedings{kapelinski2026anonshield,
  author    = {Cristhian Kapelinski and Douglas Lautert and Beatriz Roland Machado and Diego Kreutz and Isadora Garcia Ferrão},
  title     = {{AnonShield: Scalable On-Premise Pseudonymization for CSIRT Network Vulnerability Data}},
  booktitle = {Anais Estendidos do XLIV Simpósio Brasileiro de Redes de Computadores e Sistemas Distribuídos (SBRC)},
  year      = {2026},
  pages     = {1--12},
  publisher = {SBC},
  address   = {Porto Alegre, RS, Brasil},
  issn      = {2177-9384},
  doi       = {10.5753/sbrc_estendido.2026.23154},
  url       = {https://sol.sbc.org.br/index.php/sbrc_estendido/article/view/42580}
}
```

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](.github/CONTRIBUTING.md) and the [Code of Conduct](.github/CODE_OF_CONDUCT.md) before opening an issue or pull request.

For questions or to report a security issue directly: **anonshield@unipampa.edu.br**.

## License

Licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

Developed at UNIPAMPA in collaboration with UBO (Université de Bretagne Occidentale), with contributions from UFU, UFRGS, and SENAC.
