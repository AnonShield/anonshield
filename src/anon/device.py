"""Decide once per process whether the NER models can run on the GPU.

``torch.cuda.is_available()`` is not enough: a CUDA build of torch can see a
GPU it has no kernels for (an RTX 50xx with a CUDA 12.6 build, a GTX 10xx with
a CUDA 13 build) and then fails mid-run with "no kernel image is available".
This checks the build against the device, runs one small kernel, and falls
back to the CPU with a message that says which build or image to use instead.
"""
import functools
import logging
import os

logger = logging.getLogger(__name__)

_GPU_IMAGE_HINT = (
    "With Docker, ./run.sh --gpu picks the matching image (anonshield/anon:gpu for "
    "NVIDIA driver 580+ and RTX 20xx or newer, anonshield/anon:gpu-cu126 otherwise)."
)


def _nvidia_gpu_visible() -> bool:
    return os.path.exists("/dev/nvidia0") or os.path.exists("/dev/dxg")


def _arch_supported(major: int, minor: int, arch_list: list) -> bool:
    """True if the build ships kernels for compute capability major.minor:
    a cubin for the same major and a lower or equal minor, or PTX for an
    equal or lower capability, which the driver compiles on load."""
    capability = major * 10 + minor
    for arch in arch_list:
        kind, _, number = arch.partition("_")
        if not number.isdigit():
            continue
        value = int(number)
        if kind == "sm" and value // 10 == major and value % 10 <= minor:
            return True
        if kind == "compute" and value <= capability:
            return True
    return False


@functools.lru_cache(maxsize=1)
def cuda_usable() -> bool:
    """Whether to put the NER models on the GPU (cached for the process)."""
    try:
        import torch
    except ImportError:
        return False

    if not torch.cuda.is_available():
        if _nvidia_gpu_visible():
            if torch.version.cuda is None:
                logger.info("An NVIDIA GPU is present but this PyTorch build is CPU-only; running on CPU. "
                            + _GPU_IMAGE_HINT)
            else:
                logger.warning(
                    "PyTorch %s is built for CUDA %s but cannot reach the GPU (NVIDIA driver too old "
                    "for this build?); running on CPU. %s", torch.__version__, torch.version.cuda, _GPU_IMAGE_HINT)
        return False

    try:
        major, minor = torch.cuda.get_device_capability(0)
        name = torch.cuda.get_device_name(0)
        arch_list = torch.cuda.get_arch_list()
        if not _arch_supported(major, minor, arch_list):
            logger.warning(
                "%s (compute capability %d.%d) is not supported by PyTorch %s (CUDA %s, kernels for %s); "
                "running on CPU. %s", name, major, minor, torch.__version__, torch.version.cuda,
                ", ".join(arch_list), _GPU_IMAGE_HINT)
            return False
        (torch.ones(8, device="cuda") * 2).sum().item()
    except Exception as exc:
        logger.warning("CUDA is available but not usable (%s); running on CPU. %s", exc, _GPU_IMAGE_HINT)
        return False
    return True
