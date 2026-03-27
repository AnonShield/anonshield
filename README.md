# AnonShield: Scalable On-Premise Pseudonymization for CSIRT Vulnerability Data

AnonShield is a pseudonymization framework designed for Computer Security Incident Response Teams (CSIRTs). It replaces Personally Identifiable Information (PII) and cybersecurity indicators with cryptographically secure, deterministic pseudonyms (HMAC-SHA256), preserving referential integrity across documents while enabling GDPR/LGPD-compliant data sharing. AnonShield combines GPU-accelerated NER, an LRU entity cache, streaming processors for large files, and a schema-aware configuration mechanism. Evaluated on datasets up to 550 MB (70,951+ vulnerability records), it reduces processing time from ~92 hours to under 10 minutes (~738× speedup over v2.0 on D2 JSON; ≥743× on D2 CSV) and achieves F1 = 94.2%, Recall = 96.7% with the `filtered`/`hybrid` strategies.

> **Paper:** *AnonShield: Scalable On-Premise Pseudonymization for CSIRT Vulnerability Data* — SBRC 2026 Salão de Ferramentas.

---

## README Structure

| Section | Description |
|---|---|
| [Considered Seals](#considered-seals) | SBRC quality seals targeted by this artifact |
| [Basic Information](#basic-information) | Hardware, OS, and software environment |
| [Dependencies](#dependencies) | Required packages and external tools |
| [Security Concerns](#security-concerns) | Risks and mitigations for evaluators |
| [Installation](#installation) | Step-by-step setup (local and Docker) |
| [Minimal Test](#minimal-test) | Quick functional verification (~5–10 min) |
| [Experiments](#experiments) | Reproduction of the three main paper claims |
| [License](#license) | Licensing information |

---

## Considered Seals

The seals considered are: **Available (SeloD)**, **Functional (SeloF)**, **Sustainable (SeloS)**, and **Reproducible Experiments (SeloR)**.

**SeloS — Sustainable:** The tool source code is maintained under `src/anon/` (core library: `engine.py`, `strategies.py`, `processors.py`, `entity_detector.py`, `standalone_strategy.py`, etc.) and the CLI entry point is `anon.py`. All dependencies are pinned in `pyproject.toml` and `uv.lock`, ensuring reproducible installation. Docker images (`anonshield/anon:latest` / `:gpu`) provide a fully self-contained execution environment.

---

## Basic Information

| | |
|---|---|
| **Hardware (paper experiments)** | NVIDIA RTX 5060 Ti 16 GB VRAM · AMD Ryzen 5 8600G (6c/12t) · 32 GB DDR5 6000 MHz |
| **Minimum for smoke test** | 4 GB RAM · x86\_64 · Python 3.12 + uv |
| **Software** | Python 3.12 + [`uv`](https://astral.sh/uv) for all experiments; Docker optional (tool use only) |
| **GPU (optional)** | NVIDIA driver ≥ 525 (CUDA 12.8) + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) |
| **OS** | Linux (tested and recommended); macOS/Windows supported via Docker only |
| **Disk** | `.venv` after `uv sync`: ~6.5 GB; NER models: ~1.5 GB (downloaded on first run to `~/.cache/huggingface/`); D1 ~133 MB (in git); D3 bundled as zips (~80 MB in git, ~700 MB extracted). Benchmark comparisons with v2.0 (via `--setup`) require ~8 GB additional (v2.0 venv + models). **Total for full experiment suite: ~17 GB.** |

---

## Dependencies

**Python environment (all experiments):**
- Python 3.12 + [`uv`](https://astral.sh/uv) — all packages pinned in `pyproject.toml` / `uv.lock`
- Key packages: `presidio-analyzer`, `presidio-anonymizer`, `transformers`, `spacy`, `torch`, `pandas`, `pymupdf`, `pytesseract`, `lxml`, `orjson`, `scipy`, `statsmodels`
- NER models downloaded automatically on first run and cached in `~/.cache/huggingface/` (~1.5 GB)

**Optional:**
- Tesseract OCR — required only for OCR-mode tests (PDF/image files):
  ```bash
  sudo apt install tesseract-ocr  # Ubuntu/Debian
  ```
- Docker — for tool use only (not needed for experiments): `anonshield/anon:latest` (~2 GB CPU) or `anonshield/anon:gpu` (~6 GB GPU)

---

## Security Concerns

- AnonShield processes sensitive cybersecurity data entirely **locally** — no data is transmitted to external services
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

> **⚠️ Warning:** The Docker images contain only the anonymization tool (`anon.py`). They do **not** include the benchmark suite, datasets (D1/D3), evaluation data, or any experiment scripts. To reproduce the paper's claims, use the local installation with `uv sync` as described above.

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

~5–10 minutes. No datasets beyond what is already in the repository.

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

Expected: the final line reads `OK` (all tests passed) or `FAILED` (one or more tests failed). Some tests intentionally exercise error paths and will print `ERROR` or warning messages during the run — this is normal and does not indicate a failure. Only the final `OK` / `FAILED` verdict matters.

---

## Experiments

### Claim #1 — AnonShield (`standalone`) achieves ~3×–~17× speedup over v2.0 per file on D1 (GPU); ≥3,532× (GPU) / ≥535× (CPU) at D3 scale

**Paper reference:** Tables 3, 4, 6, 7, and 8.

**What this claim asserts and why it has two parts:**

The per-file speedup is measured on D1 (small files, 130 targets). On GPU, AnonShield benefits from accelerated NER inference, yielding ~3×–~17× over v2.0 per file (paper Table 3, mean-based). On CPU-only hardware, AnonShield loses GPU acceleration (~5.5× slower per file) while v2.0 is already CPU-bound — so per-file speedup on CPU is ~GPU speedup ÷ 5.5, and AnonShield may be slower per file without a GPU. However, at D3 scale the advantage recovers due to AnonShield's O(n) streaming architecture vs v2.0's scaling behavior: ≥3,532× on GPU and ≥535× on CPU (D3 CPU times are measured in stored results).

**Verification options (in order of time cost):**

**Option A — Smoke test (~5–25 min depending on hardware):**
Verifies the full pipeline is functional on small subsets of D1, D1C, and D3.
```bash
./paper_data/test_minimal/run_tests.sh --skip-d2            # with NVIDIA GPU (D2 is private — skip it)
./paper_data/test_minimal/run_tests.sh --skip-d2 --cpu-only  # no GPU
```
Expected: the final line reads `RESULT: ALL PASSED`. D2 is a private dataset not included in this repository; `--skip-d2` omits those 4 steps so the script exits cleanly. Absolute runtimes on 500-row subsets will not match the paper's full-scale numbers, but the pipeline is verified end-to-end.

**Option B — Spot check (~8–20 min after setup):**
Runs v2.0 and AnonShield on a ~512 KB subset of D3 CSV. v2.0 throughput is compute-limited and scales poorly with file size; AnonShield benefits from GPU acceleration when available, so the measured ratio varies by hardware. On first run, the script automatically sets up v2.0 and v3.0 environments and downloads model weights (~several GB) — this can take significantly longer depending on network speed. Subsequent runs skip setup entirely.

```bash
./paper_data/scripts/extract_datasets.sh             # extract D3 from bundled zips (required once)
./paper_data/scripts/spot_check_claim1.sh            # with NVIDIA GPU
./paper_data/scripts/spot_check_claim1.sh --cpu-only  # no GPU
```
Expected output (absolute times vary by hardware; speedup is larger with GPU):
```
══════════════════════════════════════════════════════════════
  Claim #1 Spot Check  (515 KB subset of D3 CSV)
══════════════════════════════════════════════════════════════
  v2.0  default    :    XXX.X s   (X.XX KB/s on this machine)
  AnonShield  standalone :     XX.X s   (XXX KB/s on this machine)
  Speedup          : XX×  (varies by hardware — larger when GPU is available)

  Extrapolating to full D3 (247 MB) via measured throughputs:
  v2.0 on full D3  : ≥ XX.X h   (lower bound — extrapolated from measured throughput)
  AnonShield on full D3  : ≤ XXXX s   (upper bound — AnonShield cache improves at scale)
  Projected speedup: ≥ XX×
══════════════════════════════════════════════════════════════
```

**Option C — Full D3 benchmark (reproduces paper Tables 6–8):**
Runtime is hardware-dependent and cannot be estimated without knowing the evaluator's machine.
```bash
./paper_data/scripts/extract_datasets.sh                     # extract D3 from bundled zips (~80 MB → ~700 MB)
./paper_data/scripts/reproduce_all_runs.sh --skip-d1 --skip-d2
./paper_data/scripts/analyze_all.sh
```
The stored `benchmark_results.csv` files under `paper_data/results_paper/` contain the paper's original measurements and can be inspected directly without re-running.

**Per-file performance on D1 (130 targets, mean, Table 3):**

> CPU estimates derived by applying the D3 standalone CPU/GPU factor (~5.5×) to AnonShield GPU times. v2.0 does not use GPU acceleration (CPU-bound DOM parsing), so v2.0 CPU ≈ v2.0 GPU. This means per-file speedup on CPU = GPU speedup ÷ 5.5 — AnonShield may be **slower** than v2.0 per file without a GPU, but remains faster at scale (D3: ≥535× CPU vs ≥3,532× GPU).

| Format | v2.0 GPU | v2.0 CPU~est | AnonShield standalone GPU | AnonShield standalone CPU~est | Speedup (GPU) | Speedup (CPU~est) |
|---|---|---|---|---|---|---|
| XML | 192 s | ~192 s | 12 s | ~64 s | **16.5×** | **~3.0×** |
| CSV | 74 s | ~74 s | 8 s | ~43 s | **9.6×** | **~1.7×** |
| PDF (text) | 27 s | ~27 s | 9 s | ~47 s | **3.3×** | **~0.6×** |
| TXT | 31 s | ~31 s | 10 s | ~57 s | **3.0×** | **~0.5×** |

**Per-file performance on D1C (130 targets, mean, Table 4):**

| Format | v2.0 GPU | v2.0 CPU~est | AnonShield standalone GPU | AnonShield standalone CPU~est | Speedup (GPU) | Speedup (CPU~est) |
|---|---|---|---|---|---|---|
| XLSX | 60 s | ~60 s | 7 s | ~39 s | **8.5×** | **~1.5×** |
| DOCX | 30 s | ~30 s | 9 s | ~52 s | **3.2×** | **~0.6×** |
| JSON | 247 s | ~247 s | 11 s | ~58 s | **23.2×** | **~4.3×** |
| PDF (image/OCR) | 59 s | ~59 s | 36 s | ~198 s | **1.6×** | **~0.3×** |

**Large-scale performance on D2 and D3 (AnonShield standalone, mean, Tables 7–8):**

| Dataset/Format | GPU | CPU~est | Speedup vs v2.0 (GPU) | Speedup vs v2.0 (CPU~est) |
|---|---|---|---|---|
| D2 CSV (419.72 MB) | 588.5 ± 30.7 s | ~3,237 s | ≥743× | ≥133× |
| D2 JSON (550 MB) | 453.1 ± 35.9 s | ~2,492 s | ~738× | ~134× |
| D3 CSV (247 MB) | 73.0 ± 1.6 s | 481.5 ± 8.9 s† | ≥3,532× | ≥535× |
| D3 JSON (445 MB) | 172.1 ± 6.2 s | 881.9 ± 57.7 s† | ~1,569× | ~306× |

> † D3 CPU times are measured (stored in `paper_data/results_paper/D3_mock_cve_*__cpu`). D2 CPU times are estimated using the D3 standalone factor (~5.5×). v2.0 extrapolated from D1 throughput (0.98 KB/s CSV, 1.69 KB/s JSON) — CPU-bound, no GPU benefit assumed.

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
python3 benchmark/benchmark.py \
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

### Claim #3 — `anonymization_config` eliminates NER inference overhead, reducing D3 processing time significantly (paper hardware: ~9× GPU / ~55× CPU; actual speedup depends on GPU speed)

**Paper reference:** Tables 6 and 7 (config gain rows).

**What this claim asserts:** A schema-aware `anonymization_config` that specifies only `force_anonymize` and `exclude` directives bypasses the NER and regex pipeline entirely — no field undergoes inference. On GPU (paper hardware), this reduces D3 CSV processing from ~73 s to ~8 s (~9×, Table 8). The CPU gain is larger because NER inference costs more without a GPU. The paper also reports gains on D2 (private dataset, not reproducible by evaluators).

**Dataset:** D3 with `paper_data/configs/anonymization_config_cve.json`.

```bash
./paper_data/scripts/extract_datasets.sh              # extract D3 from bundled zips (required once)
./paper_data/scripts/spot_check_claim3.sh             # with NVIDIA GPU  (~80 s)
./paper_data/scripts/spot_check_claim3.sh --cpu-only  # no GPU          (~490 s / ~8 min)
```
Expected speedup: **larger on CPU** (NER inference costs more without a GPU, so removing it saves more). Absolute times vary by hardware.
```
══════════════════════════════════════════════════════════════
  Claim #3 Spot Check  (D3 CSV, AnonShield standalone)
══════════════════════════════════════════════════════════════
  without config  :    XXX.X s
  with config     :      X.X s
  Config speedup  : XX×

  Note: for this specific config (only force_anonymize and
  fields_to_exclude directives, zero fields_to_anonymize entries),
  no field passes through the NER or regex pipeline, so GPU and
  CPU times converge. The CPU gain is therefore larger than on GPU.
══════════════════════════════════════════════════════════════
```

**Gains on D3 — `standalone` strategy (paper hardware: RTX 5060 Ti / Ryzen 5 8600G):**

| Format | Without config (GPU) | Without config (CPU) | With config (GPU) | With config (CPU) | Gain (GPU) | Gain (CPU) |
|---|---|---|---|---|---|---|
| D3 CSV | 73.0 ± 1.6 s | 481.5 ± 8.9 s | 7.96 ± 0.08 s | 8.7 ± 0.6 s | **9.2×** | **~55×** |
| D3 JSON | 172.1 ± 6.2 s | 881.9 ± 57.7 s | 20.43 ± 0.81 s | 20.9 ± 0.9 s | **8.4×** | **~42×** |

> GPU values are from paper Table 8; CPU values are from stored benchmark runs (`paper_data/results_paper/D3_mock_cve_*__cpu`). With config, GPU and CPU times converge because no field passes through the NER or regex pipeline. The CPU gain is therefore larger than on GPU. Absolute times on your hardware will differ.

> Full reproduction steps: [`paper_data/EXPERIMENTS.md`](paper_data/EXPERIMENTS.md)

---

## Support & Contact

We welcome feedback, questions, and contributions from the community.

* **Bugs & Feature Requests:** Please [open an issue](https://github.com/AnonShield/tool/issues) on our GitHub repository.
* **Direct Contact & Inquiries:** For institutional questions, partnerships, or to report a security bug directly, reach out to our team at **[anonshield@unipampa.edu.br](mailto:anonshield@unipampa.edu.br)**.

---

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE) for the full text.

---

*[CLI Reference](docs/users/CLI_REFERENCE.md) · [Architecture](docs/developers/ARCHITECTURE.md) · [Anonymization Strategies](docs/developers/ANONYMIZATION_STRATEGIES.md) · [Benchmark Suite](benchmark/BENCHMARK.md) · [Experiments & Datasets](paper_data/EXPERIMENTS.md) · [Evaluation Data](paper_data/evaluation/EVALUATION_DATA.md)*
