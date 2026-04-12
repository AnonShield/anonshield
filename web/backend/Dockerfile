FROM python:3.12-slim

# Create a non-root user for security
RUN groupadd -r anonuser && useradd -r -g anonuser -d /app -s /sbin/nologin anonuser

WORKDIR /app

# System deps for pytesseract and python-magic
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-por \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy local source directly into the image for portability (No runtime mounts needed)
COPY src /app/src
COPY anon.py /app/anon.py

COPY web/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend app code
COPY web/backend /app

# Ensure correct permissions for the non-root user
RUN mkdir -p /anon-jobs && chown -R anonuser:anonuser /app /anon-jobs

USER anonuser

ENV PYTHONPATH="/app"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
