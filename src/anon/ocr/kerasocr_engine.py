"""Keras-OCR engine — best for custom training, CAPTCHAs, specific fonts.

Install: pip install keras-ocr
         (or: uv add --optional kerasocr keras-ocr)

Limitations: English only by default; ignores punctuation and case;
             not ideal for general-purpose OCR without fine-tuning.
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)


class KerasOCREngine(OCREngine):
    """Keras-OCR backend. Lazy-loads the pipeline on first use."""

    def __init__(self):
        self._pipeline = None

    @property
    def name(self) -> str:
        return "kerasocr"

    def is_available(self) -> bool:
        try:
            import keras_ocr  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_pipeline(self):
        if self._pipeline is None:
            import keras_ocr
            self._pipeline = keras_ocr.pipeline.Pipeline()
        return self._pipeline

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import numpy as np
            from PIL import Image
            with Image.open(io.BytesIO(image_bytes)) as img:
                arr = np.array(img.convert("RGB"))
            predictions = self._get_pipeline().recognize([arr])
            # predictions[0] is a list of (word, box) tuples sorted by reading order
            words = [word for word, _ in predictions[0]] if predictions else []
            return " ".join(words)
        except Exception as e:
            logger.error("Keras-OCR failed: %s", e)
            return ""
