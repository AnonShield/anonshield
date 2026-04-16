"""vLLM HTTP client — runs against a local vLLM OpenAI-compat server.

Zero-cloud: the server must live on localhost (or internal docker network).
Any vLLM-supported VLM (GLM-4V, Qwen2.5-VL, etc.) can be wrapped by setting
the matching model_id + base_url at engine construction.

Env:
    ANON_VLLM_URL        base URL (default http://vllm-serve:8000)
    ANON_VLLM_MODEL      model id the server was launched with
"""
from __future__ import annotations

import base64
import logging
import os
from typing import ClassVar

from .base import OCREngine

logger = logging.getLogger(__name__)

_OCR_PROMPT = "OCR the document. Return only the text content, preserving layout."


class VLLMOCREngine(OCREngine):
    _DEFAULT_TIMEOUT: ClassVar[float] = 120.0

    def __init__(
        self,
        engine_name: str = "vllm_glm",
        base_url: str | None = None,
        model_id: str | None = None,
        max_tokens: int = 2048,
        timeout: float | None = None,
    ):
        self._engine_name = engine_name
        self._base_url = (base_url or os.getenv("ANON_VLLM_URL", "http://vllm-serve:8000")).rstrip("/")
        self._model_id = model_id or os.getenv("ANON_VLLM_MODEL", "zai-org/GLM-4.1V-9B-Thinking-FP8")
        self._max_tokens = max_tokens
        self._timeout = timeout or self._DEFAULT_TIMEOUT

    @property
    def name(self) -> str:
        return self._engine_name

    def is_available(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self._base_url}/v1/models", timeout=5.0)
            r.raise_for_status()
            return any(m.get("id") == self._model_id for m in r.json().get("data", []))
        except Exception as exc:
            logger.debug("vLLM server %s unreachable: %s", self._base_url, exc)
            return False

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import httpx
            b64 = base64.b64encode(image_bytes).decode("ascii")
            payload = {
                "model": self._model_id,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                        {"type": "text", "text": _OCR_PROMPT},
                    ],
                }],
                "max_tokens": self._max_tokens,
                "temperature": 0.0,
            }
            r = httpx.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=self._timeout,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or ""
        except Exception as exc:
            logger.error("vLLM %s (%s) failed: %s", self._engine_name, self._model_id, exc)
            return ""
