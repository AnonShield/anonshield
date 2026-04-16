"""HTTP client that speaks to a sidecar container hosting an OCR engine.

Used when an engine's dependencies conflict with the main image (paddle_vl /
monkey_ocr pin transformers 4.51; kerasocr needs TensorFlow). The sidecar
exposes POST /ocr/{engine} with a multipart image and returns plain text.
"""
from __future__ import annotations

import logging
from typing import ClassVar

from .base import OCREngine

logger = logging.getLogger(__name__)


class SidecarOCREngine(OCREngine):
    _DEFAULT_TIMEOUT: ClassVar[float] = 300.0

    def __init__(self, engine_name: str, base_url: str, timeout: float | None = None):
        self._engine_name = engine_name
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout or self._DEFAULT_TIMEOUT

    @property
    def name(self) -> str:
        return self._engine_name

    def is_available(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self._base_url}/engines", timeout=5.0)
            r.raise_for_status()
            return bool(r.json().get(self._engine_name))
        except Exception as exc:
            logger.debug("Sidecar %s unreachable: %s", self._base_url, exc)
            return False

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import httpx
            r = httpx.post(
                f"{self._base_url}/ocr/{self._engine_name}",
                files={"file": ("page.png", image_bytes, "image/png")},
                timeout=self._timeout,
            )
            r.raise_for_status()
            return r.text
        except Exception as exc:
            logger.error("Sidecar %s/%s failed: %s", self._base_url, self._engine_name, exc)
            return ""
