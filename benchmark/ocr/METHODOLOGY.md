# OCR Benchmark Methodology

**AnonShield OCR Benchmark Suite — Scientific Methodology**
Target venues: ICDAR, SIBGRAPI, IJDAR

---

## 1. Metrics

### 1.1 Primary Metrics

#### CER — Character Error Rate

The primary metric for raw transcription fidelity. Defined as normalized Levenshtein
distance at the character level:

```
CER = (S_c + D_c + I_c) / N_c
```

- `S_c`, `D_c`, `I_c`: character substitutions, deletions, insertions
- `N_c`: number of characters in the reference (ground truth)
- CER can exceed 1.0 when the hypothesis is substantially longer than the reference

Computed with the Wagner–Fischer algorithm (O(mn) time, O(min(m,n)) space).
Implementation: `benchmark/ocr/metrics.py::cer` — takes the edit distance
divided by `len(reference)`; returns `0.0` when both strings are empty and
`float('inf')` when the reference is empty but the hypothesis is not.
Always applied **after** the normalization pipeline (§2).

#### WER — Word Error Rate

Same formula at the token level. Tokenization convention: `str.split()` (Python
default — any whitespace run), punctuation attached (not split).
Case-sensitive (normalization does not fold case by default).
Implementation: `benchmark/ocr/metrics.py::wer`.

#### Field-level F1 (structured documents)

For forms and ID cards. Each reference field is compared against a best-effort
OCR extraction (`runner._extract_fields` — substring match for text fields,
digit-only containment for numeric fields listed in `datasets.NUMERIC_FIELDS`).

- **Text fields:** bag-of-tokens F1 over whitespace-split tokens
  (`metrics._token_f1`):

  ```
  F1 = 2 * Precision * Recall / (Precision + Recall)
  ```

  where Precision = |pred ∩ ref| / |pred|, Recall = |pred ∩ ref| / |ref|.
  Token comparison uses the normalized form (§2); token order is ignored.

- **Numeric fields (CPF, dates, IDs):** exact match after digit-only
  extraction (`re.sub(r'\D', '', value)`). Score is `1.0` or `0.0` per field.

- **Macro-average** over per-field scores is reported as
  `macro_f1` — this is the `macro_field_f1` column in the primary table.

#### ANLS — Average Normalized Levenshtein Similarity

Standard metric for document understanding / information extraction tasks (DocVQA).
Better than exact match because it gives partial credit proportional to similarity:

```
NLS(pred, gt) = 1 - NED(pred, gt)
NED = EditDistance(pred, gt) / max(len(pred), len(gt))

Score = NLS   if NLS >= τ (threshold = 0.5)
      = 0     otherwise

ANLS = mean(Score) over all field-extraction questions
```

Use ANLS when evaluating whether the correct entity value was recovered for
anonymization purposes, even if minor OCR artifacts are present.
Implementation: `benchmark/ocr/metrics.py::anls_score`,
threshold configurable via `--anls-threshold` (default 0.5).

### 1.2 Secondary Metrics

#### CER-NoDiacritic

CER computed after applying NFD decomposition and removing combining diacritical marks
(Unicode category Mn). The difference `CER_primary − CER_NoDiacritic` quantifies the
fraction of total error attributable specifically to diacritic confusion — a well-
documented failure mode on Brazilian administrative documents.

```python
def strip_diacritics(text: str) -> str:
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )
```

#### KVRR — Key-Value Recovery Rate

Binary metric at the document level:

```
KVRR = documents where ALL mandatory fields are correctly extracted
       / total documents
```

Strict; complementary to field-level F1. Useful for compliance contexts where
partial extraction is not acceptable. Implementation:
`benchmark/ocr/metrics.py::kvrr`. **Currently defined and unit-tested but not
yet emitted by the standard report** — consumers compute it on demand from
`ocr_benchmark_per_doc.csv`.

### 1.3 Metrics Defined For Future Work (Not Emitted Today)

- **Weighted CER** — substitution-cost matrix for visually similar pairs
  (e.g. `0`/`O`, `1`/`l`, `rn`/`m`, `ç`/`c`, `ã`/`a`). Useful when comparing
  engines that share character-confusion patterns. Not implemented; the T5
  error analysis table surfaces raw confusion counts instead.

### 1.4 Metrics NOT Used and Why

**BLEU:** Designed for machine translation (precision-only, corpus-level). Rewards
correct n-grams regardless of position; does not penalize missing content. At the
single-document level it is statistically unreliable. Not suitable for OCR evaluation.
Exception: "pipeline BLEU" measuring end-to-end OCR→NLP quality may be reported
separately and clearly labeled.

