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
| **Disk** | ~2–3 GB (Python env + NER models); D1 ~88 MB (in git); D3 bundled as zips (~80 MB in git, ~700 MB extracted) |

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
git clone https://github.com/AnonShield/tool.git
cd tool

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

### Claim #1 — v3.0 (`standalone`) achieves 2–18× speedup over v2.0 per file on D1 (GPU); compounds to ≥3,500× (GPU) / ≥560× (CPU) at D3 scale

**Paper reference:** Tables 3, 4, 6, 7, and 8.

**What this claim asserts and why it has two parts:**

The per-file speedup is measured on D1 (small files, 130 targets). On GPU, v3.0 benefits from accelerated NER inference, yielding 2–18× over v2.0 per file. On CPU-only hardware, the ratio is lower since v3.0's NER pipeline runs slower without a GPU, but v2.0 is also CPU-bound so the gap persists. The large-scale speedup at D3 scale (247 MB CSV, 70,951 records) emerges from two compounding effects: (i) v2.0 exhibits superlinear scaling on CSV (CV = 1.75 on D1), meaning its per-byte cost *grows* with file size; (ii) v3.0's LRU cache *improves* throughput with entity recurrence. Using the measured v2.0 throughput (~1 KB/s) and the stored v3.0 D3 runtimes, the extrapolated speedup is ≥3,500× (GPU) / ≥560× (CPU).

**Verification options (in order of time cost):**

**Option A — Smoke test (~5–20 min, any hardware):**
Verifies the full pipeline is functional on small subsets of D1, D1C, and D3.
```bash
./paper_data/test_minimal/run_tests.sh            # with NVIDIA GPU
./paper_data/test_minimal/run_tests.sh --cpu-only  # no GPU
```
Expected: `13/13` steps pass. Absolute runtimes on 500-row subsets will not match the paper's full-scale numbers, but the pipeline is verified end-to-end.

**Option B — Spot check (~8–10 min, any hardware):**
Runs v2.0 and v3.0 on a ~512 KB subset of D3 CSV. v2.0 bottlenecks at ~1 KB/s on any hardware; v3.0 benefits from GPU acceleration, so the ratio varies by hardware (larger with GPU).
```bash
./paper_data/scripts/spot_check_claim1.sh            # with NVIDIA GPU
./paper_data/scripts/spot_check_claim1.sh --cpu-only  # no GPU
```
Expected output (absolute times and ratio vary by hardware):
```
══════════════════════════════════════════════════════════════
  Claim #1 Spot Check  (515 KB subset of D3 CSV)
══════════════════════════════════════════════════════════════
  v2.0  default    :    494.0 s   (1.04 KB/s on this machine)
  v3.0  standalone :      6.6 s   (78 KB/s on this machine)
  Speedup          : 75×  (ratio is hardware-independent)

  Extrapolating to full D3 (247 MB) via measured throughputs:
  v2.0 on full D3  : ≥ 67.5 h   (lower bound — v2.0 superlinear on CSV)
  v3.0 on full D3  : ≤ 3266 s   (upper bound — v3.0 cache improves at scale)
  Projected speedup: ≥ 74×
══════════════════════════════════════════════════════════════
```

**Option C — Full D3 benchmark (reproduces paper Tables 6–8):**
Runtime is hardware-dependent and cannot be estimated without knowing the evaluator's machine.
```bash
./paper_data/scripts/extract_datasets.sh                     # extract D3 from bundled zips (~80 MB → ~700 MB)
./paper_data/scripts/reproduce_all_runs.sh --skip-d1 --skip-d2
./paper_data/scripts/analyze_all.sh
```
The stored `benchmark_results.csv` files under `paper_data/results/` contain the paper's original measurements and can be inspected without re-running:
```bash
./paper_data/scripts/analyze_all.sh   # regenerate charts from stored CSVs only
```

**Per-file speedup on D1 (GPU, median across 130 targets, Table 3):**

| Format | v2.0 (median) | v3.0 standalone (median) | Speedup |
|---|---|---|---|
| XML | 176 s | 10 s | **17.6×** |
| CSV | 37 s | 7 s | **5.6×** |
| PDF (text) | 13 s | 7 s | **1.8×** |
| TXT | 13 s | 8 s | **1.6×** |

> The large-scale speedup at D3 scale is verifiable via Option B's spot check, which extrapolates v2.0's measured throughput to the full D3 file. Full D1 reproduction takes ~35 h and full D3 reproduction is hardware-dependent — neither is expected of evaluators.

> Full dataset details and step-by-step instructions: [`paper_data/EXPERIMENTS.md`](paper_data/EXPERIMENTS.md)

---

### Claim #2 — `filtered` and `hybrid` strategies achieve F1 = 94.2%, Recall = 96.7%

**Paper reference:** Table 5.

**What this claim asserts:** On a stratified sample of 67 OpenVAS vulnerability records annotated by three security specialists, the `filtered` and `hybrid` strategies achieve F1 = 94.2% and Recall = 96.7%. Annotation was performed by the paper authors and is **not expected to be reproduced by evaluators** — it required manual expert judgment across 13 entity types.

