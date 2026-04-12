# PDF Engine Evaluation: opendataloader-pdf vs PyMuPDF

**Evaluated:** 2026-04-11  
**Evaluator:** AnonShield feature-expansion sprint

---

## Summary

| Criterion | PyMuPDF (current) | opendataloader-pdf |
|-----------|------------------|--------------------|
| Fully local | Yes | Yes |
| Uses PyMuPDF internally | — | No (independent stack) |
| Actively maintained | Yes | Yes (weekly releases; v2.2.1, 2026-04-03) |
| Overall accuracy | ~73% | ~90% |
| Complex tables | Weak | Strong (XY-Cut++ algorithm) |
| Scanned PDFs / built-in OCR | No (separate Tesseract step) | Yes (80+ languages) |
| Multi-column layout | Partial | Yes |
| LaTeX / formulas | No | Yes |
| Bounding boxes | No | Yes (per element) |
| License | AGPL-3.0 | Apache-2.0 |
| Install size | ~5 MB | ~22.4 MB wheel |
| System requirement | None | **Java 11+ runtime** |

---

## Findings

### opendataloader-pdf

- Repository: `opendataloader-project/opendataloader-pdf`
- Python wrapper (3.10+) around a Java-based PDF parser; requires Java 11+ installed on the host.
- Provides a Python API — no CLI round-trip needed.
- Does **not** use PyMuPDF internally; it is an independent implementation.
- Benchmarks from the project documentation show 90% overall layout/extraction accuracy vs. PyMuPDF's 73%.
- Handles scanned PDFs with built-in multi-language OCR, making the separate `extract_text_from_image` fallback unnecessary for PDF inputs.
- Apache-2.0 license: compatible with all downstream uses.
- Optional `hybrid` extra for local AI-assisted layout detection (no cloud).

### Current PyMuPDF pipeline (`PdfFileProcessor`)

- `fitz.open()` → page text extraction → fallback to `extract_text_from_image` (Tesseract) for image-only pages.
- Works well for text-based PDFs; degrades on complex tables, multi-column, and scanned pages.
- Zero system dependencies beyond the Python wheel.

---

## Recommendation: Integrate as optional extra

opendataloader-pdf meets all integration criteria:
- 100% local
- Not a thin wrapper
- Actively maintained
- Measurable improvement (~23 pp accuracy gain)
- Permissive license

The **only friction** is the Java 11+ runtime dependency. This is manageable for server/containerized deployments (add `default-jre` to Docker image) but may be unexpected for local developer use.

**Proposed integration path:**

1. Add as optional dependency in `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   pdf-enhanced = ["opendataloader-pdf>=2.2.0"]
   ```

2. Create `src/anon/ocr/opendataloader_engine.py` following the `OCREngine` ABC:
   ```python
   class OpenDataLoaderEngine(OCREngine):
       def is_available(self) -> bool:
           try:
               import opendataloader_pdf  # noqa: F401
               return True
           except ImportError:
               return False
       def extract_text(self, image_bytes: bytes) -> str:
           # use opendataloader_pdf.extract() on a temp file
   ```

3. Update `PdfFileProcessor` to accept the engine via the existing `_do_ocr()` dispatch.

4. Document Java requirement in Docker images and installation guide.

**This integration is deferred to a follow-up task.** The evaluation is complete; no blocking issues found.

---

## Image Preprocessing Integration (implemented)

A preprocessing pipeline has been implemented in `src/anon/ocr/preprocessor.py` and wired into `FileProcessor._do_ocr()`. It runs **before** any OCR engine receives the image bytes, improving recognition quality on low-quality inputs.

### How it interacts with PyMuPDF

The current `PdfFileProcessor` extracts embedded images using `doc.extract_image(xref)`, which returns the image at its native embedded resolution. For scanned PDFs (where the page itself is a raster image), the embedded image DPI matches the scanner DPI — typically 150–300 DPI. Preprocessing steps like `upscale` bring sub-1000 px images up to the 300 DPI range that Tesseract is optimised for.

**Critical note for future work:** When rendering full pages via `page.get_pixmap()` (e.g. if a fallback to full-page rasterisation is added), always use:

```python
mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
pix = page.get_pixmap(matrix=mat)
```

The PyMuPDF default of 72 DPI will produce degraded OCR results regardless of which engine is used.

### Preprocessing steps available

| Step | OpenCV | Pillow fallback |
|------|--------|----------------|
| `grayscale` | ✓ | ✓ |
| `upscale` | ✓ | ✓ |
| `clahe` | ✓ | equalize (approximate) |
| `denoise` | ✓ | GaussianBlur (approximate) |
| `deskew` | ✓ | — |
| `binarize` | ✓ | — |
| `morph_open` | ✓ | — |
| `border` | ✓ | ✓ |

### Impact on opendataloader-pdf evaluation

If opendataloader-pdf is integrated, its built-in scanned-PDF OCR already handles multi-language extraction internally. The preprocessing pipeline would apply only to the `extract_image` fallback path, not to the opendataloader-pdf path. The two are orthogonal: preprocessing improves Tesseract/EasyOCR quality; opendataloader-pdf replaces the extraction architecture entirely.

---

## References

- [opendataloader-pdf GitHub](https://github.com/opendataloader-project/opendataloader-pdf)
- [opendataloader-pdf on PyPI](https://pypi.org/project/opendataloader-pdf/)
- Current implementation: `src/anon/processors.py` → `PdfFileProcessor`
