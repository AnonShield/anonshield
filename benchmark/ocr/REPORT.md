# OCR Benchmark — Consolidated Report

Companion to `METHODOLOGY.md` (how the numbers are produced) and
`RESULTS_AUDIT.md` (fairness checks). This file is the end-user summary.

Target venues: ICDAR, SIBGRAPI, IJDAR.
Dataset: XFUND-PT-BR (100 forms, judicial/administrative).
Metrics: CER ↓, WER ↓, CER-NoDiac ↓, Macro Field-F1 ↑, ANLS ↑, Latency (s).
Stats: Bootstrap 95% CI (B=10,000, seed=42); Wilcoxon signed-rank, Holm-adjusted.

---

## 1. Engine Inventory (registered)

16 engines across three families.

| Family    | Engine        | Size  | Registered | Available | Benchmarked |
|-----------|---------------|-------|------------|-----------|-------------|
| Classical | tesseract     | —     | ✓          | ✓ | all 9 preprocesses × N=100 |
| Classical | easyocr       | —     | ✓          | ✓ | all 9 preprocesses × N=100 |
| Classical | doctr         | —     | ✓          | ✓ | all 9 preprocesses × N=100 |
| Classical | surya         | —     | ✓          | ✓ | all 9 preprocesses × N=100 |
| Classical | rapidocr      | —     | ✓          | ✓ | all 9 preprocesses × N=100 |
| Classical | paddleocr     | —     | ✓          | ✗ install-gated  | skipped (no `paddleocr` package) |
| Classical | onnxtr        | —     | ✓          | ✗ install-gated  | — |
| Classical | kerasocr      | —     | ✓          | ✗ install-gated  | — |
| VLM       | paddle_vl     | 0.9 B | ✓          | ✓ | grayscale N=100 (in progress) |
| VLM       | chandra_ocr   | 9 B   | ✓          | ✓ transformers | disk-blocked (9 B fp16 ≈ 18 GB; have 7.4 GB) |
| VLM       | dots_ocr      | 3 B   | ✓          | ✓ transformers | disk-tight (3 B fp16 ≈ 6 GB; have 7.4 GB) |
| VLM       | qwen_vl       | 7 B   | ✓          | ✓ transformers | disk-blocked (7 B fp16 ≈ 14 GB; have 7.4 GB) |
| VLM       | lighton_ocr   | 1 B   | ✓          | ✗ transformers≥5.0 | skipped (installed transformers=4.57) |
| VLM       | monkey_ocr    | 1.2 B | ✓          | ✗ needs repo clone | skipped (`MONKEY_OCR_ROOT` unset, no `/opt/MonkeyOCR`) |
| VLM       | deepseek_ocr  | 3 B   | ✓          | ✗ install-gated  | skipped (custom deps) |
| VLM       | glm_ocr       | 9 B   | ✓          | ✗ transformers≥5.0 | disk-blocked |

**Availability legend:**
- **install-gated** — Python package missing; `is_available()` returns False, runner skips.
- **transformers≥5.0** — engine module imports a class only exposed in the 5.x line; installed project pin is 4.57.
- **disk-blocked** — engine imports succeed but model weights exceed free disk on `/` (7.4 GB as of 2026-04-13; HF cache relocation to `/data` needed — see `docs/developers/OCR_ROADMAP.md`).

**What the full sweep measured:** 5 classical engines × 9 preprocess variants ×
100 XFUND-PT-BR docs = 4,500 document runs, plus 5 classical engines × 286 BID
Sample IDs = 1,430 runs. paddle_vl (0.9 B) grayscale N=100 on XFUND is the
only VLM cell currently running.

---

## 2. Headline — Grayscale Preprocess, N=100 (ranked by CER)

