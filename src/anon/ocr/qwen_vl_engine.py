"""Qwen2.5-VL — multilingual VLM (inc. PT-BR), native Transformers support.

HuggingFace: Qwen/Qwen2.5-VL-7B-Instruct (default), 3B / 72B also available.
Install: pip install "transformers>=4.49" qwen-vl-utils torch pillow
         (or: uv sync --extra qwen-vl)
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)

_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"


class QwenVLEngine(OCREngine):
    def __init__(self, model_id: str = _MODEL_ID, max_new_tokens: int = 2048):
        self._model_id = model_id
        self._max_tokens = max_new_tokens
        self._model = None
        self._processor = None

    @property
    def name(self) -> str:
        return "qwen_vl"

    def is_available(self) -> bool:
        try:
            import torch  # noqa: F401
            from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        logger.info("Loading Qwen2.5-VL (%s)…", self._model_id)
        self._processor = AutoProcessor.from_pretrained(self._model_id)
        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self._model_id,
            torch_dtype=torch.bfloat16,
            device_map="auto",
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
                    {"type": "text", "text": "Transcreva todo o texto do documento."},
                ],
            }]
            text = self._processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )
            inputs = self._processor(
                text=[text], images=[image],
                padding=True, return_tensors="pt",
            ).to(self._model.device)
            with torch.no_grad():
                out = self._model.generate(**inputs, max_new_tokens=self._max_tokens)
            generated = out[0, inputs["input_ids"].shape[1]:]
            return self._processor.decode(generated, skip_special_tokens=True)
        except Exception as exc:
            logger.error("Qwen2.5-VL failed: %s", exc)
            return ""
