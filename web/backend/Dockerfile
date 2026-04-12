FROM python:3.12-slim

WORKDIR /app

# System deps for pytesseract and python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# The repo root (with src/anon/) is mounted at /repo at runtime (see docker-compose.yml)
ENV PYTHONPATH="/app:/repo"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