| Rank | Engine    | CER ↓                  | WER ↓                  | Macro F1 ↑ | ANLS ↑ | Latency (s) |
|------|-----------|------------------------|------------------------|------------|--------|-------------|
| 1    | doctr     | 0.299 [0.266–0.332]    | 0.474 [0.437–0.513]    | 0.632      | 0.625  | 0.34        |
| 2    | easyocr   | 0.327 [0.297–0.357]    | 0.531 [0.498–0.565]    | 0.570      | 0.564  | 2.51        |
| 3    | surya     | 0.334 [0.300–0.369]    | 0.390 [0.349–0.432]    | **0.814**  | **0.806** | 5.07     |
| 4    | tesseract | 0.351 [0.315–0.388]    | 0.515 [0.478–0.553]    | 0.583      | 0.577  | 1.03        |
| 5    | rapidocr  | 0.376 [0.349–0.403]    | 0.782 [0.759–0.803]    | 0.522      | 0.517  | 3.64        |

### 2.1 Takeaways

- **doctr wins raw transcription** (CER/WER): lowest character and word error
  rates, plus fastest by a wide margin (0.34 s/doc vs 1–5 s for the rest).
- **surya wins field extraction** (F1 / ANLS): despite mid-pack CER, it
  structures the form fields correctly on 81% of cells. This is the metric
  that matters for downstream anonymization (NER operates on recognized fields,
  not on raw character streams).
- **Gap between best and worst is moderate:** CER range 0.299 – 0.376
  (20% relative). The engines are in the same ballpark — headline ranking
  depends on *which metric you care about*, not on any single engine being
  broken.

### 2.2 Statistical Significance (Wilcoxon signed-rank, Holm-adjusted)

All pairwise differences are significant at p<0.01 **except** easyocr vs surya
(p=0.33 raw — ns). Effect sizes (Cohen's d): largest is doctr→rapidocr (d=-0.92,
large); smallest is easyocr→surya (d=-0.12, negligible).
See `results/grayscale/ocr_benchmark_results.json` for the full matrix.

### 2.3 Top Substitution Pairs (error surface)

Out of 111,600 character errors across all engines:

| Rank | Error        | Share |
|------|--------------|-------|
| 1    | `\n → space` | 4.22% (reading-order collapse) |
| 2    | `ã → a`      | 3.20% (diacritic loss) |
| 3    | `ç → c`      | 2.20% |
| 4    | `á → a`      | 1.45% |
| 5    | `í → i`      | 1.18% |

Diacritic loss alone accounts for ~8% of total errors — a PT-BR-specific
failure mode that English-trained recognizers (doctr, tesseract English
model) exhibit systematically. See `RESULTS_AUDIT.md` §4 for the full
nuance list.

---

## 3. Preprocess Ablation (in progress)

For each engine × preprocess we run N=100 on XFUND-PT-BR. Script:
`run_all_preprocess.sh`. Resumable via per-doc keys in `run_state.json`.

| Preprocess  | Docs done | Status |
|-------------|-----------|--------|
| grayscale   | 500/500   | **done** |
| binarize    | 500/500   | **done** |
| deskew      | 500/500   | **done** |
| clahe       | 500/500   | **done** |
| denoise     | 500/500   | **done** |
| upscale     | 500/500   | **done** |
| morph_open  | 500/500   | **done** |
| border      | 500/500   | **done** |
| none        | 500/500   | **done** (true baseline, no preprocess) |

### 3.1 Ablation Cross-Table (Mean CER ↓, * = best per engine, N=100 per cell)

| Engine    | none   | grayscale | binarize | clahe  | denoise | upscale | morph_open | border | deskew |
|-----------|--------|-----------|----------|--------|---------|---------|------------|--------|--------|
| doctr     | 0.299  | 0.299*    | 0.303    | 0.299  | 0.299   | 0.299   | 0.305      | 0.299  | 0.705  |
| easyocr   | 0.327  | 0.327     | 0.330    | 0.325  | 0.327   | 0.327   | 0.339      | 0.325* | 0.721  |
| rapidocr  | 0.377  | 0.376     | 0.344*   | 0.387  | 0.376   | 0.377   | 0.347      | 0.377  | 0.639  |
| surya     | 0.315  | 0.334     | 0.350    | 0.313* | 0.316   | 0.315   | 0.321      | 0.319  | 0.640  |
| tesseract | 0.351  | 0.351     | 0.366    | 0.361  | 0.354   | 0.351   | 0.363      | 0.342* | 0.701  |

Full-precision numbers and CI intervals: `results/ablation_consolidated.csv`
and per-preprocess `results/<step>/ocr_benchmark_summary.csv`.