---

## 2. Text Normalization Pipeline

Applied identically to both reference and hypothesis before any metric
computation. Single source of truth: `benchmark/ocr/metrics.py::normalize`.
References come pre-normalized from each dataset loader; hypotheses are
normalized by the runner (`runner.py`) immediately after inference.

```python
def normalize(text, *, fold_case=False, fold_diacritics=False):
    text = unicodedata.normalize("NFC", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Cf")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\xa0\u2009\u200a]+", " ", text).strip()
    if fold_diacritics: ...  # NFD + strip Mn
    if fold_case:       text = text.casefold()
    return text
```

Concretely, in order:

1. **NFC canonical composition** — precomposed diacritics (`e` + `´` → `é`).
2. **Remove Unicode format characters** (category `Cf`). This covers zero-width
   joiners (U+200C, U+200D), zero-width space (U+200B), BOM (U+FEFF), bidi
   controls, and similar invisibles.
3. **Normalize line endings** — `\r\n` and bare `\r` become `\n`.
   **Newlines are preserved** (not collapsed to spaces); only spaces, tabs,
   NBSP (U+00A0), thin space (U+2009) and hair space (U+200A) runs are
   collapsed to a single ASCII space and the result is stripped.
4. **Diacritic folding (opt-in)** — NFD decomposition + drop of combining
   marks (Unicode category `Mn`). Used exclusively by `cer_no_diacritic`.
5. **Case folding (opt-in)** — `str.casefold()`. Never applied by the
   primary metric path; left available for diagnostic reports.

### 2.1 Diacritics Policy

**Do not fold diacritics in primary metrics.** Brazilian OCR systems are tested
specifically on their ability to handle ã, ç, ê, é, ó, ô, ú, etc. Stripping them
removes discriminative signal. Diacritic-folded results are reported only as
the secondary `CER-NoDiacritic` metric (`metrics.py::cer_no_diacritic`).

### 2.2 OCR-Specific Noise — Explicit Non-Handling

The current pipeline intentionally does **not** implement any of the following.
If they are needed for a specific publication, apply them in a pre-processing
step and republish this section.

- **Line-break collapse:** newlines are preserved, so `foo\nbar` vs `foo bar`
  counts as one substitution. For page-level CER on documents where line-break
  position is noise, pre-replace `\n` with space on both sides before calling
  `cer`.
- **Hyphenation joining:** `word-\nrest` is *not* reassembled to `wordrest`.
- **Layout-aware region alignment:** CER is computed over the full page-level
  string as emitted by the engine, without reading-order correction.

---

## 3. Statistical Significance

Single-run benchmarks are insufficient for scientific publication. Every reported
metric must be accompanied by a confidence interval, and every pairwise engine
comparison must include a significance test.

### 3.1 Bootstrap Confidence Intervals

95% percentile bootstrap with B=10 000 resamples on per-document CER values.
Seed fixed to 42 (overridable via `--seed`). Implementation:
`benchmark/ocr/metrics.py::bootstrap_ci` — pure stdlib (`random.choices`),
no NumPy dependency. Computed for both `mean_cer` and `mean_wer`; CIs for
field-F1 / ANLS are not currently emitted by the standard report.

Report as: `CER = 0.043 [95% CI: 0.039–0.047]`

### 3.2 Significance Testing

For pairwise engine comparison on the same document set, the
**Wilcoxon signed-rank test** (`scipy.stats.wilcoxon`, two-sided,
`zero_method='wilcox'`) is used. Preferred over the paired t-test because CER
distributions are right-skewed. Pairs with fewer than 10 common documents are
skipped (insufficient power). Implementation:
`benchmark/ocr/report.py::print_significance_matrix`.

**Holm–Bonferroni correction** is applied across all K(K−1)/2 engine pairs
(sort raw p by ascending, multiply rank-*i* p by (m − i)).

**Effect size: Cohen's d** on paired differences —
`d = mean(Δ) / std(Δ, ddof=1)`. Thresholds:
- |d| < 0.2: negligible
- 0.2–0.5: small
- 0.5–0.8: medium — minimum to claim practical superiority
- ≥ 0.8: large

The T4 table prints significance flags `***` (p<0.001), `**` (<0.01),
`*` (<0.05), `ns` otherwise. Requires scipy; if unavailable the table is
skipped and a diagnostic printed.

### 3.3 Minimum Sample Size

Power analysis for two-tailed Wilcoxon test, medium effect (d=0.5), α=0.05, power=0.80:

- Minimum: **N = 100 documents** (exploratory studies)
- Publishable at ICDAR: **N ≥ 300 documents** (stratified)
- Per document type: **N ≥ 50** within each quality tier

