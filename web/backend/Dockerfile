# syntax=docker/dockerfile:1
# Build from the repository root. Targets:
#   production (default): the API and worker image of the hosted site, which
#     runs behind its proxy next to the frontend image.
#   local: the whole app in one container for one computer, published as
#     anonshield/anon:web. Redis, the worker and the API run together, and the
#     API also serves the interface, so it needs no proxy and no Node.
#   local with --build-arg LOCAL_BASE=runtime-gpu: the same app with the CUDA
#     build of PyTorch (run with --gpus all), published as :web-gpu
#     (TORCH_CUDA=cu130: NVIDIA driver >= 580, RTX 20xx or newer, needed for
#     RTX 50xx) and :web-gpu-cu126 (TORCH_CUDA=cu126: older GPUs and drivers).
ARG LOCAL_BASE=runtime

# ---- builder: resolve and install the Python deps into a venv ----
FROM python:3.12-slim AS builder
WORKDIR /app
# build-essential is only needed at build time for any package without a wheel.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_NO_CACHE=1
# --group web: FastAPI, Celery, Redis and web-only deps. tesseract-only OCR with
# CPU torch. --no-install-project: the source is copied into the runtime stage.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --group web \
    && find /app/.venv -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find /app/.venv -type d -name tests -prune -exec rm -rf {} + \
    && find /app/.venv -name "*.pyc" -delete

# ---- builder-gpu: the same venv with the CUDA build of torch/torchvision ----
# The exact versions of uv.lock from the CUDA index, as docker/Dockerfile does
# for the command-line GPU images; the build fails if torch is still CPU-only.
FROM builder AS builder-gpu
ARG TORCH_CUDA=cu130
RUN TORCH_VER="$(.venv/bin/python -c "import importlib.metadata as m; print(m.version('torch').split('+')[0])")" \
    && TV_VER="$(.venv/bin/python -c "import importlib.metadata as m; print(m.version('torchvision').split('+')[0])")" \
    && uv pip install --python .venv/bin/python \
       --index-url "https://download.pytorch.org/whl/${TORCH_CUDA}" \
       --reinstall-package torch --reinstall-package torchvision \
       "torch==${TORCH_VER}+${TORCH_CUDA}" "torchvision==${TV_VER}+${TORCH_CUDA}" \
    && .venv/bin/python -c "import torch; assert torch.version.cuda, 'CPU torch in the GPU image'; print('torch', torch.__version__, 'CUDA', torch.version.cuda)" \
    && find .venv -type d -name __pycache__ -prune -exec rm -rf {} + \
    && find .venv -type d -name tests -prune -exec rm -rf {} +

# ---- runtime-base: system packages and the app user, shared by CPU and GPU ----
FROM python:3.12-slim AS runtime-base
RUN groupadd -r anonuser && useradd -r -g anonuser -d /app -s /sbin/nologin anonuser
WORKDIR /app
# Runtime system deps only: Tesseract OCR with its language packs, libmagic for
# file-type detection, and libgomp for the torch/numpy OpenMP runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-deu \
    libmagic1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_VERBOSITY=error \
    HF_HUB_DISABLE_PROGRESS_BARS=1

# ---- runtime: the CPU venv and the application ----
# The venv comes prebuilt (no compilers here). Only the directories the app
# writes to change owner: a recursive chown of /app rewrote the whole venv into
# a second layer and doubled the image (~5 GB).
FROM runtime-base AS runtime
COPY --from=builder /app/.venv /app/.venv
COPY src ./src
COPY anon.py ./anon.py
COPY web/backend/. /app/
RUN mkdir -p /anon-jobs /app/.cache && chown anonuser:anonuser /app /app/.cache /anon-jobs
USER anonuser

# ---- runtime-gpu: the same with the CUDA venv ----
FROM runtime-base AS runtime-gpu
ENV NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility
COPY --from=builder-gpu /app/.venv /app/.venv
COPY src ./src
COPY anon.py ./anon.py
COPY web/backend/. /app/
RUN mkdir -p /anon-jobs /app/.cache && chown anonuser:anonuser /app /app/.cache /anon-jobs
USER anonuser

# ---- the interface as static files, for the local image ----
FROM node:22-alpine AS interface
WORKDIR /app
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN ANON_STATIC_UI=1 npm run build

# ---- local: everything in one container, no limits (anonshield/anon:web) ----
FROM ${LOCAL_BASE} AS local
USER root
RUN apt-get update && apt-get install -y --no-install-recommends redis-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /data && chown anonuser:anonuser /data
COPY --from=interface /app/build /app/static
ENV ANON_DATA_DIR=/data \
    ANON_JOBS_DIR=/data/jobs \
    ANON_METRICS_DB=/data/metrics.db \
    XDG_CACHE_HOME=/data/cache \
    HF_HOME=/data/cache/huggingface \
    TMPDIR=/data/cache/tmp \
    ANON_STATIC_DIR=/app/static \
    ANON_MAX_SIZE_MB=0 \
    ANON_MAX_SIZE_KEY_MB=0 \
    ANON_MAX_ZIP_SIZE_MB=0 \
    ANON_FORCE_LARGE_XML=true \
    ANON_RATE_LIMIT_ENABLED=false \
    ANON_JOB_TTL_SECONDS=0
USER anonuser
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=4)"]
CMD ["python", "/app/local_entrypoint.py"]

# ---- production (default target) ----
FROM runtime AS production
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
