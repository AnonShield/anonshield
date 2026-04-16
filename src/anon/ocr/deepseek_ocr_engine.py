"""DeepSeek-OCR-2 engine — 3B MoE, OmniDocBench 91.09. CUDA + flash-attn required.

HuggingFace: deepseek-ai/DeepSeek-OCR-2
Requires: flash-attn==2.7.3, transformers==4.46.3 (pinned), CUDA GPU.

WARNING: This engine pins transformers to 4.46.3 which may conflict with other
engines. Install in a dedicated environment or after other VLM engines.

Install:
    pip install transformers==4.46.3 tokenizers==0.20.3 einops addict easydict
    pip install flash-attn==2.7.3 --no-build-isolation
    (or: uv add --optional deepseek-ocr transformers==4.46.3 einops addict easydict)
"""
import logging
import tempfile
from pathlib import Path

from .base import OCREngine

logger = logging.getLogger(__name__)

_MODEL_ID = "deepseek-ai/DeepSeek-OCR-2"
_PLAIN_PROMPT = "<image>\nFree OCR. "
_MARKDOWN_PROMPT = "<image>\n<|grounding|>Convert the document to markdown."


class DeepSeekOCREngine(OCREngine):
    def __init__(self, markdown: bool = False, max_new_tokens: int = 2048):
        self._markdown = markdown
        self._max_tokens = max_new_tokens
        self._model = None
        self._tokenizer = None

    @property
    def name(self) -> str:
        return "deepseek_ocr"

    def is_available(self) -> bool:
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            import flash_attn  # noqa: F401
            from transformers import AutoModel  # noqa: F401
            return True
        except ImportError:
            return False

    def _load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModel, AutoTokenizer
        logger.info("Loading DeepSeek-OCR-2 (CUDA required)…")
        self._tokenizer = AutoTokenizer.from_pretrained(_MODEL_ID, trust_remote_code=True)
        self._model = AutoModel.from_pretrained(
            _MODEL_ID,
            _attn_implementation="flash_attention_2",
            trust_remote_code=True,
            use_safetensors=True,
        ).eval().cuda().to(torch.bfloat16)

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            self._load()
            prompt = _MARKDOWN_PROMPT if self._markdown else _PLAIN_PROMPT
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(image_bytes)
                tmp = Path(f.name)
            try:
                result = self._model.infer(
                    self._tokenizer,
                    prompt=prompt,
                    image_file=str(tmp),
                    output_path=None,
                    base_size=1024,
                    image_size=768,
                    crop_mode=True,
                    save_results=False,
                )
                return result or ""
            finally:
                tmp.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("DeepSeek-OCR-2 failed: %s", exc)
            return ""