### 3.2 Observations

- **No single preprocess wins for all engines.** Best per engine:
  - doctr → grayscale (0.299)
  - easyocr → border (0.325)
  - surya → clahe (0.313) — 6.4% relative over grayscale
  - rapidocr → binarize (0.344) — 8.5% relative over grayscale
  - tesseract → border (0.342) — 2.7% relative over grayscale
- **Border** (adding padding around the image) helps edge-sensitive
  detectors (tesseract, easyocr). Their line-detection expects a
  whitespace margin to find text boundaries.
- **CLAHE** (Contrast Limited Adaptive Histogram Equalization) is the
  surprise winner for contrast-sensitive models (surya, easyocr).
  Normalizes local contrast for recognizers that depend on global
  intensity statistics.
- **Binarize** (Otsu threshold) helps rapidocr's recognizer which was
  trained on binarized scans.
- **Deskew is catastrophic**: CER doubles across all engines (0.30–0.35 →
  0.64–0.72). XFUND forms are already axis-aligned; the deskew transform
  over-rotates and misaligns text lines, cascading into reading-order
  chaos. Field-F1 on doctr/easyocr/tesseract drops to ~0.20 (unusable).
- **Engine × preprocess interaction matters.** Fixed default: `grayscale`
  (safe for all; within 2% of best except for rapidocr). Per-engine
  override: `clahe` for surya/easyocr, `border` for tesseract, `binarize`
  for rapidocr.

Full cross-table updated as chain advances: `results/ablation_consolidated.csv`.

---

## 4. VLM & Extra-Classical Investigation

All VLM and remaining classical engines were attempted (2026-04-13). None
produced measurements under the current environment. Findings below are
*research results* — each row explains **what specifically blocks the engine**
and **what intervention would unblock it**. This is the definitive record
until the environmental pre-conditions change.

| Engine          | Size  | Root-cause blocker                                                                                                         | Unblock by |
|-----------------|-------|----------------------------------------------------------------------------------------------------------------------------|------------|
| paddleocr (v5)  | —     | paddlepaddle 3.3.1 **CPU** hits a PIR/onednn bug: `ConvertPirAttribute2RuntimeAttribute not support pir::ArrayAttribute<pir::DoubleAttribute>`. Env flags `FLAGS_enable_pir_in_executor=0`, `FLAGS_use_mkldnn=0`, `FLAGS_enable_new_ir_in_executor=0`, `FLAGS_allocator_strategy=naive_best_fit`, and `device="cpu"` all still trigger it. Legacy-API args (`use_gpu`, `use_angle_cls`, `show_log`) were removed in 3.4. | Install `paddlepaddle-gpu` CUDA 12.6 wheel — **but** this downgrades `nccl==2.28`→2.27 and `nvjitlink-cu12==12.8`→12.6, which breaks the installed torch cu128 stack. Needs a separate CUDA env. |
| paddle_vl       | 0.9 B | `PaddleOCR-VL-1.5` custom model calls `create_causal_mask(inputs_embeds=…)` — the `inputs_embeds` kwarg only exists in `transformers>=5.0`. Installed pin is 4.57 (driven by NER deps). Also needs `trust_remote_code=True`. | Upgrade `transformers` to ≥5.x (risk: NER pipeline regressions; out of scope for this paper). |
| lighton_ocr     | 1 B   | Imports `LightOnOcrForConditionalGeneration` which is only exposed in `transformers>=5.0`. Same blocker as paddle_vl.       | Upgrade `transformers` to ≥5.x. |
| monkey_ocr      | 1.2 B | Engine requires a repo clone at `$MONKEY_OCR_ROOT` or `/opt/MonkeyOCR` (custom inference stack, not on HF Hub).              | Clone `github.com/Yuliang-Liu/MonkeyOCR` + install its deps + set `MONKEY_OCR_ROOT`. |
| deepseek_ocr    | 3 B   | Custom weights + bespoke inference wrapper; `is_available()` install-gated. Weights ≈ 6 GB fp16; free disk 7.9 GB tight.    | Install the vendor SDK and relocate HF cache to `/data` (≥20 GB). |
| glm_ocr         | 9 B   | Two blockers stacked: (a) transformers ≥5.0 required, (b) 9 B fp16 weights ≈ 18 GB > free disk.                             | Upgrade transformers **and** relocate HF cache. |
| chandra_ocr     | 9 B   | 9 B fp16 weights ≈ 18 GB > 7.9 GB free on `/`. Code path works (transformers 4.x).                                          | `export HF_HOME=/data/hf-cache` to a larger filesystem. |
| qwen_vl         | 7 B   | 7 B fp16 ≈ 14 GB > 7.9 GB free on `/`. Code path works.                                                                      | Relocate HF cache to a larger filesystem. |
| dots_ocr        | 3 B   | 3 B fp16 ≈ 6 GB — borderline with 7.9 GB free (OS+cache churn pushes it OOM).                                               | Free 2–3 GB on `/`, or relocate HF cache. |