---

## 4. Datasets & Artifacts

### 4.0 Datasets Available On-Disk

Concrete files under `benchmark/ocr/data/` — all downloaded, ground-truth-parsed,
registered in `benchmark/ocr/datasets.py`, and ready for benchmark runs.

| Dataset | Path | Images | GT format | Doc types | Script / Paper |
|---------|------|--------|-----------|-----------|----------------|
| **XFUND-PT** | `benchmark/ocr/data/xfund_pt/` | 199 (100 used via `--max-samples 100`) | JSON — box+text+label+linking per word; K–V built from `linking` edges | Real scanned PT forms | ACL 2022, Microsoft Research |
| ~~BID Sample~~ | `benchmark/ocr/data/bid_sample/BID Sample Dataset/` | 286 — **excluded from formal evaluation**, see §4.0.2 | CSV (ISO-8859-1) per-region bboxes | Brazilian ID documents | SIBGRAPI 2020 |
| ESTER-Pt | `benchmark/ocr/data/ester_pt/` | *(not downloaded — 19.6 GB archive, disk-blocked)* | Per-page `.txt` line-level transcriptions | Free-text scans (UFRGS) | ICDAR 2023 |

**The formal benchmark uses XFUND-PT only.** BID is kept on disk for future
GT regeneration but is not scored in `ablation_consolidated.csv`.

Loaders: `load_xfund`, `load_bid` (auto-detects Sample vs fullset via
`*_gt_ocr.txt` presence), `load_ester`.

### 4.0.2 Why BID Sample Is Excluded

Audit (2026-04-13) found a systematic reference/image mismatch in the BID
Sample loader's output. For every class (CNH/CPF/RG × front/back/open), the
reference string aggregated by `load_bid` is the **blank template text** of
the document class (e.g. `"REPÚBLICA FEDERATIVA DO BRASIL / MINISTÉRIO DAS
CIDADES / DEPARTAMENTO NACIONAL DE TRÂNSITO / CARTEIRA NACIONAL DE
HABILITAÇÃO / NOME / APPINHANESI BLAZEK PASSOTTO / ..."`), while the
corresponding image is an anonymized fake ID that visibly contains different
text (e.g. `"PROIBIDO PLASTIFICAR"`, unrelated holder names, placeholder
numbers). All five classical engines converge on CER ≈ 0.87–1.06 and
`macro_field_f1 = 0` across all 286 documents — the OCR output is correct;
the ground truth is not aligned with the image. This is a dataset-parsing
problem, not an engine failure, so reporting it would bias the aggregate
numbers downward by ~0.5 CER.

Until the loader is rewritten to either (a) align each sample's transcription
CSV with its *own* image or (b) regenerate GT from the bounding-box CSVs, BID
is excluded from `ablation_consolidated.csv` and from the T2/T6 tables. The
raw per-doc files under `benchmark/ocr/results/bid_grayscale/` are preserved
for reproducibility.

### 4.0.1 Result Artifacts

Each run writes to a `benchmark/ocr/results/<preprocess>/` directory with five
files:

| File | Content |
|------|---------|
| `run_state.json` | Per-sample results keyed by `(engine, doc_id)` — enables resume |
| `run_meta.json` | Engine versions, seeds, hardware, CLI args, preprocess config |
| `ocr_benchmark_results.json` | Aggregate summary: per-engine CER/WER/F1/ANLS + 95% bootstrap CI |
| `ocr_benchmark_summary.csv` | Flat summary table (engine × metric) |
| `ocr_benchmark_per_doc.csv` | One row per `(engine, doc_id)` — for stratified / significance analysis |

With `--store-texts` enabled, `run_state.json` also carries `reference_text` and
`hypothesis_text` per sample — required for T5 (error analysis) and T7 (entity
recall against anonymizer).

### 4.1 Quality Tiers

| Tier | Description | DPI range | Expected CER |
|------|-------------|-----------|-------------|
| **Clean** | Modern print, no degradation | 300+ | 0.00–0.02 |
| **Degraded** | Real-world scans: noise, stains, skew | 100–200 | 0.05–0.25 |
| **Synthetic** | Artificially degraded with controlled parameters | Variable | 0.01–0.15 |

Each tier must be represented in the test set. Benchmarks on clean documents only
are not representative of real-world performance.

### 4.2 Document Types

| Type | Metric emphasis |
|------|----------------|
| Free text (certidões, contratos) | Page-level CER/WER |
| Structured forms (RG, CPF, CNH) | Field-F1, ANLS, KVRR |
| Tables (declarações, planilhas) | Table-structure F1 + cell CER |
| Mixed (forms with handwriting) | Composite per-region |

