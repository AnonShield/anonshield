"""GLM-OCR engine — highest OmniDocBench score (94.62) in the open-source VLM class.

HuggingFace: zai-org/GLM-OCR
Architecture: GlmOcrForConditionalGeneration (native transformers class, no trust_remote_code)

Install: pip install "transformers>=5.3.0" torch pillow
         (or: uv add --optional glm-ocr transformers torch)
"""
import io
import logging
import tempfile
from pathlib import Path

from .base import OCREngine

logger = logging.getLogger(__name__)

_MODEL_ID = "zai-org/GLM-OCR"


class GLMOCREngine(OCREngine):
    def __init__(self, max_new_tokens: int = 1024):
        self._max_tokens = max_new_tokens
        self._model = None
        self._processor = None

    @property
    def name(self) -> str:
        return "glm_ocr"

    def is_available(self) -> bool:
        try:
            from transformers import GlmOcrForConditionalGeneration  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoProcessor, GlmOcrForConditionalGeneration
        logger.info("Loading GLM-OCR…")
        self._processor = AutoProcessor.from_pretrained(_MODEL_ID)
        self._model = GlmOcrForConditionalGeneration.from_pretrained(
            _MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto"
        ).eval()

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import torch
            self._load()
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(image_bytes)
                tmp = Path(f.name)
            try:
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "image", "url": str(tmp)},
                        {"type": "text", "text": "Text Recognition:"},
                    ],
                }]
                inputs = self._processor.apply_chat_template(
                    messages, tokenize=True, add_generation_prompt=True,
                    return_dict=True, return_tensors="pt",
                ).to(self._model.device)
                with torch.no_grad():
                    out = self._model.generate(**inputs, max_new_tokens=self._max_tokens)
                return self._processor.decode(
                    out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
                )
            finally:
                tmp.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("GLM-OCR failed: %s", exc)
            return ""
