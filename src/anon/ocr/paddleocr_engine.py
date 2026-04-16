"""PaddleOCR engine — very high accuracy, table/layout support, multilingual.

Supports two API generations transparently:
  • PP-OCRv5 (paddleocr >= 2.9.0, paddlepaddle >= 3.0.0) — new dict-based API,
    uses ocr_version="PP-OCRv5", predict(), and returns {"rec_texts": [...]}
  • PP-OCRv3/v4 (paddleocr >= 2.7.0) — old API with PaddleOCR(use_angle_cls=True)
    and .ocr() returning a nested list of [[bbox, [text, score]], ...]

Install (CPU):
    pip install paddlepaddle paddleocr
    (or: uv add --optional paddleocr paddleocr paddlepaddle)

Install (GPU / PP-OCRv5):
    pip install "paddlepaddle>=3.0.0" "paddleocr>=2.9.0"
    (CUDA 12 wheels: pip install paddlepaddle-gpu -i https://www.paddlepaddle.org.cn/packages/stable/cu126/)

Note: PP-OCRv5 requires paddleocr >= 2.9.0 and paddlepaddle >= 3.0.0.
      Older installations will automatically fall back to the v3/v4 API.
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)

# Map ISO 639-1 → PaddleOCR lang codes.
# PP-OCRv5 accepts per-language codes directly (tested 2026-04 with paddleocr 3.4).
_LANG_MAP_V5: dict[str, str] = {
    "pt": "pt",
    "es": "es",
    "fr": "fr",
    "de": "german",
    "en": "en",
}
_LANG_MAP_LEGACY: dict[str, str] = {
    "pt": "pt",
    "es": "es",
    "fr": "fr",
    "de": "german",
    "en": "en",
}


def _paddle_api_version() -> int:
    """Return 5 if paddleocr >= 2.9.0 (PP-OCRv5 API), else 3 (legacy API)."""
    try:
        import importlib.metadata as meta
        from packaging.version import Version
        ver = Version(meta.version("paddleocr"))
        return 5 if ver >= Version("2.9.0") else 3
    except Exception:
        return 3


def _cuda_available() -> bool:
    try:
        import torch
        return bool(torch.cuda.is_available())
    except ImportError:
        return False


class PaddleOCREngine(OCREngine):
    """PaddleOCR backend. Lazy-loads the OCR pipeline on first use.

    Automatically picks PP-OCRv5 when paddleocr >= 2.9.0 is installed;
    falls back to the PP-OCRv3/v4 API for older installations.
    `use_gpu=None` (default) auto-detects CUDA availability.
    """

    def __init__(self, lang: str = "pt", use_gpu: bool | None = None):
        self._lang = lang
        self._use_gpu = _cuda_available() if use_gpu is None else use_gpu
        self._ocr = None
        self._api_ver: int | None = None

    @property
    def name(self) -> str:
        return "paddleocr"

    def is_available(self) -> bool:
        try:
            from paddleocr import PaddleOCR  # noqa: F401
            import paddle  # noqa: F401
        except ImportError:
            return False
        return True

    def _get_ocr(self):
        if self._ocr is None:
            self._api_ver = _paddle_api_version()
            from paddleocr import PaddleOCR
            if self._api_ver >= 5:
                lang = _LANG_MAP_V5.get(self._lang, "latin")
                device = "gpu" if self._use_gpu else "cpu"
                logger.info("PaddleOCR: using PP-OCRv5 API (lang=%s, device=%s)", lang, device)
                self._ocr = PaddleOCR(
                    ocr_version="PP-OCRv5",
                    lang=lang,
                    device=device,
                    use_textline_orientation=True,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                )
            else:
                lang = _LANG_MAP_LEGACY.get(self._lang, "en")
                logger.info("PaddleOCR: using legacy API (lang=%s, use_gpu=%s)", lang, self._use_gpu)
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=lang,
                    use_gpu=self._use_gpu,
                    show_log=False,
                )
        return self._ocr

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import numpy as np
            from PIL import Image

            with Image.open(io.BytesIO(image_bytes)) as img:
                arr = np.array(img.convert("RGB"))

            ocr = self._get_ocr()

            if self._api_ver and self._api_ver >= 5:
                pages = ocr.predict(arr)
                lines = []
                for page in (pages or []):
                    if isinstance(page, dict):
                        lines.extend(page.get("rec_texts") or [])
                    elif isinstance(page, list):
                        # Fallback: some builds return old-style list even in v5
                        for item in page:
                            if item and len(item) >= 2 and item[1]:
                                lines.append(item[1][0] if isinstance(item[1], (list, tuple)) else item[1])
                return "\n".join(t for t in lines if t and t.strip())
            else:
                result = ocr.ocr(arr, cls=True)
                lines = []
                for page in (result or []):
                    for line in (page or []):
                        if line and len(line) >= 2 and line[1]:
                            lines.append(line[1][0])
                return "\n".join(lines)

        except Exception as exc:
            logger.error("PaddleOCR failed: %s", exc)
            return ""
