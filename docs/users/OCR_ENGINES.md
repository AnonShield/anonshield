# OCR Engines — Comparison and Installation

AnonShield supports five OCR engines for extracting text from images and scanned PDFs. Select the engine with `--ocr-engine <name>`.

---

## Comparison Table

| Engine | Overall Accuracy | Speed (CPU) | Languages | Layout / Tables | Install Size | License | Notes |
|--------|-----------------|-------------|-----------|-----------------|--------------|---------|-------|
| `tesseract` | Good | Fast | 100+ | Basic | ~30 MB | Apache-2.0 | **Default.** System package; widely available. |
| `easyocr` | Very good | Medium | 80+ | Good | ~400 MB (models) | Apache-2.0 | Best on noisy / rotated images. Pure Python. |
| `paddleocr` | Excellent | Fast | 80+ | Excellent | ~350 MB (models) | Apache-2.0 | Top accuracy for CJK. Parallel multi-page. |
| `doctr` | Excellent | Medium | 60+ | Excellent | ~200 MB (models) | Apache-2.0 | Best layout preservation; outputs bounding boxes. |
| `kerasocr` | Good | Slow | English only | Basic | ~250 MB (models) | MIT | Keras/TF backend; English only. |

---

## Engine Details

### tesseract (default)

Tesseract is Google's open-source OCR engine, available as a system package on all major Linux distributions and in Docker images.

**Strengths:** Fast, zero Python dependencies beyond `pytesseract` (already bundled), supports 100+ language packs.

**Weaknesses:** Struggles with complex tables and multi-column layouts; requires clean, well-aligned images for best results.

**Installation:**
```bash
# Ubuntu / Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract

# Additional language packs (e.g., Portuguese)
sudo apt-get install tesseract-ocr-por
```

---

### easyocr

EasyOCR is a ready-to-use OCR library with deep learning models for 80+ languages.

**Strengths:** Handles noisy, rotated, and low-contrast images well; good word-level confidence scores; no system dependencies.

**Weaknesses:** Slower than Tesseract on CPU; large model download on first use.

**Installation:**
```bash
pip install easyocr
# Or via extras:
pip install "anonshield[easyocr]"
```

---

### paddleocr

PaddleOCR from Baidu Research is among the highest-accuracy open-source OCR engines, especially for CJK (Chinese, Japanese, Korean) scripts.

**Strengths:** State-of-the-art accuracy on multi-language documents; fast batch processing; excellent table and form detection.

**Weaknesses:** PaddlePaddle dependency can conflict with PyTorch; larger initial setup.

**Installation:**
```bash
pip install paddleocr paddlepaddle
# GPU (CUDA 11):
pip install paddlepaddle-gpu
# Or via extras:
pip install "anonshield[paddleocr]"
```

---

### doctr

DocTR (Document Text Recognition) is a PyTorch/TensorFlow-based engine from Mindee, optimized for document understanding.

**Strengths:** Best layout preservation; outputs structured document objects with bounding boxes; excellent on forms and multi-column PDFs.

**Weaknesses:** Requires `torch` (already present if GPU is used); slower than Tesseract on CPU.

**Installation:**
```bash
pip install "python-doctr[torch]"
# Or via extras:
pip install "anonshield[doctr]"
```

---

### kerasocr

Keras-OCR is a Keras/TensorFlow pipeline combining CRAFT (text detection) and CRNN (recognition).

**Strengths:** Good general-purpose results on printed text; pure Python.

**Weaknesses:** English-only; slowest of all five engines; requires TensorFlow which is a large dependency.

**Installation:**
```bash
pip install keras-ocr
```

---

## Choosing an Engine

| Use case | Recommended engine |
|----------|--------------------|
| General-purpose (text PDFs, mixed docs) | `tesseract` (default) |
| Noisy scans, skewed images | `easyocr` |
| Multi-language or CJK documents | `paddleocr` |
| Complex layouts, tables, forms | `doctr` |
| English printed text, simple images | `tesseract` or `easyocr` |

---

## Usage

```bash
# Default Tesseract
./docker/run.sh ./scanned_report.pdf

# EasyOCR for noisy scans
./docker/run.sh ./receipt.jpg --ocr-engine easyocr

# PaddleOCR for Chinese document
./docker/run.sh ./chinese_invoice.pdf --ocr-engine paddleocr --lang zh

# DocTR for a complex multi-column form
./docker/run.sh ./application_form.pdf --ocr-engine doctr

# In a config file (examples/profiles/banking_pt.yaml)
# ocr_engine: tesseract
```

---

## Docker

The CPU Docker image (`production` stage) ships with Tesseract pre-installed. For other engines, install the corresponding Python package in a custom image:

```dockerfile
FROM anonshield:latest
RUN pip install easyocr
```

The GPU image includes CUDA-compatible versions of PaddlePaddle and PyTorch, making `paddleocr` and `doctr` ready to use after `pip install`.
