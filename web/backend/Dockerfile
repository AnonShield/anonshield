# syntax=docker/dockerfile:1

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
FROM python:3.12-slim
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
    PYTHONUNBUFFERED=1

# Application source.
COPY src ./src
COPY anon.py ./anon.py
COPY web/backend/. /app/

# Only the directories the app writes to change owner. A recursive chown of /app
# rewrote the whole venv into a second layer and doubled the image (~5 GB); the
# code and the venv stay root-owned and read-only for the app user.
RUN mkdir -p /anon-jobs /app/.cache && chown anonuser:anonuser /app /app/.cache /anon-jobs
USER anonuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
