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
    "With Docker, ./run.sh --gpu (or ./run.sh --web --gpu) picks the matching image "
    "(anonshield/anon:gpu or :web-gpu for NVIDIA driver 580+ and RTX 20xx or newer, "
    "the -cu126 builds otherwise)."
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

@functools.lru_cache(maxsize=1)
def activate_gpu() -> None:
    """Put the NER models on the GPU when one is usable: CUDA library paths,
    then spaCy on the GPU (CuPy), or, without CuPy, the Hugging Face pipeline
    of the default strategies through PyTorch. Called once per process by the
    command line and by the web worker; a no-op on a CPU-only build."""
    import sys

    import spacy
    import torch

    # --- Common Setup ---
    # Dynamically set LD_LIBRARY_PATH for NVIDIA CUDA libraries.
    # Strategy: check system-wide CUDA paths first (Docker nvidia/cuda image),
    # then fall back to pip-installed nvidia packages (local development).
    cuda_lib_paths = []

    # 1. System-wide CUDA installation (Docker nvidia/cuda base image)
    for sys_path in ["/usr/local/cuda/lib64", "/usr/local/cuda/lib"]:
        if os.path.isdir(sys_path):
            cuda_lib_paths.append(sys_path)

    # 2. Pip-installed NVIDIA packages (local venv)
    if not cuda_lib_paths:
        venv_python_path = os.path.dirname(sys.executable)
        venv_lib_path = os.path.join(os.path.dirname(venv_python_path), "lib")
        if os.path.exists(venv_lib_path):
            venv_pyver = next(
                (d for d in os.listdir(venv_lib_path)
                 if d.startswith("python") and os.path.isdir(os.path.join(venv_lib_path, d))),
                None
            )
            if venv_pyver:
                nvidia_base_path = os.path.join(venv_lib_path, venv_pyver, "site-packages", "nvidia")
                if os.path.exists(nvidia_base_path):
                    for pkg in os.listdir(nvidia_base_path):
                        lib_path = os.path.join(nvidia_base_path, pkg, "lib")
                        if os.path.isdir(lib_path):
                            cuda_lib_paths.append(lib_path)

    if cuda_lib_paths:
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        new_paths = ":".join(cuda_lib_paths)
        os.environ["LD_LIBRARY_PATH"] = f"{new_paths}:{existing}" if existing else new_paths
        logging.info(f"CUDA libraries configured ({len(cuda_lib_paths)} paths added to LD_LIBRARY_PATH)")
    else:
        logging.debug("No NVIDIA CUDA libraries found (CPU-only mode)")

    # --- GPU Activation ---
    logging.info("Verifying hardware...")
    if cuda_usable():
        gpu_name = torch.cuda.get_device_name(0)
        logging.info(f"CUDA GPU detected: {gpu_name}")
        # Test if CuPy actually works on this GPU architecture before enabling spaCy GPU
        cupy_works = False
        try:
            import cupy
            a = cupy.array([1.0, 2.0])
            _ = (a * a).sum()  # Force kernel compilation to detect arch incompatibility
            cupy.cuda.Stream.null.synchronize()
            cupy_works = True
        except Exception as e:
            logging.info(f"CuPy not usable on this GPU ({e}). spaCy will use CPU.")
        if cupy_works and spacy.prefer_gpu():  # type: ignore
            logging.info(f"spaCy GPU activated (CuPy backend on {gpu_name})")
        else:
            # CuPy unavailable/incompatible: spaCy stays on CPU, but force the
            # HuggingFace transformer pipeline to use GPU via PyTorch directly.
            # hf_token_pipe reads get_torch_default_device() from its module scope,
            # so patching it here (before any nlp.add_pipe call) redirects to CUDA.
            try:
                import spacy_huggingface_pipelines.token_classification as _shp_tc
                _shp_tc.get_torch_default_device = lambda: torch.device("cuda:0")
                logging.info(f"Transformers pipeline GPU activated via PyTorch direct (spaCy NLP on CPU).")
            except Exception as e2:
                logging.info(f"Could not activate GPU for transformer pipeline: {e2}. Running fully on CPU.")
    else:
        logging.info("No usable CUDA GPU. Running on CPU.")