**What evaluators can verify:**
1. **Inspect the pre-computed annotated outputs** directly (no re-running required):
   - `paper_data/evaluation/3.0-filtered/filtered/` — anonymized CSV + XLSX with TP/FP/FN counts
   - `paper_data/evaluation/3.0-hybrid/hybrid/`
   - `paper_data/evaluation/3.0-standalone/standalone/`
   - `paper_data/evaluation/3.0-presidio/presidio/`
   - `paper_data/evaluation/1.0/` and `paper_data/evaluation/2.0/`
2. **Re-run the tool** on the evaluation dataset and compare the anonymized output against the reference:
```bash
python benchmark/benchmark.py \
  --benchmark \
  --file paper_data/evaluation/vulnnet_scans_openvas_compilado.csv \
  --versions 3.0 \
  --strategies filtered hybrid standalone presidio \
  --transformer-model attack-vector/SecureModernBERT-NER \
  --entities-to-preserve TOOL,PLATFORM,FILE_PATH,THREAT_ACTOR,SERVICE,REGISTRY_KEY,CAMPAIGN,MALWARE,SECTOR \
  --anonymization-config paper_data/configs/anonymization_config_openvas.json
```

**Reference results (pre-computed, 67 records, 3 specialists, 13 entity types):**

| Strategy | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| `filtered` | 724 | 64 | 25 | 91.9% | **96.7%** | **94.2%** |
| `hybrid` | 724 | 64 | 25 | 91.9% | **96.7%** | **94.2%** |
| `standalone` | 739 | 102 | 43 | 87.9% | 94.5% | 91.1% |
| `presidio` | 724 | 287 | 25 | 71.6% | 96.7% | 82.3% |

> Annotation methodology and XLSX format details: [`paper_data/evaluation/EVALUATION_DATA.md`](paper_data/evaluation/EVALUATION_DATA.md)

---

### Claim #3 — `anonymization_config` eliminates NER inference overhead, significantly reducing D3 processing time (>2×)

**Paper reference:** Tables 6 and 7 (config gain rows).

**What this claim asserts:** A schema-aware `anonymization_config` that specifies only `force_anonymize` and `exclude` directives bypasses the NER and regex pipeline entirely — no field undergoes inference. On GPU, this reduces D3 CSV processing from ~73 s to ~8 s (~9×); on CPU, from ~434 s to ~9 s (~48×). The larger CPU gain follows directly from the fact that NER inference is much more expensive on CPU: removing it saves more time. The paper also reports gains on D2 (private dataset, not reproducible by evaluators).

**Dataset:** D3 with `paper_data/configs/anonymization_config_cve.json`.

```bash
./paper_data/scripts/spot_check_claim3.sh            # with NVIDIA GPU
./paper_data/scripts/spot_check_claim3.sh --cpu-only  # no GPU
```
Expected speedup: **~9× on GPU**, **~48× on CPU** (absolute times vary by hardware; CPU gain is larger because NER inference costs more without a GPU).
```
══════════════════════════════════════════════════════════════
  Claim #3 Spot Check  (D3 CSV, v3.0 standalone)
══════════════════════════════════════════════════════════════
  without config  :     73.1 s
  with config     :      8.4 s
  Config speedup  : 8.7×

  Note: with config, GPU and CPU times converge to ~8–9 s each,
  because no field passes through the NER or regex pipeline.
  The CPU gain is therefore larger than the GPU gain (~50× vs ~9×).
══════════════════════════════════════════════════════════════
```

**Expected gains on D3 (publicly reproducible, standalone strategy):**

| Format | Without config (GPU) | Without config (CPU) | With config (GPU) | With config (CPU) | Gain (GPU) | Gain (CPU) |
|---|---|---|---|---|---|---|
| D3 CSV | ~73 s | ~434 s | ~8 s | ~9 s | **9.2×** | **~50×** |
| D3 JSON | ~172 s | ~882 s | ~20 s | ~21 s | **8.4×** | **~42×** |

> With `anonymization_config`, GPU and CPU times converge to near-identical values because the config uses only `force_anonymize` and `exclude` directives — no field passes through the NER or regex pipeline, eliminating the GPU's advantage. The config gain on CPU is therefore larger than on GPU.

> Full reproduction steps: [`paper_data/EXPERIMENTS.md`](paper_data/EXPERIMENTS.md)

---

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

---

*[CLI Reference](docs/users/CLI_REFERENCE.md) · [Architecture](docs/developers/ARCHITECTURE.md) · [Anonymization Strategies](docs/developers/ANONYMIZATION_STRATEGIES.md) · [Benchmark Suite](benchmark/BENCHMARK.md) · [Experiments & Datasets](paper_data/EXPERIMENTS.md) · [Evaluation Data](paper_data/evaluation/EVALUATION_DATA.md)*
