# AnonLFI: Comparative Evaluation of Pseudonymization Strategies for Large-Scale Vulnerability Datasets in CSIRTs

AnonLFI is a pseudonymization framework designed for Computer Security Incident Response Teams (CSIRTs). It replaces Personally Identifiable Information (PII) and cybersecurity indicators with cryptographically secure, deterministic pseudonyms (HMAC-SHA256), preserving referential integrity across documents while enabling GDPR/LGPD-compliant data sharing. Version 3.0 introduces four modular anonymization strategies, GPU acceleration, streaming processors for large files, and a schema-aware configuration mechanism. Evaluated on 70,951+ vulnerability records, it achieves more than 743× speedup over v2.0 and F1 = 94.2% with the `filtered`/`hybrid` strategies.

> **Paper:** *AnonLFI: Comparative Evaluation of Pseudonymization Strategies for Large-Scale Vulnerability Datasets in CSIRTs* — SBRC 2026 Salão de Ferramentas.

---

## README Structure

| Section | Description |
|---|---|
| [Considered Seals](#considered-seals) | SBRC quality seals targeted by this artifact |
| [Basic Information](#basic-information) | Hardware, OS, and software environment |
| [Dependencies](#dependencies) | Required packages and external tools |
| [Security Concerns](#security-concerns) | Risks and mitigations for evaluators |
| [Installation](#installation) | Step-by-step setup (local and Docker) |
| [Minimal Test](#minimal-test) | Quick functional verification (~2–5 min) |
| [Experiments](#experiments) | Reproduction of the three main paper claims |
| [License](#license) | Licensing information |

---

## Considered Seals

The seals considered are: **Available (SeloD)**, **Functional (SeloF)**, **Sustainable (SeloS)**, and **Reproducible Experiments (SeloR)**.

---

## Basic Information

| | |
|---|---|
| **Hardware (paper experiments)** | NVIDIA RTX 5060 Ti 16 GB VRAM · AMD Ryzen 5 8600G (6c/12t) · 32 GB DDR5 6000 MHz |
| **Minimum for smoke test** | 4 GB RAM · x86\_64 · Python 3.12 + uv |
| **Software** | Python 3.12 + [`uv`](https://astral.sh/uv) for all experiments; Docker optional (tool use only) |
| **GPU (optional)** | NVIDIA driver ≥ 525 (CUDA 12.8) + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| **OS** | Linux (tested and recommended); macOS/Windows supported via Docker only |
| **Disk** | ~2–3 GB (Python env + NER models); D1 dataset ~88 MB (in git); D3 dataset ~700 MB (public, **not** in git — download separately, see [Experiments](#experiments)) |

---

## Dependencies

**Python environment (all experiments):**
- Python 3.12 + [`uv`](https://astral.sh/uv) — all packages pinned in `pyproject.toml` / `uv.lock`
- Key packages: `presidio-analyzer`, `presidio-anonymizer`, `transformers`, `spacy`, `torch`, `pandas`, `pymupdf`, `pytesseract`, `lxml`, `orjson`, `scipy`, `statsmodels`
- NER models downloaded automatically on first run and cached in `anon/models/` (~1–2 GB)

**Optional:**
- Tesseract OCR — required only for OCR-mode tests (PDF/image files):
  ```bash
  sudo apt install tesseract-ocr  # Ubuntu/Debian
  ```
- Docker — for tool use only (not needed for experiments): `anonshield/anon:latest` (~2 GB CPU) or `anonshield/anon:gpu` (~6 GB GPU)

---

## Security Concerns

- AnonLFI processes sensitive cybersecurity data entirely **locally** — no data is transmitted to external services
- `db/entities.db` stores the PII entity mapping table — keep it secure; losing it makes de-anonymization impossible
- The HMAC secret key (`ANON_SECRET_KEY`) must be protected — it is required to correlate pseudonyms across separate runs
- The Docker `--gpu` flag passes `--gpus all` to the container; review this before use in shared environments

---

## Installation

### Local (recommended for experiments)

```bash
# 1. Clone the repository
git clone https://github.com/AnonShield/AnonLFI3.0.git
cd AnonLFI3.0

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install Python dependencies
uv sync

# 4. Set the HMAC secret key (required for pseudonymization)
export ANON_SECRET_KEY=$(openssl rand -hex 32)
# To persist across sessions:
echo "export ANON_SECRET_KEY=$ANON_SECRET_KEY" >> ~/.bashrc
```

**GPU only** — after `uv sync`, install CUDA-enabled PyTorch and CuPy:
```bash
.venv/bin/pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu128
.venv/bin/pip install cupy-cuda12x==12.3.0
```

### Docker (tool use only — not required for experiments)

```bash
curl -fsSL https://raw.githubusercontent.com/AnonShield/runshanondocker/main/run.sh -o run.sh
chmod +x run.sh
export ANON_SECRET_KEY=$(openssl rand -hex 32)
docker pull anonshield/anon:latest       # CPU
# docker pull anonshield/anon:gpu        # GPU
./run.sh ./your_file.csv                 # anonymize a file
```

---

## Minimal Test

~2–5 minutes. No datasets beyond what is already in the repository.

```bash
# Set a secret key
export ANON_SECRET_KEY=$(openssl rand -hex 32)

# Anonymize the included example file
uv run anon.py examples/teste-exemplo-artigo.txt

# Expected: output/anon_teste-exemplo-artigo.txt is created
# PII tokens replaced with [TYPE_<slug>] pseudonyms — verify with:
cat output/anon_teste-exemplo-artigo.txt
```

Run the unit test suite:
```bash
uv run python -m unittest discover tests/
```

Expected: all tests pass with no errors.

---

## Experiments

### Claim #1 — v3.0 achieves ≥743× speedup over v2.0 on operational-scale datasets

**Paper reference:** Tables 6, 7, and 8.

**Dataset:** D3 — public synthetic mock-CAIS dataset (247 MB CSV / 445 MB JSON, 70,951 records) at `paper_data/datasets/D3_mock_cais/`. D3 is **not** stored in git (too large); download it before running:
```bash
./paper_data/scripts/download_datasets.sh   # downloads D3 (~693 MB)
```
D2 (CAIS/RNP real Tenable scans, 420 MB CSV / 551 MB JSON) is private and cannot be redistributed; skip it with `--skip-d2`.

**Smoke test (~5–20 min on GPU):**
```bash
./paper_data/test_minimal/run_tests.sh            # GPU
./paper_data/test_minimal/run_tests.sh --cpu-only  # CPU-only
```

Expected: `13/13` steps pass, CSV files created under `paper_data/test_minimal/results/`.

**D3-only full reproduction (~6.3 h on GPU — measured):**
```bash
./paper_data/scripts/reproduce_all_runs.sh --skip-d1 --skip-d2
./paper_data/scripts/analyze_all.sh
```

**All public datasets (~103 h on GPU — measured):**
```bash
./paper_data/scripts/reproduce_all_runs.sh --skip-d2
./paper_data/scripts/analyze_all.sh
```

**Expected results:**

| Dataset / Format | v2.0 time (est.) | v3.0 standalone | Speedup |
|---|---|---|---|
| D3 CSV (247 MB) | ≥71.6 h | ~73 s | **≥3,532×** |
| D3 JSON (445 MB) | ~75.0 h | ~172 s | **~1,569×** |
| D2 CSV (420 MB) | ≥121.5 h | ~589 s | **≥743×** |
| D2 JSON (551 MB) | ~92.9 h | ~453 s | **~738×** |

Analysis output is written to `paper_data/results/<run_folder>/analysis/` and reproduces the figures and tables in the paper.

> Full dataset details and step-by-step instructions: [`paper_data/EXPERIMENTS.md`](paper_data/EXPERIMENTS.md)

---

### Claim #2 — `filtered` and `hybrid` strategies achieve F1 = 94.2%, Recall = 96.7%

**Paper reference:** Table 5.

**Dataset:** `paper_data/evaluation/vulnnet_scans_openvas_compilado.csv` (9.2 MB, 6,472 records compiled from all 130 D1 OpenVAS scan targets).

**Step 1 — Reproduce the 67-record sample** (drawn in two batches; deterministic with fixed seed):
```bash
# First draw: 50 records (SEED = 30)
uv run python scripts/sortear.py   # enter 50 when prompted

# Second draw: 17 more from the remaining pool (SEED = 30 + 50 = 80)
uv run python scripts/sortear.py   # enter 17 when prompted

# Output: numeros_sorteados.json in the current directory
```
The final list of 67 row indices is also recorded in `paper_data/evaluation/numeros_sorteados.docx`.

**Step 2 — Run all versions and strategies:**
```bash
python benchmark/benchmark.py \
  --benchmark \
  --file paper_data/evaluation/vulnnet_scans_openvas_compilado.csv \
  --versions 1.0 2.0 3.0 \
  --strategies filtered hybrid standalone presidio \
  --transformer-model attack-vector/SecureModernBERT-NER \
  --entities-to-preserve TOOL,PLATFORM,FILE_PATH,THREAT_ACTOR,SERVICE,REGISTRY_KEY,CAMPAIGN,MALWARE,SECTOR \
  --anonymization-config paper_data/configs/anonymization_config_openvas.json
```

Annotated outputs (anonymized CSV + XLSX with TP/FP/FN counts per entity type) are pre-computed and available in:
- `paper_data/evaluation/1.0/`
- `paper_data/evaluation/2.0/`
- `paper_data/evaluation/3.0-filtered/filtered/`
- `paper_data/evaluation/3.0-hybrid/hybrid/`
- `paper_data/evaluation/3.0-presidio/presidio/`
- `paper_data/evaluation/3.0-standalone/standalone/`

**Expected results:**

| Strategy | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| `filtered` | 724 | 64 | 25 | 91.9% | **96.7%** | **94.2%** |
| `hybrid` | 724 | 64 | 25 | 91.9% | **96.7%** | **94.2%** |
| `standalone` | 739 | 102 | 43 | 87.9% | 94.5% | 91.1% |
| `presidio` | 724 | 287 | 25 | 71.6% | 96.7% | 82.3% |

> Annotation methodology and XLSX format details: [`paper_data/evaluation/EVALUATION_DATA.md`](paper_data/evaluation/EVALUATION_DATA.md)

---

### Claim #3 — `anonymization_config` yields up to 47× additional throughput gain

**Paper reference:** Tables 6 and 7 (config gain rows).

**Dataset:** D3 with `paper_data/configs/anonymization_config_cve.json`.

```bash
# Without config (~73 s — D3-CSV, standalone, GPU-measured)
uv run anon.py paper_data/datasets/D3_mock_cais/cve_dataset_anonimizados_stratified.csv \
  --anonymization-strategy standalone

# With config (~8 s on GPU — D3-CSV, standalone)
uv run anon.py paper_data/datasets/D3_mock_cais/cve_dataset_anonimizados_stratified.csv \
  --anonymization-strategy standalone \
  --anonymization-config paper_data/configs/anonymization_config_cve.json
```

**Expected gains (standalone, GPU):**

| Dataset | Without config | With config | Gain |
|---|---|---|---|
| D3 CSV | ~73 s | ~8 s | **9.2×** |
| D3 JSON | ~172 s | ~20 s | **8.4×** |
| D2 CSV | ~589 s | ~13 s | **~47×** |
| D2 JSON | ~453 s | ~18 s | **~25×** |

> Full reproduction steps: [`paper_data/EXPERIMENTS.md`](paper_data/EXPERIMENTS.md)

---

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

---

*[CLI Reference](docs/users/CLI_REFERENCE.md) · [Architecture](docs/developers/ARCHITECTURE.md) · [Anonymization Strategies](docs/developers/ANONYMIZATION_STRATEGIES.md) · [Benchmark Suite](benchmark/BENCHMARK.md) · [Experiments & Datasets](paper_data/EXPERIMENTS.md) · [Evaluation Data](paper_data/evaluation/EVALUATION_DATA.md)*