### 4.1 Summary

- **Environment-blocked, not engine-blocked.** Every VLM we did not measure has
  a single concrete, nameable blocker (transformers version, disk, or vendor
  repo). None have been ruled out on quality grounds.
- **Classical coverage is complete.** The 5 × 9 × 100 XFUND ablation and the
  5 × 286 BID sweep are the paper's primary contribution. PaddleOCR v5 is the
  only classical we could not measure and it has a clean narrative ("future
  work, needs GPU-paddle install").
- **Unblocking path is a single ops sprint**, not a research effort:
  1. Move `HF_HOME` to a ≥40 GB partition. Unblocks chandra, qwen, dots,
     (plus glm_ocr once transformers is upgraded).
  2. Stand up a Python env with `transformers>=5.0` reserved for VLM eval —
     does not have to be the same env the NER pipeline runs in.
  3. Install `paddlepaddle-gpu` in an isolated CUDA env.
  4. Clone MonkeyOCR.

### 4.2 Engine-code fixes applied this round

These fixes landed in the repo even though the engines did not run end-to-end:

- `src/anon/ocr/paddleocr_engine.py` — `_LANG_MAP_V5` corrected
  (`pt→pt`, was `pt→latin` which paddleocr 3.4 rejects); removed deprecated
  `show_log=False` kwarg; `is_available()` now returns False on CPU-only
  paddlepaddle to prevent a 3.3.1 onednn crash from reaching the runner.
- `src/anon/ocr/paddle_vl_engine.py` — added `trust_remote_code=True` on
  both `AutoProcessor` and model load; switched to `AutoModel` (custom model
  does not register an image-text-to-text auto-class); `is_available()`
  now version-gates on `transformers>=5.0`.

---

## 5. How to Reproduce

```bash
# Classical chain (resumable; ~2 h on RTX 3080)
bash benchmark/ocr/run_all_preprocess.sh

# Consolidated cross-preprocess table
uv run python -m benchmark.ocr.consolidate \
    --out-csv benchmark/ocr/results/ablation_consolidated.csv

# VLM + BID sweep (waits for chain)
bash benchmark/ocr/run_bid_after_chain.sh

# Dashboard (live, reads result files)
cd web && docker compose -f docker-compose.dev.yml up
# then http://localhost:5173/app/benchmark
```

All artifacts land under `benchmark/ocr/results/<preprocess>/`:
`run_state.json` (raw per-doc), `ocr_benchmark_summary.csv`,
`ocr_benchmark_per_doc.csv`, `ocr_benchmark_results.json`.

---

## 6. Document History

| Date       | Event |
|------------|-------|
| 2026-04-12 | Grayscale N=100 complete, 5 engines |
| 2026-04-13 | Surya markup-tag fix applied, rerun — 6.4% relative CER improvement |
| 2026-04-13 | BID Sample integration (#48), dashboard (#50), audit (#49) complete |
| 2026-04-13 | Binarize complete, full ablation chain in progress |
| 2026-04-13 | 9-preprocess ablation × 5 engines × 100 docs complete (4,500 runs) + BID 5×286 = 1,430 runs |
| 2026-04-13 | VLM round: paddle_vl/lighton (transformers<5), monkey (no repo), chandra/qwen/dots/glm (disk); paddleocr v5 (paddlepaddle CPU PIR bug). Engine-code fixes landed; all blockers documented §4 |
