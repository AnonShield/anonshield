FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd -r anonuser && useradd -r -g anonuser -d /app -s /sbin/nologin anonuser

WORKDIR /app

# System deps for OCR (Tesseract + OpenCV/Paddle/DocTR dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-por tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-deu \
    libmagic1 \
    libgl1 libglib2.0-0 \
    libsm6 libxext6 libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:${PATH}"

# Copy unified requirements (includes Web + Core)
COPY web/backend/requirements.txt ./
RUN uv pip install --system -r requirements.txt

# Copy local source directly into the image
COPY src ./src
COPY anon.py ./anon.py

# Copy backend app code (explicitly copying contents to /app)
COPY web/backend/. /app/

# Ensure correct permissions for the non-root user and create cache dir
RUN mkdir -p /anon-jobs /app/.cache && chown -R anonuser:anonuser /app /anon-jobs

USER anonuser

ENV PYTHONPATH="/app"

CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
