"""MonkeyOCR-pro engine — 1.2B compact transformer, OmniDocBench 86.96.

HuggingFace: echo840/MonkeyOCR-pro-1.2B
No PyPI package — requires source clone of MonkeyOCR (magic_pdf package) and
its weights in <root>/model_weight. Point MONKEY_OCR_ROOT at the clone.

Install:
    git clone https://github.com/Yuliang-Liu/MonkeyOCR /opt/MonkeyOCR
    cd /opt/MonkeyOCR && python tools/download_model.py -n MonkeyOCR-pro-1.2B
    pip install -r /opt/MonkeyOCR/requirements.txt
    export MONKEY_OCR_ROOT=/opt/MonkeyOCR
"""
import logging
import os
import sys
import tempfile
from pathlib import Path

from .base import OCREngine

logger = logging.getLogger(__name__)

_CANDIDATE_ROOTS = [
    Path("/opt/MonkeyOCR"),
    Path.home() / "MonkeyOCR",
    Path.home() / "anonshield_data/models/MonkeyOCR",
]


def _find_monkey_root() -> Path | None:
    root = os.environ.get("MONKEY_OCR_ROOT")
    if root and (Path(root) / "magic_pdf").exists():
        return Path(root)
    for candidate in _CANDIDATE_ROOTS:
        if (candidate / "magic_pdf").exists():
            return candidate
    return None


class MonkeyOCREngine(OCREngine):
    def __init__(self, task: str = "text", max_new_tokens: int = 1024, backend: str = "transformers"):
        self._task = task          # "text" or "markdown"
        self._max_tokens = max_new_tokens
        self._backend = backend    # transformers | lmdeploy | vllm
        self._model = None
        self._root: Path | None = None

    @property
    def name(self) -> str:
        return "monkey_ocr"

    def is_available(self) -> bool:
        root = _find_monkey_root()
        if root is None:
            return False
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        try:
            from magic_pdf.model.custom_model import MonkeyOCR  # noqa: F401
            return True
        except ImportError:
            return False

    def _write_runtime_config(self, root: Path) -> Path:
        """Copy model_configs.yaml and patch backend to transformers (no lmdeploy needed)."""
        import yaml
        src = root / "model_configs.yaml"
        with open(src) as f:
            cfg = yaml.safe_load(f)
        cfg["chat_config"]["backend"] = self._backend
        out = Path(tempfile.mkstemp(suffix="_monkey.yaml")[1])
        with open(out, "w") as f:
            yaml.safe_dump(cfg, f)
        return out

    def _load(self) -> None:
        if self._model is not None:
            return
        self._root = _find_monkey_root()
        if self._root is None:
            raise RuntimeError("MonkeyOCR root not found — set MONKEY_OCR_ROOT")
        if str(self._root) not in sys.path:
            sys.path.insert(0, str(self._root))
        os.chdir(self._root)  # custom_model reads relative models_dir
        cfg_path = self._write_runtime_config(self._root)
        from magic_pdf.model.custom_model import MonkeyOCR as MonkeyOCRModel
        logger.info("Loading MonkeyOCR-pro-1.2B (backend=%s) from %s…", self._backend, self._root)
        self._model = MonkeyOCRModel(str(cfg_path))

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            self._load()
            prompt = {
                "text": "Please output the text content from the image.",
                "markdown": "Parse this document to markdown.",
            }.get(self._task, "Please output the text content from the image.")
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                f.write(image_bytes)
                tmp = Path(f.name)
            try:
                results = self._model.chat_model.batch_inference([str(tmp)], [prompt])
                return results[0] if results else ""
            finally:
                tmp.unlink(missing_ok=True)
        except Exception as exc:
            logger.error("MonkeyOCR failed: %s", exc)
            return ""