Report metrics separately per type. A single aggregate metric masks type-specific
failures.

### 4.3 Evaluation Split

This benchmark evaluates **pre-trained** OCR engines — no training or
fine-tuning is performed, so no train/val split is needed. All samples serve
as **test data**:

- **XFUND-PT:** First 100 documents from `pt.train.json` (via
  `--max-samples 100`). The "train" label is upstream nomenclature; for us
  it is just the larger annotated split. **This is the only split scored in
  the formal tables.**
- **BID Sample:** 286 images on disk but **not scored** (GT/image mismatch
  — see §4.0.2).
- **ESTER-Pt:** Not yet downloaded (19.6 GB, disk-blocked).

Sampling order is deterministic (dataset load order, seed=42) so reruns hit
the same documents. No overlap between datasets. If a subsample is taken, it
is always the first N documents in load order — never random — so resume
semantics stay stable across restarts.

---

## 5. Field Extraction — What the Runner Actually Does

Field-F1 and ANLS require both a **reference** dict and a **predicted** dict of
field values. The reference dict comes directly from the dataset loader
(`Sample.fields`); the predicted dict is built by
`benchmark.ocr.runner._extract_fields`, which is a **heuristic substring
matcher** — not a trained field extractor. Behavior per reference key:

1. If the key is in `datasets.NUMERIC_FIELDS` (see list below), the reference
   value is digits-extracted (`re.sub(r'\D', '', ref)`); the same digit stream
   is searched inside the OCR output's digit stream. Match is all-or-nothing.
2. Otherwise, the reference value is searched case-insensitively as a
   substring of the OCR output. Match is all-or-nothing.
3. When the reference value is empty, the prediction is also empty
   (scored separately in F1).

```python
NUMERIC_FIELDS = {
    "rg_numero", "cpf_numero", "numero_registro", "data_nascimento",
    "data_expedicao", "validade", "livro", "folha", "termo",
}
```

### Implications

- On **XFUND-PT**, field keys come from the dataset's own question strings
  (normalized to snake_case). Values are question *answers* as annotated by
  upstream annotators. The substring heuristic checks whether the
  ground-truth answer appears verbatim in the OCR hypothesis. This is a
  conservative measure of *recoverability*, not of a downstream extractor's
  quality.
- On **BID Sample**, the only reference field is `doc_class` (e.g.
  `CNH_FRENTE`) — a classification label. No per-field F1 is informative
  here; the useful BID signal is page-level CER.
- A trained per-document-type field extractor would improve F1 across the
  board. When that extractor ships, swap `_extract_fields` and rerun the
  matrix. The fields below are the **target schema** that extractor would
  produce — they are not enforced by the current benchmark.

### Target schema (downstream extractor, not yet implemented)

<details>
<summary>RG / CPF / CNH / Certidão — click to expand</summary>

#### RG (Registro Geral)
| Field | Format | Normalization |
|-------|--------|---------------|
| `nome` | Full name | NFC, strip, collapse spaces |
| `rg_numero` | 7–9 digits | Digits only |
| `data_nascimento` | DD/MM/YYYY | Separators → `/` |
| `filiacao_mae` | Full name | NFC, strip |
| `filiacao_pai` | Full name or `—` | NFC, strip |
| `naturalidade` | City/State | NFC, strip |
| `orgao_expedidor` | Abbreviation | Uppercase, strip |
| `data_expedicao` | DD/MM/YYYY | Separators → `/` |

#### CPF
| Field | Normalization |
|-------|---------------|
| `cpf_numero` | Digits only |
| `nome` | NFC, strip |
| `data_nascimento` | Separators → `/` |

#### CNH
| Field | Notes |
|-------|-------|
| `nome` | NFC, strip |
| `cpf_numero` | Digits only |
| `data_nascimento` | Separators → `/` |
| `categoria` | Uppercase strip (A, B, AB, C, D, E) |
| `validade` | Separators → `/` |
| `numero_registro` | Digits only |

#### Certidão de Nascimento
| Field | Notes |
|-------|-------|
| `nome_registrado`, `nome_mae`, `nome_pai` | NFC, strip |
| `data_nascimento` | Separators → `/` |
| `municipio_nascimento`, `cartorio` | NFC, strip |
| `livro`, `folha`, `termo` | Digits only |

</details>

---

## 6. Reproducibility

### 6.1 Actual Per-Run Metadata (`run_meta.json`)

Exactly what the runner writes today (`benchmark/ocr/runner.py::run_benchmark`):

