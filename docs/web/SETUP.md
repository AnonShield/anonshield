# AnonShield Web: Setup Guide

This guide covers running the AnonShield web application in both **production** and **development** modes.

---

## Architecture Overview

```
Browser → Caddy (TLS) → FastAPI (backend) ← Redis ← Celery workers
                      → SvelteKit (frontend)
```

- **Frontend**: SvelteKit SSR app (Node.js, port 3000)
- **Backend**: FastAPI + uvicorn (port 8000)
- **Queue**: Celery with two queues: `fast` (CPU/regex) and `gpu` (NER models)
- **Broker**: Redis (no persistence, purely ephemeral)
- **TLS**: Caddy with automatic HTTPS (production) or plain HTTP (dev)

---

## Production Setup

### Prerequisites

- Docker + Docker Compose v2
- NVIDIA Container Toolkit (if using GPU workers, optional)
- A domain name pointed at your server (for automatic HTTPS via Caddy)

### 1. Environment Variables

Create a `.env` file in `web/`:

```bash
# Required
ANON_SECRET_KEY=<at-least-32-chars-random-hex>

# Optional (defaults shown)
ANON_MAX_SIZE_MB=10       # per-file size limit (default 10 MB)
PUBLIC_API_URL=/api       # frontend API base (leave as-is behind Caddy)
```

Generate a secure key:

```bash
openssl rand -hex 32
```

### 2. Configure Caddy

Edit `web/Caddyfile`, replace the domain:

```
anonshield.example.com {
    request_body {
        max_size 10MB     # match ANON_MAX_SIZE_MB
    }

    handle /api/* {
        reverse_proxy backend:8000
    }

    handle {
        reverse_proxy frontend:3000
    }
}
```

Caddy fetches a Let's Encrypt certificate automatically on first request.

### 3. Start Services

```bash
cd web
docker compose -f docker-compose.prod.yml up -d
```

Services started:

| Service | Role |
|---------|------|
| `caddy` | TLS termination, reverse proxy |
| `frontend` | SvelteKit SSR (Node.js) |
| `backend` | FastAPI API server |
| `worker-fast` | Celery: CPU queue (regex, fast NER) |
| `redis` | Broker + entity-list cache |

> **GPU workers**: If you have a NVIDIA GPU, add a `worker-gpu` service (see `docker-compose.yml` for the template). Requires the NVIDIA Container Toolkit installed on the host.

### 4. First Run: Model Downloads

On first startup the Celery workers will download transformer models from HuggingFace. Depending on your chosen model:

| Model | Size |
|-------|------|
| `Davlan/xlm-roberta-base-ner-hrl` (default) | ~1.1 GB |
| `attack-vector/SecureModernBERT-NER` | ~400 MB |

Models are cached in the `model_cache` Docker volume (`/app/.cache/huggingface` inside the container). Subsequent restarts use the cache.

### 5. Health Check

```bash
curl https://anonshield.example.com/api/health
# → {"status": "ok"}
```

---

## Development Setup

Dev mode runs each service natively (no Docker required) with hot-reload. OCR uses Tesseract, installed via your system package manager.

### Prerequisites

- Python 3.11+ with `uv`
- Node.js 20+ with `npm`
- Redis (`redis-server`)
- Tesseract (`tesseract-ocr`)

Install system dependencies (Ubuntu/Debian):

```bash
sudo apt-get install redis-server tesseract-ocr tesseract-ocr-por
```

### 1. Clone and Install

```bash
git clone <repo-url>
cd tool

# Python deps: installs core + web group (FastAPI, Celery, Redis, etc.)
uv sync --group web

# Frontend deps
cd web/frontend
npm install
cd ../..
```

> **About dev deps**: The `web` group installs only what's needed for the web server. OCR runs on Tesseract (a system package), so no extra Python OCR dependencies are required.

### 2. Environment

```bash
export ANON_SECRET_KEY="dev-key-do-not-use-in-production-123"
export REDIS_URL="redis://localhost:6379/0"
export ANON_JOBS_DIR="/tmp/anon-jobs"
mkdir -p /tmp/anon-jobs
```

Add these to your shell profile or create a `.envrc` file (direnv).

### 3. Start Services

Open **four terminals**:

**Terminal 1: Redis**
```bash
redis-server --save "" --appendonly no
```

**Terminal 2: Backend API**
```bash
cd web/backend
PYTHONPATH=. uvicorn main:app --reload --port 8000
```

**Terminal 3: Celery Worker**
```bash
cd web/backend
PYTHONPATH=. celery -A workers.celery_app worker -Q fast,gpu --concurrency 2 --loglevel=info
```

**Terminal 4: Frontend**
```bash
cd web/frontend
PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

Open: `http://localhost:5173`

The frontend dev server proxies API calls to `localhost:8000`. Hot-reload is active for both frontend and backend.

---

## Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ANON_SECRET_KEY` | None (required) | HMAC key for pseudonymization |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `ANON_JOBS_DIR` | `/anon-jobs` | Scratch dir for in-flight job files |
| `ANON_MAX_SIZE_MB` | `10` | Per-file upload size limit (MB) |
| `PUBLIC_API_URL` | `/api` | API base URL (seen by browser) |
| `TRANSFORMERS_CACHE` | `/app/.cache/huggingface` | HuggingFace model cache dir |

---

## Data Privacy

- Input files are deleted **immediately** after the worker reads them.
- Output files are deleted **immediately** after streaming to the browser.
- The anonymization key is stored only in Redis (1h TTL); never written to disk.
- `--db-mode in-memory` is set on every job; no entity database is created.
- Celery Beat runs cleanup every 15 minutes for any orphaned job files.

---

## Updating

```bash
cd web
git pull
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

Model cache is preserved across rebuilds (stored in the `model_cache` volume).
