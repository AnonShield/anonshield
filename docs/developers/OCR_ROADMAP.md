# OCR Engine Roadmap

Tracks the state of all 16 OCR engines registered in `src/anon/ocr/factory.py`.

## Integrated (16)

### Classical / traditional (8)

| Engine | Backbone | Size | Benchmarked |
|---|---|---|---|
| `tesseract` | LSTM | 30 MB | ✅ grayscale |
| `easyocr` | CRAFT + CRNN | 120 MB | ✅ grayscale |
| `paddleocr` | PP-OCRv4 | 15 MB | ⏳ chain queued |
| `doctr` | DB + CRNN (PyTorch) | 95 MB | ✅ grayscale |
| `onnxtr` | DocTR in ONNX | 95 MB | ⏳ chain queued |
| `kerasocr` | CRAFT + CRNN (TF) | 130 MB | — (English-only weights) |
| `surya` | Transformer det+rec | 500 MB | ✅ grayscale |
| `rapidocr` | PaddleOCR → ONNX | 12 MB | ✅ grayscale |

### Vision-Language Models (8)

| Engine | HF ID | Params | Benchmarked | External score |
|---|---|---|---|---|
| `glm_ocr` | `zai-org/GLM-4.5V` | 9 B | ⏳ blocked: disk | OmniDocBench **94.62** (SOTA) |
| `paddle_vl` | `PaddlePaddle/PaddleOCR-VL` | 0.9 B | ⏳ next up (fits budget) | OmniDocBench 94.50 |
| `deepseek_ocr` | `deepseek-ai/DeepSeek-OCR` | 3 B | ⏳ blocked: disk | OmniDocBench 91.09 |
| `monkey_ocr` | `echo840/MonkeyOCR-pro-1.2B` | 1.2 B | ⏳ tight-fit | OmniDocBench 86.96 |
| `lighton_ocr` | `lightonai/LightOnOCR-1B-32k-1025` | 1 B | ⏳ tight-fit | — |
| `chandra_ocr` | `datalab-to/chandra` | 9 B | ⏳ blocked: disk | olmOCR-Bench 83.1 |
| `dots_ocr` | `rednote-hilab/dots.ocr` | 3 B | ⏳ blocked: disk | — |
| `qwen_vl` | `Qwen/Qwen2.5-VL-7B-Instruct` | 7 B | ⏳ blocked: disk | — |

## Benchmark Run Matrix

9 preprocess × 16 engines × 100 XFUND-PT docs = **14 400 evaluations**

Preprocess steps (single-step only, no combinations — see
`benchmark/ocr/METHODOLOGY.md` §10):
`baseline`, `grayscale`, `binarize`, `deskew`, `clahe`, `denoise`, `upscale`,
`morph_open`, `border`.

Each step writes to `benchmark/ocr/results/<step>/` with `run_state.json` that
resumes by `(engine, doc_id)`.

## Current Results — Grayscale Preprocess, XFUND-PT (N=100)

Mean CER with 95% bootstrap CI (B=10 000, seed=42):

| Engine | CER | 95% CI | WER | Field-F1 | ANLS | Latency |
|---|---|---|---|---|---|---|
| **doctr** | **0.299** | 0.266–0.332 | 0.474 | 0.632 | 0.625 | **0.34 s** |
| easyocr | 0.327 | 0.297–0.357 | 0.531 | 0.570 | 0.564 | 2.51 s |
| surya | 0.334 | 0.300–0.369 | **0.390** | **0.814** | **0.806** | 5.07 s |
| tesseract | 0.351 | 0.315–0.388 | 0.515 | 0.583 | 0.577 | 1.03 s |
| rapidocr | 0.376 | 0.349–0.403 | 0.782 | 0.522 | 0.517 | 3.64 s |

Headline: **DocTR wins CER + latency**; **Surya wins F1/ANLS** — Surya is the
pick for structured field extraction on forms; DocTR for cheapest accurate
transcription. Difference at the CER level is within CI for doctr vs easyocr;
Wilcoxon signed-rank + Holm correction pending once remaining preprocess
configs finish.

## Disk Budget — as of 2026-04-13

Free on `/`: **7.4 GB** (from 96 GB total).

| Item | Model size | Fits current budget? |
|---|---|---|
| PaddleOCR-VL 0.9 B | ~2 GB | ✅ |
| MonkeyOCR 1.2 B | ~2.4 GB | ✅ |
| LightOn-OCR 1 B | ~2 GB | ✅ |
| DotsOCR 3 B | ~6 GB | 🟡 tight |
| DeepSeek-OCR 3 B | ~10 GB | ❌ |
| Qwen2.5-VL 7 B | ~15 GB | ❌ |
| GLM-OCR / Chandra 9 B | ~18 GB each | ❌ |

**Plan:**
1. Finish classical preprocess chain (running — binarize now).
2. Download + benchmark `paddle_vl` on all 9 preprocess configs (~18 GB run
   output + 2 GB model).
3. Rotate `monkey_ocr`, `lighton_ocr`, `dots_ocr` — delete prior model cache
   between runs to stay within budget.
4. Blocked engines (`glm_ocr`, `deepseek_ocr`, `chandra_ocr`, `qwen_vl`) need
   either `TRANSFORMERS_CACHE` relocation to a larger volume or cleaning
   `~/.cache/huggingface` to free ≥ 20 GB.

## Integration checklist per engine

- [ ] Add `src/anon/ocr/<name>_engine.py` inheriting `OCREngine`
- [ ] Implement `name`, `is_available()`, `extract_text()`
- [ ] Register in `src/anon/ocr/factory.py`
- [ ] Add optional-dependency group to `pyproject.toml`
- [ ] Document in `docs/users/OCR_ENGINES.md`
- [ ] Benchmark on full preprocess matrix (`METHODOLOGY.md` §10)