```json
{
  "hardware": {
    "os": "Linux-6.17.0-20-generic-x86_64-with-glibc2.xx",
    "python": "3.12.x",
    "cpu": "x86_64",
    "cuda_available": true,
    "cuda_version": "12.8",
    "gpu": "NVIDIA GeForce RTX 5060 Ti",
    "gpu_vram_gb": 16.0
  },
  "dataset_hash": "<16-hex SHA-256 prefix over sorted (sample_id, image_byte_size)>",
  "n_samples": 100,
  "engines": ["tesseract", "easyocr", "doctr", "surya", "rapidocr"],
  "seed": 42,
  "anls_threshold": 0.5,
  "preprocessing": "grayscale"
}
```

Notes:
- `dataset_hash` is deliberately a lightweight fingerprint (id + byte-size
  per sample) — it is stable across reruns but does not guarantee bit-exact
  image identity. To detect silent image corruption, hash the archive from
  §4.0 separately.
- `preprocessing` is the `__name__` of the composed preprocess callable, i.e.
  the dash-joined step list (e.g. `"grayscale+binarize"`) — or `null` when no
  preprocessing is applied.
- Engine versions, model weights SHAs, pip-freeze hash, and a run-level UUID
  are **not** currently logged. A scientifically-publishable run must capture
  them out of band (virtualenv lockfile, git SHA, CUDA driver) — a TODO
  tracked in this file.

### 6.2 Stochasticity — What's Enforced and What Isn't

- **Bootstrap CI**: deterministic given the seed, always fixed to 42 (or
  `--seed`).
- **Engine inference**: the runner does **not** currently call
  `torch.manual_seed`, `numpy.random.seed`, or
  `torch.backends.cudnn.deterministic = True`. VLM engines that sample
  tokens (e.g. top-k) can therefore vary slightly across runs.
- Documents are processed in loader order; no shuffling.
- Each `(engine, doc_id)` pair is run **exactly once**; re-runs are skipped
  because of the resume state in `run_state.json`. If variance estimates per
  document are required, delete the state file and rerun N times with
  distinct `--out-dir` values, then aggregate offline.

---

## 7. Reporting Standards

### Tables Emitted Today

Source: `benchmark/ocr/report.py::print_full_report`. Every table is printed
to stdout and CSV/JSON copies land in the run's `--out-dir`.

| Table | Content | Emitted by |
|-------|---------|------------|
| T1: Dataset Statistics | Per-tier and per-doc-type counts, total docs | `print_dataset_stats` |
| T2: Primary Results | CER, WER, CER-NoDiacritic, Field-F1, ANLS, Latency — CER/WER with 95% CI | `print_primary_results` |
| T3: Stratified CER | Mean CER per `quality_tier::doc_type` cell | `print_stratified_results` |
| T4: Significance Matrix | Pairwise Wilcoxon p + Holm p + Cohen's d | `print_significance_matrix` (requires scipy) |
| T5: Error Analysis | Top-15 character substitution pairs (count + % of errors) | `print_error_analysis` (requires `--store-texts`) |
| T6: Preprocess Ablation | CER/WER/F1/latency per engine × preprocess step + Δ vs baseline | `benchmark/ocr/consolidate.py` (separate CLI; merges all per-step `run_state.json` files) |

### Tables / Figures NOT Yet Emitted

- **Field-F1 / ANLS confidence intervals** — only CER and WER CIs are
  computed in `bootstrap_ci` today. Add via wrapper if needed.
- **F1 (violin CER distribution), F2 (error-vs-quality scatter),
  F3 (confusion heatmap)** — figures described above are publication
  targets; no plotting code ships in this benchmark. Re-use
  `ocr_benchmark_per_doc.csv` with Seaborn/Matplotlib to produce them.
- **Critical Difference diagram** (Demšar 2006) — preferred over radar
  charts for multi-engine ranking summaries; also a publication target.

### Note on Radar Charts

Radar charts are acceptable for visual communication in talks and
supplementary material, but must not serve as primary evidence. Area
distortion and axis-scaling sensitivity make them scientifically unreliable.
Primary evidence must be tabular with confidence intervals. When included,
label explicitly as "for illustration only."

---

## 8. Alternative Data Strategies (Not Implemented — Documented for Future Work)

### Level 2 — Synthetic Document Generation

For document types where no public labeled dataset exists (certidão de nascimento,
comprovante de residência, cheques, extratos bancários), generate synthetic documents
with controlled properties:

