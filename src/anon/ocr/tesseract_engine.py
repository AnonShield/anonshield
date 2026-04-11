"""Tesseract OCR engine (default, via pytesseract)."""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)


class TesseractEngine(OCREngine):
    """Wraps pytesseract / Tesseract OCR (system binary required)."""

    @property
    def name(self) -> str:
        return "tesseract"

    def is_available(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import pytesseract
            from PIL import Image
            with Image.open(io.BytesIO(image_bytes)) as img:
                return pytesseract.image_to_string(img)
        except Exception as e:
            logger.error("Tesseract OCR failed: %s", e)
            return ""
