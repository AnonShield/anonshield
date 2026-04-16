"""OCR engine abstraction layer for AnonShield.

Available engines: tesseract, easyocr, paddleocr, doctr, kerasocr

Usage:
    from anon.ocr.factory import get_ocr_engine
    engine = get_ocr_engine("easyocr")
    text = engine.extract_text(image_bytes)
"""
from . import _compat_shims  # noqa: F401  (must run before any engine imports)
from .factory import get_ocr_engine

__all__ = ["get_ocr_engine"]