1. Use `Faker` (Python) with `pt_BR` locale to generate realistic Brazilian PII
2. Apply document templates (SVG/HTML → PDF render) with correct field layouts
3. Render to images at controlled DPI (300, 150, 72) to simulate quality tiers
4. Apply degradation pipeline: Gaussian noise, blur, rotation, perspective warp,
   stain simulation (using `albumentations` or `imgaug`)
5. Ground truth is exact because synthetic data is generated deterministically

Pros: full control over quality tiers and document type distribution; no privacy risk.
Cons: domain gap — synthetic documents may not reflect real-world degradation patterns.

### Level 3 — Zero-Shot Ground Truth via VLM Oracle

When real documents are available but lack ground truth annotations:

1. Process each image through a high-accuracy VLM (GPT-4o, GLM-OCR, LightOn OCR-2)
   as an "oracle"
2. Use oracle output as pseudo-ground-truth
3. Evaluate other engines against the oracle
4. Report oracle CER against itself (always 0) and note this is pseudo-GT evaluation

Caveat: Oracle errors propagate as false negatives/positives. Use only when no human-
annotated ground truth is available. Disclose explicitly in methodology.

Practical workflow: collect documents the user has already processed with AnonShield
(with consent and privacy controls), use VLM to produce pseudo-GT, evaluate all
engines. Compare anonymization completeness (entity recall) across engines as a
downstream metric complementary to raw CER.

---

## 9. OCR Engines Under Evaluation

The benchmark covers **16 engines** registered in `src/anon/ocr/factory.py`,
split into two families. All engines are evaluated on the full preprocess
matrix (§10) × dataset matrix (§4) with identical normalization (§2) and
metrics (§1).

### 9.1 Classical / Traditional OCR (8 engines)

CPU- or GPU-accelerated pipelines built from detector + recognizer components.
Small models (sizes are approximate and refer to the weights loaded by the
engine wrapper in `src/anon/ocr/`).

| Engine | Key | Backbone | Size | License | Notes |
|--------|-----|----------|------|---------|-------|
| Tesseract | `tesseract` | LSTM (legacy + neural) | ~30 MB | Apache 2.0 | Baseline; `--psm 6` default |
| EasyOCR | `easyocr` | CRAFT + CRNN (ResNet) | ~120 MB | Apache 2.0 | PT-BR langs=`["pt"]` |
| PaddleOCR | `paddleocr` | PP-OCRv4 (DB + SVTR-LCNet) | ~15 MB | Apache 2.0 | PT via `latin` recognizer |
| DocTR | `doctr` | DB-ResNet-50 + CRNN-VGG16 | ~95 MB | Apache 2.0 | PyTorch backend |
| OnnxTR | `onnxtr` | DocTR models in ONNX runtime | ~95 MB | Apache 2.0 | GPU-optional |
| KerasOCR | `kerasocr` | CRAFT + CRNN (TF) | ~130 MB | MIT | English-only weights; included for completeness |
| Surya | `surya` | Custom det + rec transformers | ~500 MB | GPL-3.0 | 90+ languages, PT trained |
| RapidOCR | `rapidocr` | PaddleOCR weights → ONNX | ~12 MB | Apache 2.0 | CPU-first; GPU via `onnxtr[gpu]` extra |

Measured per-document latency on grayscale XFUND-PT (100 docs, RTX 5060 Ti):
DocTR 0.34 s, Tesseract 1.03 s, EasyOCR 2.51 s, RapidOCR 3.64 s, Surya 5.07 s.

### 9.2 Vision-Language-Model OCR (8 engines)

End-to-end multimodal models. Latency varies widely by architecture and
document length — populated in the T2 `Latency(s)` column once each engine's
run completes. All run locally (no external API).

| Engine | Key | HuggingFace ID | Params | License | External benchmark |
|--------|-----|---------------|--------|---------|-------------------|
| **GLM-OCR** | `glm_ocr` | `zai-org/GLM-4.5V` / GLM-4.1V-9B | 9 B | MIT | **OmniDocBench 94.62** (SOTA) |
| **PaddleOCR-VL** | `paddle_vl` | `PaddlePaddle/PaddleOCR-VL` (0.9 B ERNIE-4.5) | 0.9 B | Apache 2.0 | OmniDocBench 94.50 |
| **DeepSeek-OCR** | `deepseek_ocr` | `deepseek-ai/DeepSeek-OCR` | 3 B | MIT | OmniDocBench 91.09 |
| **MonkeyOCR-pro** | `monkey_ocr` | `echo840/MonkeyOCR-pro-1.2B` | 1.2 B | Apache 2.0 | OmniDocBench 86.96 |
| **LightOn-OCR** | `lighton_ocr` | `lightonai/LightOnOCR-1B-32k-1025` | 1 B | Apache 2.0 | Strong long-page perf |
| **Chandra-OCR** | `chandra_ocr` | `datalab-to/chandra` | 9 B | Apache 2.0 | olmOCR-Bench 83.1 |
| **DotsOCR** | `dots_ocr` | `rednote-hilab/dots.ocr` | 3 B | Apache 2.0 | Small-footprint VLM |
| **Qwen2.5-VL** | `qwen_vl` | `Qwen/Qwen2.5-VL-7B-Instruct` | 7 B | Apache 2.0 | Multilingual (PT-BR) |

