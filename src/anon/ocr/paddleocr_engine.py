"""PaddleOCR engine — very high accuracy, table/layout support, multilingual.

Install: pip install paddlepaddle paddleocr
         (or: uv add --optional paddleocr paddleocr paddlepaddle)

Note: GPU support requires paddlepaddle-gpu; defaults to CPU.
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)


class PaddleOCREngine(OCREngine):
    """PaddleOCR backend. Lazy-loads the OCR pipeline on first use."""

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        self._lang = lang
        self._use_gpu = use_gpu
        self._ocr = None

    @property
    def name(self) -> str:
        return "paddleocr"

    def is_available(self) -> bool:
        try:
            from paddleocr import PaddleOCR  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_ocr(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang=self._lang, use_gpu=self._use_gpu, show_log=False)
        return self._ocr

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import numpy as np
            from PIL import Image
            with Image.open(io.BytesIO(image_bytes)) as img:
                arr = np.array(img.convert("RGB"))
            result = self._get_ocr().ocr(arr, cls=True)
            lines = []
            for page in (result or []):
                for line in (page or []):
                    if line and len(line) >= 2 and line[1]:
                        lines.append(line[1][0])
            return "\n".join(lines)
        except Exception as e:
            logger.error("PaddleOCR failed: %s", e)
            return ""
