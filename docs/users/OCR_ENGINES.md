# OCR Engines — Comparison and Installation

AnonShield supports **13 OCR engines** across three families — classical (Tesseract), deep-learning detectors+recognizers (EasyOCR, DocTR, OnnxTR, Surya, PaddleOCR, RapidOCR, Keras-OCR), and vision-language models (PaddleOCR-VL, DeepSeek-OCR-2, MonkeyOCR, GLM-OCR, LightOn-OCR). All engines run **100% locally** — no cloud calls, no data leaves your machine.

Select one with `--ocr-engine <name>` or set `ocr_engine:` in a config file.

---

## Quick comparison

Accuracy is reported as OmniDocBench overall score when available; otherwise CER on XFUND-PT. Install size excludes model weights.

| Engine | Type | GPU? | Accuracy | Speed | Model size | License | Best for |
|---|---|---|---|---|---|---|---|
| `tesseract` | Classical LSTM | ❌ | CER ~0.40 PT | Fast CPU | ~30 MB | Apache-2.0 | Default; clean scans |
| `easyocr` | CRAFT + CRNN | ✅ auto | CER ~0.28 PT | Medium GPU | ~94 MB | Apache-2.0 | Noisy / rotated images |
| `paddleocr` | PP-OCRv5 | ✅ explicit | CER ~0.15 PT | Fast GPU | ~500 MB | Apache-2.0 | Forms, checks, CJK |
| `doctr` | PyTorch VGG/CRNN | ✅ (after `.cuda()`) | CER ~0.18 PT | Medium | ~400 MB | Apache-2.0 | Structured docs + layout |
| `onnxtr` | DocTR in ONNX | ✅ CUDAExecutionProvider | ≈ DocTR | ~2× DocTR | ~200 MB | Apache-2.0 | Faster drop-in for DocTR |
| `kerasocr` | CRAFT + CRNN (TF) | ✅ auto | CER ~0.22 EN | Slow | ~250 MB | MIT | English prints (legacy) |
| `surya` | Transformer foundation | ✅ via `TORCH_DEVICE` | CER ~0.12 PT | Medium GPU | ~1 GB | GPL-3.0 | Multilingual, Latin scripts |
| `rapidocr` | PP-OCRv4 in ONNX | ❌ CPU ONNX | CER ~0.20 PT | Fastest CPU | ~200 MB | Apache-2.0 | CPU-only deployments |
| `paddle_vl` | VLM 0.9B | ✅ required | OmniDocBench 94.50 | Slow (gen) | ~2 GB | Apache-2.0 | SOTA all-rounder |
| `deepseek_ocr` | VLM 3B MoE | ✅ + flash-attn | OmniDocBench 91.09 | Slow (gen) | ~6 GB | MIT | Complex layouts, markdown |
| `monkey_ocr` | VLM 1.2B | ✅ required | OmniDocBench 86.96 | Slow (gen) | ~2.4 GB | Apache-2.0 | Compact VLM alternative |
| `glm_ocr` | VLM | ✅ required | — | Slow (gen) | — | — | Experimental |
| `lighton_ocr` | VLM | ✅ required | — | Slow (gen) | — | — | Experimental |

**Why three families?** Classical engines handle the fast path on clean inputs; deep-learning detectors+recognizers give a solid accuracy/speed tradeoff across ~80 languages; VLMs give SOTA accuracy on documents with complex layouts (receipts, invoices, multi-column forms) at the cost of GPU memory and generation latency.

---

## GPU configuration

| Engine | How GPU is enabled |
|---|---|
| `easyocr` | Auto — `torch.cuda.is_available()` detected in `easyocr_engine.py` |
| `doctr` | `.cuda()` moves model explicitly — `ocr_predictor()` alone does **not** auto-place |
| `onnxtr` | Passes `providers=["CUDAExecutionProvider", ...]` when `onnxruntime-gpu` installed |
| `surya` | Reads `TORCH_DEVICE` env var — benchmark script sets `TORCH_DEVICE=cuda` |
| `paddleocr` | `device="gpu"` passed explicitly in v5 API |
| `paddle_vl` / `deepseek_ocr` / `monkey_ocr` | `.to("cuda")` on load — GPU is mandatory |
| `tesseract` / `rapidocr` | **CPU-only by design** — no GPU code path |

