"""LightOn OCR-2 engine — 1B params, native transformers, CPU/MPS/GPU compatible.

HuggingFace: lightonai/LightOnOCR-2-1B
Output: Markdown-formatted text.

Install: pip install "transformers>=5.0.0" pypdfium2 torch pillow
         (or: uv add --optional lighton-ocr transformers pypdfium2)
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)

_MODEL_ID = "lightonai/LightOnOCR-2-1B"


class LightOnOCREngine(OCREngine):
    def __init__(self, max_new_tokens: int = 1024):
        self._max_tokens = max_new_tokens
        self._model = None
        self._processor = None
        self._device = None
        self._dtype = None

    @property
    def name(self) -> str:
        return "lighton_ocr"

    def is_available(self) -> bool:
        try:
            from transformers import LightOnOcrForConditionalGeneration  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import LightOnOcrForConditionalGeneration, LightOnOcrProcessor

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._dtype = torch.bfloat16 if self._device == "cuda" else torch.float32
        logger.info("Loading LightOn OCR-2 on %s…", self._device)
        self._model = LightOnOcrForConditionalGeneration.from_pretrained(
            _MODEL_ID, torch_dtype=self._dtype
        ).to(self._device).eval()
        self._processor = LightOnOcrProcessor.from_pretrained(_MODEL_ID)

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import torch
            from PIL import Image
            self._load()

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            conversation = [{"role": "user", "content": [{"type": "image", "url": image}]}]
            inputs = self._processor.apply_chat_template(
                conversation, add_generation_prompt=True,
                tokenize=True, return_dict=True, return_tensors="pt",
            )
            inputs = {
                k: v.to(device=self._device, dtype=self._dtype) if v.is_floating_point() else v.to(self._device)
                for k, v in inputs.items()
            }
            with torch.no_grad():
                out = self._model.generate(**inputs, max_new_tokens=self._max_tokens)
            generated = out[0, inputs["input_ids"].shape[1]:]
            return self._processor.decode(generated, skip_special_tokens=True)
        except Exception as exc:
            logger.error("LightOn OCR failed: %s", exc)
            return ""
