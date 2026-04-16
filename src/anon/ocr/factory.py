"""OCR engine factory — resolves engine name to a concrete OCREngine instance.

Some engines live in sidecar containers (paddle_vl/monkey_ocr need transformers
4.51; kerasocr needs TensorFlow). When the local import fails and a sidecar
URL is known for the engine, the factory returns a SidecarOCREngine that
proxies extract_text() over HTTP instead of raising.

Sidecar routing is controlled by env vars so dev/prod can override independently:
  ANON_SIDECAR_LEGACY_VLM  (default: http://legacy_vlm:8001) — paddle_vl, monkey_ocr
  ANON_SIDECAR_KERASOCR    (default: http://kerasocr:8002)   — kerasocr
Running outside compose? Export e.g. http://localhost:8001.
"""
import logging
import os
from typing import Callable

from .base import OCREngine
from .tesseract_engine import TesseractEngine
from .easyocr_engine import EasyOCREngine
from .paddleocr_engine import PaddleOCREngine
from .doctr_engine import DocTREngine
from .onnxtr_engine import OnnxTREngine
from .kerasocr_engine import KerasOCREngine
from .surya_engine import SuryaEngine
from .rapidocr_engine import RapidOCREngine
from .glm_ocr_engine import GLMOCREngine
from .lighton_ocr_engine import LightOnOCREngine
from .paddle_vl_engine import PaddleVLEngine
from .deepseek_ocr_engine import DeepSeekOCREngine
from .monkey_ocr_engine import MonkeyOCREngine
from .chandra_ocr_engine import ChandraOCREngine
from .dots_ocr_engine import DotsOCREngine
from .qwen_vl_engine import QwenVLEngine
from .sidecar_engine import SidecarOCREngine
from .vllm_engine import VLLMOCREngine


def _vllm_factory(engine_name: str, model_id: str, env_url: str):
    """Build a VLLMOCREngine bound to a specific local server + model."""
    def _build(**kwargs):
        return VLLMOCREngine(
            engine_name=engine_name,
            base_url=os.getenv(env_url, "http://vllm-serve:8000"),
            model_id=model_id,
            **kwargs,
        )
    return _build

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, Callable[..., OCREngine]] = {
    "tesseract":    TesseractEngine,
    "easyocr":      EasyOCREngine,
    "paddleocr":    PaddleOCREngine,
    "doctr":        DocTREngine,
    "onnxtr":       OnnxTREngine,
    "kerasocr":     KerasOCREngine,
    "surya":        SuryaEngine,
    "rapidocr":     RapidOCREngine,
    "glm_ocr":      GLMOCREngine,
    "lighton_ocr":  LightOnOCREngine,
    "paddle_vl":    PaddleVLEngine,
    "deepseek_ocr": DeepSeekOCREngine,
    "monkey_ocr":   MonkeyOCREngine,
    "chandra_ocr":  ChandraOCREngine,
    "dots_ocr":     DotsOCREngine,
    "qwen_vl":      QwenVLEngine,
    # vLLM-accelerated variants (local, zero-cloud). Each hits a dedicated
    # vllm-serve container launched with the matching MODEL_ID + MTP enabled.
    "glm_vllm":     _vllm_factory("glm_vllm",     "zai-org/GLM-4.1V-9B-Thinking-FP8",  "ANON_VLLM_URL_GLM"),
    "qwen_vl_vllm": _vllm_factory("qwen_vl_vllm", "Qwen/Qwen2.5-VL-7B-Instruct",       "ANON_VLLM_URL_QWEN"),
    "lighton_vllm": _vllm_factory("lighton_vllm", "lightonai/LightOnOCR-1B-1025",      "ANON_VLLM_URL_LIGHTON"),
}

AVAILABLE_ENGINES = list(_REGISTRY)

_SIDECAR_ROUTES: dict[str, str] = {
    # paddle_vl now runs locally on the main image (upstream HF repo requires
    # transformers>=5.0 as of 2026-04, no longer compatible with the 4.51-pinned
    # legacy_vlm sidecar).
    "monkey_ocr": os.getenv("ANON_SIDECAR_LEGACY_VLM", "http://legacy_vlm:8001"),
    "kerasocr":   os.getenv("ANON_SIDECAR_KERASOCR",   "http://kerasocr:8002"),
}


def get_ocr_engine(name: str = "tesseract", **kwargs) -> OCREngine:
    """Instantiate and return the requested OCR engine.

    Tries the local implementation first. If it's not installed but the engine
    is known to live in a sidecar (_SIDECAR_ROUTES), returns a proxy that
    forwards extract_text() over HTTP to that sidecar.
    """
    key = name.lower()
    if key not in _REGISTRY:
        raise ValueError(
            f"Unknown OCR engine: '{name}'. "
            f"Available: {AVAILABLE_ENGINES}. "
            f"See docs/users/OCR_ENGINES.md for installation instructions."
        )
    engine = _REGISTRY[key](**kwargs)
    if engine.is_available():
        logger.info("OCR engine loaded: %s (local)", name)
        return engine

    sidecar_url = _SIDECAR_ROUTES.get(key)
    if sidecar_url:
        proxy = SidecarOCREngine(engine_name=key, base_url=sidecar_url)
        if proxy.is_available():
            logger.info("OCR engine loaded: %s (sidecar %s)", name, sidecar_url)
            return proxy
        logger.warning(
            "Sidecar for '%s' at %s is unreachable or does not advertise this engine.",
            name, sidecar_url,
        )

    raise RuntimeError(
        f"OCR engine '{name}' is not installed. "
        f"See docs/users/OCR_ENGINES.md for installation instructions."
    )
