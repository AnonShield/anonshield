FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd -r anonuser && useradd -r -g anonuser -d /app -s /sbin/nologin anonuser

WORKDIR /app

# System deps for OCR (Tesseract + OpenCV/Paddle/DocTR dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-por tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-deu \
    libmagic1 \
    libgl1 libglib2.0-0 \
    libsm6 libxext6 libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install Python deps — uv sync always creates /app/.venv
# --group web: FastAPI, Celery, Redis and web-only deps
# --all-extras: easyocr, paddleocr, doctr, kerasocr
# --no-install-project: source is copied separately below
COPY pyproject.toml uv.lock ./
ENV UV_NO_CACHE=1
RUN uv sync --frozen --no-install-project --group web --all-extras

# Expose the virtual environment in PATH so celery/uvicorn/python resolve correctly
ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Copy local source directly into the image
COPY src ./src
COPY anon.py ./anon.py

# Copy backend app code (explicitly copying contents to /app)
COPY web/backend/. /app/

# Ensure correct permissions for the non-root user and create cache dir
RUN mkdir -p /anon-jobs /app/.cache && chown -R anonuser:anonuser /app /anon-jobs

USER anonuser

ENV PYTHONPATH="/app"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
