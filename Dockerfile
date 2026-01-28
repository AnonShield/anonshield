# =============================================================================
# AnonLFI - Multi-stage Dockerfile with Lazy Loading
# =============================================================================
#
# Design Principles:
# - Lazy Loading: Models are NOT downloaded at build time
# - Modularity: Tesseract is optional, installed but not loaded unless needed
# - Persistence: Models are stored in volumes for reuse across containers
# - GPU Support: Works with or without NVIDIA GPU
#
# Build targets:
#   docker build -t anon:latest .                    # CPU version
#   docker build -t anon:gpu --target gpu .          # GPU version
#
# Usage:
#   docker run -v anon-models:/app/models anon:latest input.txt
#   docker-compose up  # Recommended - includes Ollama
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base image with system dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Application configuration
    ANON_LAZY_LOADING=1 \
    # Ollama configuration (for docker-compose networking)
    OLLAMA_BASE_URL="http://ollama:11434"

# Install system dependencies
# - tesseract-ocr: OCR capabilities (lazy - only loaded when processing images)
# - libmagic1: File type detection
# - build-essential: Required for compiling native extensions (hdbscan, etc.)
# - curl: Health checks and downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por \
    libmagic1 \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH (must be after install)
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencies installation
# -----------------------------------------------------------------------------
FROM base AS dependencies

# Copy only dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install Python dependencies (without dev dependencies)
# Using --no-cache to reduce image size
RUN uv sync --no-cache --no-dev

# -----------------------------------------------------------------------------
# Stage 3: Production image (CPU)
# -----------------------------------------------------------------------------
FROM dependencies AS production

# Copy application source
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY anon.py ./
COPY anonymization_config.json ./

# Create directories for runtime data
RUN mkdir -p /app/models /app/output /app/logs /app/db

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Volumes for persistent data
VOLUME ["/app/models", "/app/output", "/app/db"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]

# -----------------------------------------------------------------------------
# Stage 4: GPU-enabled image
# -----------------------------------------------------------------------------
FROM nvidia/cuda:12.1-runtime-ubuntu22.04 AS gpu-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ANON_LAZY_LOADING=1 \
    OLLAMA_BASE_URL="http://ollama:11434" \
    # CUDA configuration
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    tesseract-ocr \
    tesseract-ocr-por \
    libmagic1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/python3.12 /usr/bin/python3

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

FROM gpu-base AS gpu

# Copy from production stage
COPY --from=dependencies /app/.venv /app/.venv
COPY --from=production /app/src /app/src
COPY --from=production /app/prompts /app/prompts
COPY --from=production /app/anon.py /app/
COPY --from=production /app/anonymization_config.json /app/
COPY --from=production /usr/local/bin/docker-entrypoint.sh /usr/local/bin/

RUN mkdir -p /app/models /app/output /app/logs /app/db

VOLUME ["/app/models", "/app/output", "/app/db"]

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["--help"]