### 9.3 Engine Exclusion Policy

An engine is excluded from a specific T2 reporting row only when it raises on
every sample of a dataset (systematic failure). Per-sample failures (transient
OOM, malformed image) are recorded as `CER = 1.0` and counted in the sample
size — not silently dropped. This keeps the significance tests (§3.2) honest.

Each run logs per-sample latency and throughput (samples/s) so the
accuracy/latency trade-off is published alongside CER.

---

## 9.4 Engine Coverage — What Is Actually Scored Today

`ablation_consolidated.csv` (2026-04-13) contains **43 rows** covering:

| Engines scored | Preprocess configs | Dataset |
|---------------|--------------------|---------|
| Classical (5): `tesseract`, `easyocr`, `doctr`, `surya`, `rapidocr` | 8 single-step configs (§10.2) + `none` baseline | XFUND-PT, N=100 |
| VLM (2): `glm_ocr`, `lighton_ocr` | `grayscale` only | XFUND-PT, N=100 |

Pending — must share VRAM sequentially with the GPU (no parallel sidecar runs,
see runbook `run_experiments.sh`):

- `paddle_vl`, `monkey_ocr` — via `legacy_vlm` sidecar (transformers 4.51.3).
- `kerasocr` — via `kerasocr` sidecar (TF 2.17 + bundled CUDA).
- `deepseek_ocr`, `chandra_ocr`, `dots_ocr`, `qwen_vl` — main image with
  cuda-devel + flash-attn (pending rebuild).
- `paddleocr`, `onnxtr` — classical, registered but not yet scored.

**Engine Family × Preprocess coverage is not yet square.** VLMs are only
grayscale so far because their per-document latency (9–15 s) makes a full
9-config sweep ≈ 2 GPU-hours per engine. When published, any VLM × preprocess
cell not in the CSV is explicitly reported as "not evaluated" rather than
imputed.

---

## 10. Preprocessing Evaluation Scope

### 10.1 Single-Step Ablation Only

The preprocess ablation (T6) evaluates each preprocessing step **in isolation** — one
step per run, plus a `none` baseline. Combined-step runs (e.g., `grayscale+binarize`,
full `scan` preset) are intentionally **excluded** from the formal evaluation.

**Rationale:**
- The step-combinations space is 2⁸ = 256 configurations (8 steps: `grayscale`,
  `binarize`, `deskew`, `clahe`, `denoise`, `upscale`, `morph_open`, `border`). At
  ~1 h per 5-engine run, the full ablation exceeds 250 GPU-hours. Not justified given
  the interpretability loss from interaction effects.
- Single-step results isolate the marginal contribution of each operation and are
  directly comparable across engines and datasets.
- Named presets (`scan`, `photo`, `fax`) ship as product features but are *not* part
  of the formal benchmark — they serve users, not the published methodology.

### 10.2 Per-Step Run Matrix

Exact parameters from `src/anon/ocr/preprocessor.py` (OpenCV path; Pillow
fallback is a strict subset — `deskew`, `binarize`, `morph_open` become
no-ops when OpenCV is unavailable).

| Step | Exact behaviour |
|------|-----------------|
| `none` / `baseline` | Empty step list; image bytes pass through unchanged |
| `grayscale` | `cv2.COLOR_BGR2GRAY` (no-op if already single-channel) |
| `upscale` | 2× `cv2.INTER_LANCZOS4` when `max(h,w) < 1000 px`, else pass-through |
| `clahe` | Force grayscale, then `cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(img)` |
| `denoise` | Force grayscale, then `cv2.GaussianBlur(img, (3,3), 0)` |
| `deskew` | Otsu threshold → `cv2.minAreaRect` on foreground pixels → rotate; skipped when `\|angle\| < 0.5°` or fewer than 10 foreground pixels. No hard angle cap. **Observed regression on XFUND-PT**: mean CER ≈ 0.64–0.72 vs baseline 0.30. XFUND pages are already upright, so `minAreaRect` latches onto text-line orientation and rotates the page by up to 90° when a column of vertical text dominates. Reported in T6 as a cautionary signal; not recommended without a pre-check (e.g. Hough-line angle histogram) before enabling. |
| `binarize` | **Adaptive Gaussian threshold** — `cv2.adaptiveThreshold(img, 255, ADAPTIVE_THRESH_GAUSSIAN_C, THRESH_BINARY, block=31, C=10)`. Otsu is **not** used by this step; it appears inside `deskew` only as a foreground mask. |
| `morph_open` | Force binary (threshold at 127), then `cv2.MORPH_OPEN` with a 2×2 rectangular kernel |
| `border` | `cv2.copyMakeBorder(img, 20, 20, 20, 20, BORDER_CONSTANT, value=255)` — pure white, fixed 20 px on all sides |

