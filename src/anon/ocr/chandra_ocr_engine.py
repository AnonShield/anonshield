"""Chandra OCR — 9B VLM, olmOCR-Bench 83.1, fits on 16 GB VRAM.

HuggingFace: datalab-to/chandra
Install: pip install "transformers>=4.45" torch pillow
         (or: uv sync --extra chandra-ocr)
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)

_MODEL_ID = "datalab-to/chandra"


class ChandraOCREngine(OCREngine):
    def __init__(self, max_new_tokens: int = 2048):
        self._max_tokens = max_new_tokens
        self._model = None
        self._processor = None

    @property
    def name(self) -> str:
        return "chandra_ocr"

    def is_available(self) -> bool:
        try:
            import torch  # noqa: F401
            from transformers import AutoModelForImageTextToText, AutoProcessor  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor
        logger.info("Loading Chandra OCR (9B)…")
        self._processor = AutoProcessor.from_pretrained(_MODEL_ID, trust_remote_code=True)
        self._model = AutoModelForImageTextToText.from_pretrained(
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
                    {"type": "text", "text": "OCR the document. Return only the text content."},
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
            logger.error("Chandra OCR failed: %s", exc)
            return ""
