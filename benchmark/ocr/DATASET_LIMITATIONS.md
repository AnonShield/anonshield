# XFund-PT Ground-Truth Incompletude — Finding from Baseline (2026-04-13)

## Summary

Manual inspection of GLM-OCR outputs against the XFund-PT reference revealed that **the dataset's ground-truth is systematically incomplete**. Many handwritten form fields are correctly read by the VLM but absent from the GT annotation, causing the VLM to be penalized (higher CER / WER) for *correct* transcriptions.

This inverts the apparent ranking between classical OCR and VLMs in the baseline (`results/none/`).

## Evidence

Inspection of 5 GLM-OCR documents spanning the CER spectrum:

| Doc | CER (vs GT) | Manual precision (vs image) | Root cause of gap |
|---|---|---|---|
| `xfund_train_pt_train_29` | 0.029 | ~97% | GLM correct; small diacritic / punctuation differences |
| `xfund_train_pt_train_36` | 0.196 | ~90%+ | GLM read fields (e.g. `inscrição 34270984`) not present in GT |
| `xfund_train_pt_train_90` | 0.334 | likely ~85%+ | GT missing filled fields (NOME, CPF, endereço Quadro 1) |
| `xfund_train_pt_train_75` | 0.506 | **~95%+** | **GT lacks most handwritten fields** which GLM transcribed correctly |
| `xfund_train_pt_train_7`  | 1.000 | 0% | Real failure — empty output (VLM timeout) |

### Worked example — `pt_train_75`

Form (visible in image): Pedro C Santos, 12/4/2000, São Paulo, solteiro, bacharel, CEP 70.719-900, tel (11) 6083-9439, celular (24) 2501-2316, CI 4768899000, órgão SE, CPF 355.761.516-23, CNH 5344756, categoria N.78/N.89, Carteira de Trabalho 534200 série arte, etc.

GLM-OCR output: all of the above, transcribed correctly.
XFund GT: captures only a fraction — omits most of the filled-in handwritten values.
Measured CER: 0.506 — a false negative against the model.

## Implication for the baseline

1. **CER / WER against XFund-PT penalize VLMs disproportionately**. They read fields the annotation ignores; each unmatched character counts as an insertion error.
2. **Classical engines (DocTR, Surya) may rank higher in CER than their real precision warrants** — if they too skip handwritten fields, their output is "closer" to the incomplete GT.
3. **Field-F1 is partially insulated** only when the GT's field key-set is complete. When the GT simply omits the field, the VLM gets 0 for correct extractions of unlisted fields.
4. **All aggregate rankings in `results/none/ocr_benchmark_summary.csv` must be treated as lower-bound estimates for VLMs** until a complete GT is established.

## Actions

- [ ] Re-validate the strongest VLMs (GLM, Qwen-VL, PaddleOCR-VL, etc.) against manually re-annotated ground-truth on a ≥20-doc subset of XFund-PT.
- [ ] Consider replacing or supplementing XFund-PT with a dataset whose GT is known to cover all visible fields (BID cheque-likes, manually annotated set).
- [ ] Add a "GT-completeness" disclaimer to `REPORT.md` summary tables.
- [ ] When reporting the ranking in the paper, present CER on full-text macro-docs (where GT completeness is more reliable) separately from field-level metrics.

## Why this matters for the real use case

For the downstream use case (high-volume document processing where all filled fields must be captured), the **current ranking actively misleads**: it favors engines that skip handwritten content. A VLM that reads everything correctly but is penalized by incomplete GT may be the safer production choice than a classical engine with a deceptively lower CER.
