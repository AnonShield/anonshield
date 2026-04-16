"""RapidOCR engine — PaddleOCR models in ONNX format, no heavy Paddle dependency.

RapidOCR converts the PaddleOCR family of models to ONNX and runs them via
onnxruntime, achieving very high throughput with low memory overhead and without
requiring CUDA or the full PaddlePaddle framework.

Trade-offs vs PaddleOCR:
  + No CUDA / PaddlePaddle install required — pure ONNX runtime.
  + Cross-platform (Linux, macOS, Windows, ARM).
  + Lower memory footprint (~200 MB vs ~1 GB for Paddle + models).
  – Cannot use PP-OCRv5 server models directly (ONNX export lag).
  – No built-in table/structure module (use PaddleOCR for that).

Install (CPU, recommended):
    pip install rapidocr-onnxruntime
    (or: uv add --optional rapidocr rapidocr-onnxruntime)

Install (OpenVINO, Intel hardware):
    pip install rapidocr-openvino

Language support mirrors PaddleOCR's Latin pack — covers Portuguese, Spanish,
French, German, English, and 80+ other scripts out of the box.
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)


class RapidOCREngine(OCREngine):
    """RapidOCR (ONNX) backend. Lazy-loads on first use."""

    def __init__(self):
        self._engine = None

    @property
    def name(self) -> str:
        return "rapidocr"

    def is_available(self) -> bool:
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_engine(self):
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR
            logger.info("Loading RapidOCR (ONNX) engine…")
            self._engine = RapidOCR()
            logger.info("RapidOCR ready.")
        return self._engine

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import numpy as np
            from PIL import Image

            with Image.open(io.BytesIO(image_bytes)) as img:
                arr = np.array(img.convert("RGB"))

            result, _ = self._get_engine()(arr)

            if not result:
                return ""

            # result: list of (bbox_points, text, confidence)
            lines = [item[1] for item in result if item and len(item) >= 2 and item[1]]
            return "\n".join(lines)

        except Exception as exc:
            logger.error("RapidOCR failed: %s", exc)
            return ""
