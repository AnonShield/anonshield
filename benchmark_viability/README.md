# Viability Test: XFUND-PT Ground Truth Analysis

**Goal**: Determine whether XFUND-PT ground truth incompleteness causes
ranking inversions between classical OCR engines and VLMs.

**Hypothesis (revised)**: The original DATASET_LIMITATIONS.md claimed GT omits
handwritten content. Initial analysis of pt_train_75 shows the GT actually
*contains* most fill-in content, but the high CER (~0.50) comes from
**format divergence** between GT's deconstructed items and VLMs' structured
reading. This test quantifies the phenomenon across 10+ documents and
multiple engines to determine if there's a publishable finding.

## Structure

```
analyze_gt.py          — Step 0-1: Extract and compare GT content vs images
collect_results.py     — Step 2: Gather existing OCR results for selected docs
compute_metrics.py     — Step 3: CER with original GT, normalized GT, content-only
report.py              — Step 4-5: Generate viability report with decision
Dockerfile             — Reproducible environment
```
