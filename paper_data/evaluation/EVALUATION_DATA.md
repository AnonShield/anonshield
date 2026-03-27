# Accuracy Evaluation Data

This folder contains all data for the accuracy evaluation reported in **Table 5** of the paper. It includes the input dataset, anonymized outputs from all versions and strategies, execution logs, and the annotated XLSX files reviewed by three security specialists.

---

## Directory Structure

```
paper_data/evaluation/
├── EVALUATION_DATA.md               ← this file
├── vulnnet_scans_openvas_compilado.csv  ← input: compiled D1 OpenVAS reports (6,472 records)
├── numeros_sorteados.docx           ← list of 67 sampled row indices used for annotation
├── 1.0/                             ← v1.0 anonymized output
│   ├── 1.0anon_vulnnet_scans_openvas_compilado_csv.csv
│   ├── 1.0anon_vulnnet_scans_openvas_compilado_csv.xlsx   ← annotated (TP/FP/FN)
│   ├── 1.0entities.db
│   └── v1.0_default_vulnnet_scans_openvas_compilado.csv_run1.log
├── 2.0/                             ← v2.0 anonymized output
│   ├── 2.0anon_vulnnet_scans_openvas_compilado.csv
│   ├── 2.0anon_vulnnet_scans_openvas_compilado.xlsx       ← annotated (TP/FP/FN)
│   ├── 2.0entities.db
│   └── v2.0_default_vulnnet_scans_openvas_compilado.csv_run1.log
├── 3.0-filtered/filtered/           ← AnonShield filtered strategy output
│   ├── 3.0filtered_anon_vulnnet_scans_openvas_compilado.xlsx  ← annotated (TP/FP/FN)
│   ├── anon_vulnnet_scans_openvas_compilado.csv
│   └── entities.db
├── 3.0-hybrid/hybrid/               ← AnonShield hybrid strategy output
│   ├── 3.0hybrid_anon_vulnnet_scans_openvas_compilado.xlsx    ← annotated (TP/FP/FN)
│   ├── anon_vulnnet_scans_openvas_compilado.csv
│   └── entities.db
├── 3.0-presidio/presidio/           ← AnonShield presidio strategy output
│   ├── 3.0presidio_anon_vulnnet_scans_openvas_compilado.xlsx  ← annotated (TP/FP/FN)
│   ├── anon_vulnnet_scans_openvas_compilado.csv
│   └── entities.db
├── 3.0-standalone/standalone/       ← AnonShield standalone strategy output
│   ├── 3.0standalone_anon_vulnnet_scans_openvas_compilado.xlsx ← annotated (TP/FP/FN)
│   ├── anon_vulnnet_scans_openvas_compilado.csv
│   └── entities.db
├── benchmark_data/                  ← benchmark timing for this evaluation run
│   ├── benchmark_results.csv
│   ├── benchmark_results.json
│   └── benchmark_state.json
└── run_logs/                        ← per-version/strategy execution logs
    ├── v1.0_default_vulnnet_scans_openvas_compilado.csv_run1.log
    ├── v2.0_default_vulnnet_scans_openvas_compilado.csv_run1.log
    ├── v3.0_filtered_vulnnet_scans_openvas_compilado.csv_run1.log
    ├── v3.0_hybrid_vulnnet_scans_openvas_compilado.csv_run1.log
    ├── v3.0_presidio_vulnnet_scans_openvas_compilado.csv_run1.log
    ├── v3.0_slm_vulnnet_scans_openvas_compilado.csv_run1.log
    └── v3.0_standalone_vulnnet_scans_openvas_compilado.csv_run1.log
```

---

## Input Dataset

**`vulnnet_scans_openvas_compilado.csv`** — 9.2 MB, 6,472 vulnerability records compiled from all 130 D1 OpenVAS scan targets (CSV format). This is the dataset processed by every version and strategy for the accuracy evaluation.

---

## Sample Selection

67 records were drawn from the 6,472-row dataset using a statistically justified sample size:

```
n = (Z² × p × (1 − p)) / E²  =  (1.645² × 0.5 × 0.5) / 0.1²  ≈ 67
```

Parameters: 90% confidence level, Z = 1.645, p = 0.50, margin of error E = 10%.

**To reproduce the exact same 67 row indices** (drawn in two batches, deterministic with fixed seed):

