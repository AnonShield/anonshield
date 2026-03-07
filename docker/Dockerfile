# =============================================================================
# AnonLFI - Multi-stage Dockerfile
# =============================================================================
#
# Architecture:
#   builder-cpu  -> production (CPU runtime, ~1.5GB)
#   builder-gpu  -> gpu        (GPU runtime, ~5GB)
#
# Build:
#   docker build -t anon:latest -f docker/Dockerfile .
#   docker build -t anon:gpu --target gpu -f docker/Dockerfile .
#
# =============================================================================

# ----------------------------------------------------------------------------- 
# Stage 1: CPU Builder (compile everything, thrown away after)
# ----------------------------------------------------------------------------- 
FROM python:3.12-slim AS builder-cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install deps, then swap torch for CPU-only build (~300MB vs ~4.9GB)
RUN uv sync --no-cache --no-dev \
    && .venv/bin/pip install --no-cache-dir --force-reinstall \
       torch --index-url https://download.pytorch.org/whl/cpu \
    && .venv/bin/pip uninstall -y \
       nvidia-cublas-cu12 nvidia-cuda-cupti-cu12 nvidia-cuda-nvrtc-cu12 \
       nvidia-cuda-runtime-cu12 nvidia-cudnn-cu12 nvidia-cufft-cu12 \
       nvidia-curand-cu12 nvidia-cusolver-cu12 nvidia-cusparse-cu12 \
       nvidia-nccl-cu12 nvidia-nvjitlink-cu12 nvidia-nvtx-cu12 \
       triton 2>/dev/null || true \
    && find .venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find .venv -type d -name tests -exec rm -rf {} + 2>/dev/null || true \
    && find .venv -name "*.pyc" -delete 2>/dev/null || true

# Download spaCy models into the venv so they persist in the image
RUN .venv/bin/python -m spacy download en_core_web_lg

# -----------------------------------------------------------------------------
# Stage 2: CPU Runtime (minimal, no build tools)
# ----------------------------------------------------------------------------- 
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANON_LAZY_LOADING=1 \
    OLLAMA_BASE_URL="http://ollama:11434" \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

RUN apt-get update && apt-get install -y --no-install-recommends bash curl \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app
WORKDIR /app

# Copy only the pre-built venv and app source
COPY --from=builder-cpu /app/.venv /app/.venv/
COPY src/ /app/src/
COPY prompts/ /app/prompts/
COPY tests/ /app/tests/
COPY anon.py /app/
COPY scripts/ /app/scripts/
COPY docker/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /app/models /app/output /app/logs /app/db

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

VOLUME ["/app/models", "/app/output", "/app/db"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]

# ----------------------------------------------------------------------------- 
# Stage 3: GPU Builder
# ----------------------------------------------------------------------------- 
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04 AS builder-gpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN uv sync --no-cache --no-dev \
    && .venv/bin/pip install --no-cache-dir --force-reinstall \
       torch --index-url https://download.pytorch.org/whl/cu128 \
    && .venv/bin/pip install --no-cache-dir cupy-cuda12x==12.3.0 \
    && find .venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true \
    && find .venv -type d -name tests -exec rm -rf {} + 2>/dev/null || true \
    && find .venv -name "*.pyc" -delete 2>/dev/null || true

# Download spaCy models into the venv so they persist in the image
RUN .venv/bin/python -m spacy download en_core_web_lg

# -----------------------------------------------------------------------------
# Stage 4: GPU Runtime (no build tools, no uv)
# ----------------------------------------------------------------------------- 
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04 AS gpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANON_LAZY_LOADING=1 \
    OLLAMA_BASE_URL="http://ollama:11434" \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/app/.venv/bin:$PATH" \
    VIRTUAL_ENV="/app/.venv"

# Runtime-only: python + tesseract + libmagic (no build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv \
    tesseract-ocr tesseract-ocr-por \
    libmagic1 curl bash \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3

RUN mkdir -p /app
WORKDIR /app

# Copy only the pre-built venv and app source
COPY --from=builder-gpu /app/.venv /app/.venv/
COPY src/ /app/src/
COPY prompts/ /app/prompts/
COPY tests/ /app/tests/
COPY anon.py /app/
COPY scripts/ /app/scripts/
COPY docker/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /app/models /app/output /app/logs /app/db

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

VOLUME ["/app/models", "/app/output", "/app/db"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]