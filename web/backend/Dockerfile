# syntax=docker/dockerfile:1
# Build from the repository root. Targets:
#   production (default): the API and worker image of the hosted site, which
#     runs behind its proxy next to the frontend image.
#   local: the whole app in one container for one computer, published as
#     anonshield/anon:web. Redis, the worker and the API run together, and the
#     API also serves the interface, so it needs no proxy and no Node.

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

# ---- runtime: slim image with only what is needed to run ----
FROM python:3.12-slim AS runtime
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

# Copy the prebuilt virtual environment from the builder (no compilers in runtime).
COPY --from=builder /app/.venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_VERBOSITY=error \
    HF_HUB_DISABLE_PROGRESS_BARS=1

# Application source.
COPY src ./src
COPY anon.py ./anon.py
COPY web/backend/. /app/

# Only the directories the app writes to change owner. A recursive chown of /app
# rewrote the whole venv into a second layer and doubled the image (~5 GB); the
# code and the venv stay root-owned and read-only for the app user.
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
FROM runtime AS local
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