```bash
# Run from the project root
uv run python scripts/sortear.py   # enter 50 when prompted  → first draw
uv run python scripts/sortear.py   # enter 17 when prompted  → second draw

# Output: numeros_sorteados.json (written to current directory)
```

**How the seed works:** `scripts/sortear.py` uses `random.seed(SEED + len(sorteados))` where `SEED = 30` and `len(sorteados)` is the count of numbers already drawn (loaded from `numeros_sorteados.json` at the start of each call). This makes each batch independently reproducible:

- First call: no prior draws → `len(sorteados) = 0` → seed = 30
- Second call: 50 prior draws → `len(sorteados) = 50` → seed = 80

The final list of 67 row indices is also recorded in `numeros_sorteados.docx` in this folder.

---

## Annotation Protocol

Three security specialists independently reviewed each of the 67 sampled records across all version/strategy outputs. For each record, they counted:

- **TP (True Positive):** PII entity correctly detected and pseudonymized
- **FP (False Positive):** Non-PII incorrectly pseudonymized
- **FN (False Negative):** PII entity missed (not pseudonymized)

For **partial anonymizations** (e.g., a URL where only the domain was replaced but the path was leaked): 1 TP for the redacted portion + 1 FN for the exposed remainder.

13 entity types were evaluated: `IP_ADDRESS`, `HOSTNAME`, `URL`, `ORGANIZATION`, `PERSON`, `EMAIL_ADDRESS`, `CVE_ID`, `HASH`, `CERT_SERIAL`, `UUID`, `AUTH_TOKEN`, `MAC_ADDRESS`, `PORT`.

The annotated counts are recorded in the `.xlsx` files in each version/strategy subfolder.

> **Note for programmatic verification:** Each annotated XLSX contains a `=SUM(...)` formula in the **last row** of the TP, FP, and FN columns. When computing totals programmatically, skip the last row or filter only for numeric (integer/float) cells and ignore string/formula cells — otherwise the column sum will be doubled (once from the data rows, once from the SUM cell itself).

---

## Results (Table 5 in the paper)

| Version / Strategy | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| 3.0\_presidio | 724 | 287 | 25 | 71.6% | 96.7% | 82.3% |
| 3.0\_filtered | 724 | 64 | 25 | **91.9%** | **96.7%** | **94.2%** |
| 3.0\_hybrid | 724 | 64 | 25 | **91.9%** | **96.7%** | **94.2%** |
| 3.0\_standalone | 739 | 102 | 43 | 87.9% | 94.5% | 91.1% |

Model used: `attack-vector/SecureModernBERT-NER`. Preservation list applied: `TOOL`, `PLATFORM`, `FILE_PATH`, `THREAT_ACTOR`, `SERVICE`, `REGISTRY_KEY`, `CAMPAIGN`, `MALWARE`, `SECTOR`. Config: `paper_data/configs/anonymization_config_openvas.json`.

---

## Reproducing the Evaluation

```bash
# Set secret key (use the same key to compare outputs)
export ANON_SECRET_KEY=$(openssl rand -hex 32)

# Run all versions and strategies in one command
python benchmark/benchmark.py \
  --benchmark \
  --file paper_data/evaluation/vulnnet_scans_openvas_compilado.csv \
  --versions 1.0 2.0 3.0 \
  --strategies filtered hybrid standalone presidio \
  --transformer-model attack-vector/SecureModernBERT-NER \
  --entities-to-preserve TOOL,PLATFORM,FILE_PATH,THREAT_ACTOR,SERVICE,REGISTRY_KEY,CAMPAIGN,MALWARE,SECTOR \
  --anonymization-config paper_data/configs/anonymization_config_openvas.json
```

Then open each generated XLSX file, extract the 67 sampled rows (indices from `scripts/numeros_sorteados.json`), and count TP/FP/FN per entity type.

---

## benchmark_data/ Schema

`benchmark_results.csv` contains one row per (version × strategy × run) with columns: `version`, `strategy`, `file_name`, `wall_clock_time_sec`, `throughput_kb_per_sec`, `max_resident_set_kb`, `gpu_available`, `avg_gpu_utilization_percent`, and others. See `paper_data/EXPERIMENTS.md` for the full column reference.
