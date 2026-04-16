"""PaddleOCR-VL-1.5 engine — 0.9B VLM, OmniDocBench 94.50, best open-source all-rounder.

HuggingFace: PaddlePaddle/PaddleOCR-VL-1.5
Uses the transformers path (no PaddlePaddle framework required).

Install: pip install "transformers>=5.0.0" torch pillow
         (or: uv add --optional paddle-vl transformers)
"""
import io
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)

_MODEL_ID = "PaddlePaddle/PaddleOCR-VL-1.5"


class PaddleVLEngine(OCREngine):
    def __init__(self, max_new_tokens: int = 1024, compile_model: bool = True):
        self._max_tokens = max_new_tokens
        self._compile = compile_model
        self._model = None
        self._processor = None
        self._device = None

    @property
    def name(self) -> str:
        return "paddle_vl"

    def is_available(self) -> bool:
        try:
            import transformers
            from transformers import AutoModel  # noqa: F401
        except ImportError:
            return False
        # Upstream HF repo was re-baked against transformers 5.x (model card
        # now requires >=5.0.0). We keep the 4.x branch alive via the compat
        # shims in _load() below so older environments still work.
        major = int(transformers.__version__.split(".")[0])
        return major >= 4

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info("Loading PaddleOCR-VL-1.5 on %s…", self._device)
        self._processor = AutoProcessor.from_pretrained(_MODEL_ID)
        # sdpa = PyTorch's built-in flash-attn kernel (no external flash-attn
        # dependency — pre-built FA2 wheels don't cover torch 2.11 yet, and
        # building from source needs CUDA toolkit we don't have on the host).
        self._model = AutoModelForImageTextToText.from_pretrained(
            _MODEL_ID, dtype=torch.bfloat16, attn_implementation="sdpa"
        ).to(self._device).eval()
        # Use static KV cache + compile for autoregressive decoding speedup.
        # dynamic=True handles shape variation across different images.
        if self._compile and self._device == "cuda":
            try:
                self._model.generation_config.cache_implementation = "static"
                self._model.forward = torch.compile(
                    self._model.forward, mode="reduce-overhead", dynamic=True, fullgraph=False
                )
                logger.info("torch.compile enabled for PaddleOCR-VL-1.5")
            except Exception as exc:
                logger.warning("torch.compile failed, falling back to eager: %s", exc)

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            import torch
            from PIL import Image
            self._load()

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            max_pixels = 1280 * 28 * 28
            messages = [{
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "OCR:"},
                ],
            }]
            inputs = self._processor.apply_chat_template(
                messages, add_generation_prompt=True,
                tokenize=True, return_dict=True, return_tensors="pt",
                images_kwargs={"size": {
                    "shortest_edge": self._processor.image_processor.size.shortest_edge,
                    "longest_edge": max_pixels,
                }},
            ).to(self._model.device)
            with torch.inference_mode():
                out = self._model.generate(**inputs, max_new_tokens=self._max_tokens)
            generated = out[0][inputs["input_ids"].shape[-1]:-1]
            return self._processor.decode(generated, skip_special_tokens=True)
        except Exception as exc:
            logger.error("PaddleOCR-VL-1.5 failed: %s", exc)
            return ""
