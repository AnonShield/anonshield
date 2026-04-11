"""OCR engine factory — resolves engine name to a concrete OCREngine instance."""
import logging

from .base import OCREngine
from .tesseract_engine import TesseractEngine
from .easyocr_engine import EasyOCREngine
from .paddleocr_engine import PaddleOCREngine
from .doctr_engine import DocTREngine
from .kerasocr_engine import KerasOCREngine

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[OCREngine]] = {
    "tesseract": TesseractEngine,
    "easyocr": EasyOCREngine,
    "paddleocr": PaddleOCREngine,
    "doctr": DocTREngine,
    "kerasocr": KerasOCREngine,
}

AVAILABLE_ENGINES = list(_REGISTRY)


def get_ocr_engine(name: str = "tesseract", **kwargs) -> OCREngine:
    """Instantiate and return the requested OCR engine.

    Args:
        name: Engine identifier — one of: tesseract, easyocr, paddleocr, doctr, kerasocr.
        **kwargs: Forwarded to the engine constructor (e.g. langs=["pt"] for EasyOCR).

    Raises:
        ValueError: Unknown engine name.
        RuntimeError: Engine is not installed (import failed).
    """
    key = name.lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"Unknown OCR engine: '{name}'. "
            f"Available: {AVAILABLE_ENGINES}. "
            f"See docs/users/OCR_ENGINES.md for installation instructions."
        )
    engine = _REGISTRY[key](**kwargs)
    if not engine.is_available():
        raise RuntimeError(
            f"OCR engine '{name}' is not installed. "
            f"See docs/users/OCR_ENGINES.md for installation instructions."
        )
    logger.info("OCR engine loaded: %s", name)
    return engine
