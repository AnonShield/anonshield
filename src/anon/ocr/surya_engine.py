"""Surya OCR engine — multilingual, transformer-based, strong on Latin scripts.

Targets surya-ocr >= 0.14 (new Predictor API based on Foundation model).
Language parameter is kept for API compatibility but Surya auto-detects script.

Install: uv sync --extra surya
"""
import io
import logging
import re

from .base import OCREngine

logger = logging.getLogger(__name__)

_MARKUP_TAG = re.compile(r"</?(?:b|i|u|sup|sub|br|math|em|strong)>", re.IGNORECASE)


class SuryaEngine(OCREngine):
    """Surya OCR backend. Predictors are lazy-loaded and cached per instance."""

    def __init__(self, lang: str = "pt"):
        self._lang = lang
        self._det = None
        self._rec = None

    @property
    def name(self) -> str:
        return "surya"

    def is_available(self) -> bool:
        try:
            import surya  # noqa: F401
            from surya.detection import DetectionPredictor  # noqa: F401
            from surya.recognition import RecognitionPredictor, FoundationPredictor  # noqa: F401
            _ = (DetectionPredictor, RecognitionPredictor, FoundationPredictor)
            return True
        except ImportError:
            return False

    def _load_predictors(self) -> None:
        if self._rec is not None:
            return
        from surya.detection import DetectionPredictor
        from surya.recognition import RecognitionPredictor, FoundationPredictor

        logger.info("Loading Surya foundation + detection + recognition predictors…")
        foundation = FoundationPredictor()
        self._det = DetectionPredictor()
        self._rec = RecognitionPredictor(foundation)
        logger.info("Surya predictors loaded.")

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            from PIL import Image

            self._load_predictors()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

            results = self._rec([image], det_predictor=self._det)
            if not results:
                return ""

            lines = [
                _MARKUP_TAG.sub("", ln.text) for ln in results[0].text_lines
                if getattr(ln, "text", "") and ln.text.strip()
            ]
            return "\n".join(lines)

        except Exception as exc:
            logger.error("Surya OCR failed: %s", exc)
            return ""
