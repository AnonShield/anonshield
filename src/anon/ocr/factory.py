"""OCR engine factory: resolves engine name to a concrete OCREngine instance.

AnonShield ships Tesseract as its only OCR backend.
"""
import logging
from typing import Callable

from .base import OCREngine
from .tesseract_engine import TesseractEngine

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Callable[..., OCREngine]] = {
    "tesseract": TesseractEngine,
}

AVAILABLE_ENGINES = ["tesseract"]

_SIDECAR_ROUTES: dict[str, str] = {}


def get_ocr_engine(name: str = "tesseract", **kwargs) -> OCREngine:
    """Instantiate and return the requested OCR engine."""
    key = name.lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"Unknown OCR engine: '{name}'. "
            f"Available: {AVAILABLE_ENGINES}."
        )
    engine = _REGISTRY[key](**kwargs)
    logger.info("OCR engine loaded: %s (local)", name)
    return engine
