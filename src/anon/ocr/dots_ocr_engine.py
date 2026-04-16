"""DotsOCR — 3B layout-aware VLM, released Jul/2025.

HuggingFace: rednote-hilab/dots.ocr
Install: pip install "transformers>=4.45" torch pillow
         (or: uv sync --extra dots-ocr)
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)

_MODEL_ID = "rednote-hilab/dots.ocr"


class DotsOCREngine(OCREngine):
    def __init__(self, max_new_tokens: int = 2048):
        self._max_tokens = max_new_tokens
        self._model = None
        self._processor = None

    @property
    def name(self) -> str:
        return "dots_ocr"

    def is_available(self) -> bool:
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForCausalLM, AutoProcessor  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor
        logger.info("Loading DotsOCR (3B)…")
        self._processor = AutoProcessor.from_pretrained(_MODEL_ID, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            _MODEL_ID,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        ).eval()

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import torch
            from PIL import Image
            self._load()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "Extract text from the document."},
                ],
            }]
            inputs = self._processor.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_dict=True, return_tensors="pt",
            ).to(self._model.device)
            with torch.no_grad():
                out = self._model.generate(**inputs, max_new_tokens=self._max_tokens)
            generated = out[0, inputs["input_ids"].shape[1]:]
            return self._processor.decode(generated, skip_special_tokens=True)
        except Exception as exc:
            logger.error("DotsOCR failed: %s", exc)
            return ""
