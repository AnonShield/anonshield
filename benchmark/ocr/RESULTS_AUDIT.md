# Benchmark Results — Fairness Audit

Companion to `METHODOLOGY.md` — this document records fairness checks done on
the emitted results so future readers (and future benchmark runs) can trust the
headline numbers.

Scope: grayscale preprocess, XFUND-PT, N=100, engines doctr / easyocr / surya /
tesseract / rapidocr. Binarize results partial at time of writing.

## 1. Summary

| Engine    | CER (grayscale) | Hyp/Ref length ratio | Empty hyps | CER > 1.0 | Systemic bias |
|-----------|-----------------|----------------------|------------|-----------|---------------|
| doctr     | 0.299           | 0.99                 | 0          | 0         | Diacritic loss (legitimate — English-trained recognizer) |
| easyocr   | 0.327           | 0.98                 | 0          | 0         | Reading order |
| surya     | 0.334           | 1.03                 | 0          | 0         | **HTML markup emission — fix applied, see §3** |
| tesseract | 0.351           | 1.00                 | 0          | 0         | Reading order |
| rapidocr  | 0.376           | 0.89                 | 0          | 0         | Reading order (stricter than engines above) |

## 2. Sample Inputs & Outputs

Picked the median-CER document per engine to make the "typical error" visible.
Full records in `benchmark/ocr/results/grayscale/run_state.json`.

### 2.1 Reference (XFUND annotator, document xfund_train_pt_train_0)

```
Poder Judiciário do Estado de Minas Gerais
FORMULÁRIO QUANTO À APLICAÇÃO DAS
MEDIDAS SOCIOEDUCATIVAS
COMARCA:
I - Considerações iniciais
…
Nome:
```

Reference text is line-joined from annotator word boxes. Reading order is the
annotator's choice, not a canonical left-to-right / top-to-bottom.

### 2.2 Tesseract hyp (same doc, CER=0.259)

```
Poder Judiciario do Estado de Minas Gerais
FORMULARIO QUANTO A APLICAGAO DAS
…
```

Error mix: diacritic loss (`ã → a`, `Ç → G`), reading-order drift in the form
fields (`Nome: Anna C Rocha` emitted inline rather than in XFUND's separate-line
style), no hallucinations.

### 2.3 Surya hyp (same doc, pre-fix)

Contains `<b>`, `<math>`, `<u>`, `<sup>`, `<br>`, `<sub>` tags emitted as part
of the text. These tags do not appear in any XFUND reference — they are
markup Surya attaches to layout elements (bold cells, equations). Each tag
char is counted as a substitution error by the CER computation.

## 3. Surya Markup Issue — Finding & Fix

**Finding**: 93 of 100 grayscale Surya hypotheses contained at least one
`<tag>` token. Frequency of tags in the grayscale run:

| Tag | Occurrences |
|---|---|
| `<b>` / `</b>` | 342 |
| `<math>` / `</math>` | 64 |
| `<u>` / `</u>` | 49 |
| `<sup>` / `</sup>` | 25 |
| `<br>` | 18 |
| `<sub>` / `</sub>` | 7 |

**Impact**: stripping the tags lowers Surya grayscale mean CER from
**0.3341 → 0.3126** (6.4% relative improvement). Surya's F1/ANLS leadership
does not change — those metrics already ignore tag tokens because of the
substring-based `_extract_fields` routine.

**Fix**: `src/anon/ocr/surya_engine.py` now strips
`<(b|i|u|sup|sub|br|math|em|strong)>` tags (case-insensitive, opening + closing)
before returning text. The fix regex: `re.compile(r"</?(?:b|i|u|sup|sub|br|math|em|strong)>", re.IGNORECASE)`.

**Rerun status**: applied 2026-04-13. Grayscale and binarize Surya numbers
recorded before this date reflect the buggy output; all subsequent preprocess
steps use the fixed engine. Surya grayscale+binarize will be selectively rerun
after the full preprocess chain completes.

## 4. Other Nuances — Documented, Not Bugs

### 4.1 Reading-order mismatch (affects every engine)

XFUND's `all_text` is built by joining word-box `text` fields in annotator order
— generally reading order but not guaranteed for multi-column forms. Each OCR
engine reconstructs reading order with its own layout heuristics (top-to-bottom
/ left-to-right on bounding boxes). Divergence between engine order and
annotator order contributes to CER/WER but is not an engine defect.

### 4.2 DocTR diacritic loss (legitimate weakness)

DocTR uses an English-trained CRNN recognizer and strips most diacritics. The
`cer_no_diac` metric (defined in `metrics.py`, emitted in `per_doc.csv`) lets
evaluators see how much of DocTR's CER is pure-ASCII drift. In grayscale,
DocTR's CER drops from 0.299 → ≈0.22 when diacritics are folded.

### 4.3 Rapidocr shorter output (0.89 ratio)

Rapidocr is more conservative — it drops very low-confidence boxes. This
increases precision on field extraction (Field-F1 holds up) but hurts recall
on full-page CER (more deletions against the reference).

### 4.4 No empty hypotheses, no CER > 1.0

All 500 grayscale rows have non-empty `_hyp`, all `cer` values are ≤ 1.0.
Post-normalization lengths align with reference length (ratios 0.89–1.03),
confirming no engine is catastrophically failing a batch.

## 5. Fairness Criteria (met / unmet)

| Criterion | Status |
|---|---|
| Same preprocess applied uniformly across engines | ✅ single `preprocess_key` per run_meta |
| Same normalization applied to hyp and ref | ✅ `metrics.normalize()` called on both |
| Same dataset hash across engines | ✅ `run_meta.dataset_hash` matches |
| Same RNG seed | ✅ `seed=42` in run_meta (used by bootstrap & sample order) |
| No engine gets privileged markup | ⚠ fixed 2026-04-13 — Surya had HTML tag leakage, now stripped |
| No engine benefits from training-data overlap | N/A — zero-shot eval |
| Latency measured at same layer | ✅ `extract_text()` wall-clock, cold predictors excluded |

## 6. What This Audit Does NOT Cover

- **Ground-truth correctness**: assumed correct. No manual verification of
  XFUND annotator output.
- **Layout accuracy**: we evaluate page-level text only. Bounding-box IoU,
  table structure, reading-order as a first-class metric — all out of scope.
- **Confidence calibration**: engines return confidences; we don't evaluate
  them.
- **OOD generalization**: XFUND is in-domain for the types of forms AnonShield
  targets. ESTER-Pt + full BID sample will extend to free-text and ID docs once
  integrated (tasks #48 and ESTER download).