Named presets `scan`, `photo`, `fax` exist in `preprocessor.PRESETS` for
end users but are **not** evaluated in this benchmark — see §10.1.

### 10.3 Output Directory Convention

One `--out-dir` per step so each run has its own `run_state.json` and resumes
independently. The chain script (`benchmark/ocr/run_all_preprocess.sh`) uses
the name `baseline` for the no-preprocess run — which matches the
`CONFIG_ORDER` in `consolidate.py`.

```
benchmark/ocr/results/
├── baseline/      # no --preprocess flag
├── grayscale/     # --preprocess grayscale
├── binarize/
├── deskew/
├── clahe/
├── denoise/
├── upscale/
├── morph_open/
└── border/
```

A single `run_state.json` cannot mix preprocess configurations because
`(engine, doc_id)` keys would collide across different input renderings of
the same document.

### 10.4 Consolidation

The consolidator (`benchmark/ocr/consolidate.py`) merges results across per-step
directories into the T6 matrix. Each cell reports CER with 95% bootstrap CI. Rows
are engines, columns are preprocess steps. The `none` baseline is used to compute
**Δ-CER per step** — the improvement (or regression) attributable to that step.

### 10.5 VLM Engines — Same Matrix

VLM engines (`paddle_vl`, `glm_ocr`, `lighton_ocr`, `monkey_ocr`,
`deepseek_ocr`, `chandra_ocr`, `dots_ocr`, `qwen_vl`) use the same per-step
matrix. Many VLMs perform internal preprocessing; the ablation still surfaces
whether an external step helps or hurts the model's built-in pipeline.
VLM runs write to per-engine sub-directories (from
`benchmark/ocr/run_vlm_grayscale.sh`):

```
benchmark/ocr/results/<step>_vlm_<engine>/    # e.g. grayscale_vlm_paddle_vl
```

One engine per directory because VLM VRAM footprints (0.9 B–9 B parameters)
prevent loading multiple models concurrently.

---

## 11. Audit Log — Methodology Corrections

Every change to scoring scope or metric definition is logged here so that
prior `ablation_consolidated.csv` snapshots remain interpretable.

### 2026-04-13 — BID exclusion + smoke purge

1. **Removed BID Sample from formal tables.** GT string aggregated by
   `load_bid` does not match the rendered image per sample (§4.0.2).
   All five classical-engine BID rows (`bid_grayscale`, n=286) and the
   `bid_smoke` row (n=5) deleted from `ablation_consolidated.csv`.
   Raw per-doc data retained under `benchmark/ocr/results/bid_grayscale/`.
2. **Removed grayscale smoke-test rows.** Rows with `n_docs < 100`
   (`tesseract`, `chandra_ocr`, `dots_ocr`, `qwen_vl` on grayscale, n=2)
   are not publishable; a proper 100-doc re-run for the three VLMs is
   tracked as a pending task.
3. **Added VLM grayscale rows from separate result dirs.** `glm_ocr`
   (n=100, mean_cer=0.3217) and `lighton_ocr` (n=100, mean_cer=0.6735)
   were previously in their own per-engine directories; they are now
   merged into the master CSV.
4. **Deskew flagged as suspect.** Not deleted (it is a real measurement),
   but §10.2 now explains the regression mechanism.

---

## Key References

- Levenshtein (1966): Levenshtein distance
- Damerau (1964): Damerau–Levenshtein (transpositions)
- Mathew et al., WACV 2021: DocVQA + ANLS metric
- Jaume et al., ICDAR-OST 2019: FUNSD evaluation protocol
- Demšar, JMLR 2006: Critical Difference diagrams
- Dror et al., ACL 2018: Statistical significance in NLP
- Cohen (1988): Statistical Power Analysis (effect sizes)
- Santos et al., ICDAR 2023: ESTER-Pt evaluation protocol
- OmniDocBench (2024, arXiv): multi-modal document benchmark
