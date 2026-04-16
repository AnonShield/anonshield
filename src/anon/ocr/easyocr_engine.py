"""EasyOCR engine — strong on 'in the wild' text, receipts, labels.

Install: pip install easyocr
         (or: uv add --optional easyocr easyocr)
"""
import logging
import numpy as np

from .base import OCREngine

logger = logging.getLogger(__name__)


def _cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


class EasyOCREngine(OCREngine):
    """EasyOCR backend. Lazy-loads the Reader on first use.

    `gpu=None` (default) auto-detects CUDA availability. Pass True/False to force.
    """

    def __init__(self, langs: list[str] | None = None, gpu: bool | None = None):
        self._langs = langs or ["en"]
        self._gpu = _cuda_available() if gpu is None else gpu
        self._reader = None

    @property
    def name(self) -> str:
        return "easyocr"

    def is_available(self) -> bool:
        try:
            import easyocr  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_reader(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self._langs, gpu=self._gpu, verbose=False)
        return self._reader

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import io
            from PIL import Image
            with Image.open(io.BytesIO(image_bytes)) as img:
                arr = np.array(img)
            results = self._get_reader().readtext(arr, detail=0, paragraph=True)
            return "\n".join(results)
        except Exception as e:
            logger.error("EasyOCR failed: %s", e)
            return ""
