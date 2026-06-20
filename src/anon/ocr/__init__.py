"""OCR engine abstraction layer for AnonShield.

Available engines: tesseract

Usage:
    from anon.ocr.factory import get_ocr_engine
    engine = get_ocr_engine("tesseract")
    text = engine.extract_text(image_bytes)
"""
from .factory import get_ocr_engine

__all__ = ["get_ocr_engine"]
