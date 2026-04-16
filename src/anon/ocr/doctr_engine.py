"""DocTR engine — very high accuracy for structured documents (forms, invoices, receipts).

Install: pip install python-doctr
         (or: uv sync --extra doctr)

Note: PyTorch is the default backend in python-doctr>=1.0; no extra needed.
      For GPU, ensure your torch install supports CUDA (the engine calls .cuda()
      on the model in _get_model() when torch.cuda.is_available()).
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)


def _cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


class DocTREngine(OCREngine):
    """DocTR backend. Lazy-loads the document analysis pipeline on first use.

    Moves the underlying PyTorch model to CUDA when available — `ocr_predictor()`
    alone does not auto-place tensors on GPU; an explicit `.cuda()` is required.
    """

    def __init__(self, det_arch: str = "fast_base", reco_arch: str = "crnn_vgg16_bn", pretrained: bool = True):
        self._det_arch = det_arch
        self._reco_arch = reco_arch
        self._pretrained = pretrained
        self._model = None

    @property
    def name(self) -> str:
        return "doctr"

    def is_available(self) -> bool:
        try:
            from doctr.models import ocr_predictor  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_model(self):
        if self._model is None:
            from doctr.models import ocr_predictor
            model = ocr_predictor(
                det_arch=self._det_arch,
                reco_arch=self._reco_arch,
                pretrained=self._pretrained,
            )
            if _cuda_available():
                try:
                    model = model.cuda()
                    logger.info("DocTR model moved to CUDA.")
                except Exception as exc:
                    logger.warning("Could not move DocTR to CUDA, falling back to CPU: %s", exc)
            self._model = model
        return self._model

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import numpy as np
            from PIL import Image
            from doctr.io import DocumentFile
            doc = DocumentFile.from_images([image_bytes])
            result = self._get_model()(doc)
            lines = []
            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        lines.append(" ".join(w.value for w in line.words))
            return "\n".join(lines)
        except Exception as e:
            logger.error("DocTR OCR failed: %s", e)
            return ""
