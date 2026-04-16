"""OnnxTR engine — ONNX port of DocTR, ~2× faster via ONNX Runtime.

Drop-in alternative to DocTREngine with the same det+reco pipeline but executed
through ONNX Runtime instead of PyTorch. Supports CPU, CUDA, OpenVINO and CoreML
execution providers. Fully local — no cloud calls.

Install (GPU, CUDA 12):
    pip install "onnxtr[gpu]"

Install (CPU only):
    pip install "onnxtr[cpu]"

Trade-offs vs DocTR:
  + Faster inference (~2× on the same hardware per upstream benchmarks).
  + Lower memory footprint — no PyTorch runtime.
  + ONNX quantized variants available (int8 models) for extra speed.
  - Slightly larger initial model downloads (separate det+reco ONNX files).
  - Model versions may lag behind DocTR's latest PyTorch checkpoints.
"""
import logging

from .base import OCREngine

logger = logging.getLogger(__name__)


def _cuda_available() -> bool:
    try:
        import onnxruntime as ort
        return "CUDAExecutionProvider" in ort.get_available_providers()
    except ImportError:
        return False


class OnnxTREngine(OCREngine):
    """OnnxTR backend. Lazy-loads det+reco ONNX models on first use.

    Uses CUDAExecutionProvider when available, else falls back to CPU.
    """

    def __init__(
        self,
        det_arch: str = "fast_base",
        reco_arch: str = "crnn_vgg16_bn",
        pretrained: bool = True,
    ):
        self._det_arch = det_arch
        self._reco_arch = reco_arch
        self._pretrained = pretrained
        self._model = None

    @property
    def name(self) -> str:
        return "onnxtr"

    def is_available(self) -> bool:
        try:
            from onnxtr.models import ocr_predictor  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_model(self):
        if self._model is None:
            from onnxtr.models import ocr_predictor
            providers = None
            if _cuda_available():
                providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                logger.info("OnnxTR will use CUDA execution provider.")
            # OnnxTR dropped the `pretrained` kwarg (models are always pretrained
            # ONNX bundles); it now forwards unknown kwargs to DocumentBuilder
            # which rejects them.
            self._model = ocr_predictor(
                det_arch=self._det_arch,
                reco_arch=self._reco_arch,
                det_providers=providers,
                reco_providers=providers,
            )
        return self._model

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            from onnxtr.io import DocumentFile
            doc = DocumentFile.from_images([image_bytes])
            result = self._get_model()(doc)
            lines = []
            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        lines.append(" ".join(w.value for w in line.words))
            return "\n".join(lines)
        except Exception as exc:
            logger.error("OnnxTR failed: %s", exc)
            return ""