Verify your setup:

```bash
uv run python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count(), torch.version.cuda)"
```

---

## Engine details

### tesseract (default)

Google's open-source LSTM OCR. Stable, ubiquitous, CPU-only.

**Strengths:** Zero Python deps beyond `pytesseract`; 100+ language packs; fast on clean inputs.
**Weaknesses:** Struggles with skew, noise, complex layouts. Worst CER on degraded Portuguese forms.

```bash
# Ubuntu / Debian
sudo apt-get install tesseract-ocr tesseract-ocr-por
# macOS
brew install tesseract tesseract-lang
```

### easyocr

CRAFT detector + CRNN recognizer, PyTorch. Auto-detects GPU.

```bash
pip install easyocr
# or: uv sync --extra easyocr
```

### paddleocr

PaddleOCR v5 (PP-OCRv5) — SOTA accuracy for forms, checks, IDs, multilingual.

```bash
pip install "paddleocr>=2.9.0" "paddlepaddle>=3.0.0"
# GPU (CUDA 12):
pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu126/
# or: uv sync --extra paddleocr
```

The engine auto-picks between v5 and legacy v3/v4 APIs.

### doctr

Mindee's DocTR with PyTorch. Best layout preservation; outputs structured documents with bounding boxes.

```bash
pip install "python-doctr>=1.0"
# or: uv sync --extra doctr
```

GPU is **not** enabled automatically — `DocTREngine._get_model()` calls `.cuda()` when CUDA is available (see `src/anon/ocr/doctr_engine.py`).

### onnxtr

ONNX-Runtime port of DocTR. Same det/reco pipeline, ~2× faster, lower memory.

```bash
pip install "onnxtr[gpu]"      # CUDA 12
pip install "onnxtr[cpu]"      # CPU only
# or: uv sync --extra onnxtr
```

Drop-in replacement — same architectures (`fast_base` det, `crnn_vgg16_bn` reco).

### kerasocr

Legacy Keras/TF pipeline. English-only. Kept for reproducibility of older benchmarks.

```bash
pip install keras-ocr
```

### surya

Multilingual transformer foundation model. Strong on Latin scripts.

```bash
pip install "surya-ocr>=0.14"
# or: uv sync --extra surya
```

Set `TORCH_DEVICE=cuda` in the environment to force GPU — Surya's Predictor reads this env var at init.

### rapidocr

PaddleOCR models in ONNX (no Paddle framework). **CPU-only** by design — ideal for lightweight deployments.

```bash
pip install rapidocr-onnxruntime
# or: uv sync --extra rapidocr
```

### paddle_vl (PaddleOCR-VL-1.5)

0.9B parameter VLM. **Best open-source all-rounder** per OmniDocBench 94.50.

```bash
pip install "transformers>=5.0.0" torch pillow
# or: uv sync --extra paddle-vl
```

Model auto-downloads from HuggingFace on first use (~2 GB).

### deepseek_ocr (DeepSeek-OCR-2)

3B MoE VLM with markdown grounding. Pins `transformers==4.46.3` — install in a separate env if you have other VLM engines.

```bash
pip install transformers==4.46.3 tokenizers==0.20.3 einops addict easydict
pip install flash-attn==2.7.3 --no-build-isolation
# or: uv sync --extra deepseek-ocr
```

Requires **~10 GB free disk** for model + flash-attn build artifacts.

### monkey_ocr (MonkeyOCR-pro-1.2B)

Compact VLM. No PyPI package — requires git clone:

```bash
git clone https://github.com/Yuliang-Liu/MonkeyOCR /opt/MonkeyOCR
pip install -r /opt/MonkeyOCR/requirements.txt
export MONKEY_OCR_ROOT=/opt/MonkeyOCR
```

### glm_ocr (GLM-OCR — SOTA on OmniDocBench)

Native `transformers` VLM — OmniDocBench 94.62 (highest open-source score as of Apr/2026).

```bash
pip install "transformers>=5.3.0" torch pillow
# or: uv sync --extra glm-ocr
```

Model: `zai-org/GLM-OCR`. Uses `GlmOcrForConditionalGeneration` (no `trust_remote_code`).

### lighton_ocr (LightOn OCR-2)

1B-param VLM outputting Markdown. Native transformers class.

```bash
pip install "transformers>=5.0.0" pypdfium2 torch pillow
# or: uv sync --extra lighton-ocr
```

Model: `lightonai/LightOnOCR-2-1B`.

### Planned (roadmap — not yet integrated)

| Engine | Model ID | Size | Rationale |
|---|---|---|---|
| `chandra_ocr` | datalab-to/chandra | ~9B | 83.1 on olmOCR-Bench, permissive license, fits 16 GB VRAM |
| `dots_ocr` | rednote-hilab/dots.ocr | ~3B | Released Jul/2025, compact with strong layout-aware decoding |
| `qwen_vl` | Qwen/Qwen2.5-VL-7B-Instruct | ~7B | Multilingual (incl. PT-BR), native Transformers support |

These are tracked as pending tasks (#44, #45, #46). See `docs/developers/OCR_ROADMAP.md` for integration status.

---

## Choosing an engine

| Use case | Recommended |
|---|---|
| Anonymization pipeline default — any document | `tesseract` (safe baseline) |
| Noisy / rotated scans, receipts | `easyocr` |
| Brazilian forms, checks, RG/CPF | `paddleocr` (v5 latin) or `paddle_vl` |
| Complex multi-column forms (academic papers, contracts) | `doctr` or `onnxtr` |
| Fastest CPU-only deployment | `rapidocr` |
| Highest accuracy, no disk constraint, GPU available | `paddle_vl` > `deepseek_ocr` > `surya` |
| Reproducing legacy 2022-era benchmarks | `kerasocr` |

---

## Usage

```bash
# Default Tesseract
anon scanned_report.pdf

# EasyOCR for a noisy receipt
anon receipt.jpg --ocr-engine easyocr

# PaddleOCR v5 for a Brazilian form
anon form_pt.pdf --ocr-engine paddleocr --lang pt

# PaddleOCR-VL for maximum accuracy
anon invoice.png --ocr-engine paddle_vl

# In a config file
cat > profile.yaml <<EOF
ocr_engine: paddleocr
lang: pt
EOF
anon docs/ --config profile.yaml
```

---

## Benchmarking

The project ships a reproducible OCR benchmark against XFUND-PT (Portuguese subset of the XFUND forms dataset):

```bash
# All 5 baseline engines, 100 docs, 8 preprocessing configs
bash benchmark/ocr/run_ablation.sh 100 tesseract,easyocr,doctr,surya,rapidocr

# Include VLM engines (requires >10 GB free disk)
bash benchmark/ocr/run_ablation.sh 100 tesseract,easyocr,doctr,surya,rapidocr,paddle_vl

# Results written to benchmark/ocr/results/<preprocess>/
# Consolidated CSV: benchmark/ocr/results/ablation_consolidated.csv
# Metrics: CER, WER, CER without diacritics, latency, field-level F1, ANLS.
```

---

## Docker

The CPU Docker image ships Tesseract. For other engines, install the matching extra in a custom stage:

```dockerfile
FROM anonshield:latest
RUN pip install "onnxtr[gpu]"
```

The GPU image pins CUDA 12.8 PyTorch wheels; `easyocr`, `doctr`, `onnxtr`, `surya`, `paddle_vl` work out of the box after their `pip install`.
