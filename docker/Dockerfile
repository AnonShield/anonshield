# syntax=docker/dockerfile:1
# =============================================================================
# AnonShield - Multi-stage Dockerfile
# =============================================================================
#
# Architecture:
#   builder-cpu  -> production (CPU runtime, default target)
#   builder-gpu  -> gpu        (GPU runtime: same venv, CUDA build of torch)
#   runtime-base: system packages shared by both runtimes
#
# Build:
#   docker build -t anon:latest -f docker/Dockerfile .
#   docker build -t anon:gpu --target gpu -f docker/Dockerfile .
#
# The NER model is not baked in. It is downloaded on first use into
# HF_HOME=/app/models/huggingface, which lives on the /app/models volume, so it
# is fetched once per volume and not on every `docker run`.
#
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: CPU Builder (compile everything, thrown away after)
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder-cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./

# The lock already resolves torch to the CPU build (pytorch-cpu index), so the
# venv is installed exactly as locked. --group pt adds the Portuguese spaCy
# pipeline used by --lang pt (en_core_web_lg is a main dependency).
# pip is added for `spacy download` of any other pipeline at runtime.
# The public suffix list that tldextract (Presidio's URL/e-mail recognizers)
# would otherwise fetch on every run is cached inside the venv, so the
# container makes no network call besides the first NER model download.
RUN uv sync --locked --no-dev --no-install-project --group pt \
    && .venv/bin/python -m ensurepip --upgrade \
    && .venv/bin/python -c "import torch, spacy; assert spacy.util.is_package('pt_core_news_lg')" \
    && TLDEXTRACT_CACHE=/app/.venv/tldextract-cache .venv/bin/python -c "import tldextract; tldextract.extract('example.com')" \
    && find .venv -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find .venv -type d -name tests -prune -exec rm -rf {} +

# -----------------------------------------------------------------------------
# Stage 2: GPU Builder
# -----------------------------------------------------------------------------
# Same locked venv, with torch/torchvision swapped for the CUDA build of the
# exact versions in uv.lock. The wheels bundle the CUDA runtime, so the base is
# the plain Python image; the host driver comes in through the NVIDIA container
# toolkit (`docker run --gpus all`). Two builds are published and
# docker/run.sh --gpu picks one per host:
#   TORCH_CUDA=cu130 -> :gpu        NVIDIA driver >= 580, RTX 20xx or newer
#                                   (CUDA 13 dropped older GPUs; RTX 50xx needs it)
#   TORCH_CUDA=cu126 -> :gpu-cu126  older GPUs and drivers, no RTX 50xx
FROM builder-cpu AS builder-gpu

ARG TORCH_CUDA=cu130

# The last command fails the build if torch is still a CPU build: an earlier
# version of this stage chained the swap with `|| true` and shipped CPU torch
# as :gpu without anyone noticing.
RUN TORCH_VER="$(.venv/bin/python -c "import importlib.metadata as m; print(m.version('torch').split('+')[0])")" \
    && TV_VER="$(.venv/bin/python -c "import importlib.metadata as m; print(m.version('torchvision').split('+')[0])")" \
    && uv pip install --python .venv/bin/python \
       --index-url "https://download.pytorch.org/whl/${TORCH_CUDA}" \
       --reinstall-package torch --reinstall-package torchvision \
       "torch==${TORCH_VER}+${TORCH_CUDA}" "torchvision==${TV_VER}+${TORCH_CUDA}" \
    && .venv/bin/python -c "import torch; assert torch.version.cuda, 'CPU torch in the GPU image'; print('torch', torch.__version__, 'CUDA', torch.version.cuda)" \
    && find .venv -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find .venv -type d -name tests -prune -exec rm -rf {} +

# -----------------------------------------------------------------------------
# Stage 3: runtime base shared by the CPU and GPU images (no build tools)
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANON_LAZY_LOADING=1 \
    OLLAMA_BASE_URL="http://ollama:11434" \
    HF_HOME=/app/models/huggingface \
    TLDEXTRACT_CACHE=/app/.venv/tldextract-cache \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    bash curl \
    tesseract-ocr tesseract-ocr-por \
    libmagic1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Drop perl from the runtime image. It ships in the Debian base as an Essential
# package but the CLI (bash entrypoint + Python venv + tesseract) never invokes
# it, and it carries the only two CRITICAL CVEs in the image plus three HIGH.
# curl stays (the entrypoint uses it for the optional Ollama integration), libgif
# stays (tesseract/leptonica image decoding), ncurses stays (bash).
RUN dpkg --purge --force-remove-essential --force-depends perl-base 2>/dev/null || true; \
    rm -rf /usr/share/doc/* /usr/share/man/* /var/lib/apt/lists/*

RUN mkdir -p /app/models /app/output /app/logs /app/db
WORKDIR /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

VOLUME ["/app/models", "/app/output", "/app/db"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]

# -----------------------------------------------------------------------------
# Stage 4: GPU Runtime
# -----------------------------------------------------------------------------
FROM runtime-base AS gpu

ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

COPY --from=builder-gpu /app/.venv /app/.venv/
COPY src/ /app/src/
COPY tests/ /app/tests/
COPY examples/ /app/examples/
COPY anon.py /app/
COPY scripts/ /app/scripts/
COPY --chmod=755 docker/docker-entrypoint.sh /usr/local/bin/

# -----------------------------------------------------------------------------
# Stage 5: CPU Runtime (last stage: the default target of a plain `docker build`)
# -----------------------------------------------------------------------------
FROM runtime-base AS production

COPY --from=builder-cpu /app/.venv /app/.venv/
COPY src/ /app/src/
COPY tests/ /app/tests/
COPY examples/ /app/examples/
COPY anon.py /app/
COPY scripts/ /app/scripts/
COPY --chmod=755 docker/docker-entrypoint.sh /usr/local/bin/
