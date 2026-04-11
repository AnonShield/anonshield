"""DocTR engine — very high accuracy for structured documents (forms, invoices, receipts).

Install: pip install python-doctr[torch]
         (or: uv add --optional doctr python-doctr)

Note: TensorFlow backend also supported (python-doctr[tf]).
      PyTorch backend is recommended for consistency with the rest of the stack.
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)


class DocTREngine(OCREngine):
    """DocTR backend. Lazy-loads the document analysis pipeline on first use."""

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
            self._model = ocr_predictor(
                det_arch=self._det_arch,
                reco_arch=self._reco_arch,
                pretrained=self._pretrained,
            )
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
