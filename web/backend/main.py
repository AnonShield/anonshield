"""AnonShield Web — FastAPI application."""
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from routers import jobs, entities, metrics
from services.metrics import MetricsMiddleware, init_db
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from services.limiter import limiter

app = FastAPI(
    title="AnonShield Web API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

# Initialize metrics DB on startup (no-op if already exists)
init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(jobs.router)
app.include_router(entities.router)
app.include_router(metrics.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config")
def get_config() -> dict:
    """Public configuration for the frontend (file size limits, etc.)."""
    import os
    return {
        "limit_no_key_mb":   int(os.getenv("ANON_MAX_SIZE_MB",     "1")),
        "limit_with_key_mb": int(os.getenv("ANON_MAX_SIZE_KEY_MB", "1")),
    }


@app.post("/api/profiles/validate")
def validate_profile(body: dict) -> dict:
    from services.profile import validate_profile as _validate
    content = body.get("content", "")
    return _validate(content)


@app.post("/api/analyze-fields")
async def analyze_fields(file: UploadFile) -> dict:
    """Detect columns/fields from a structured file (CSV, XLSX, JSON, JSONL).
    Returns {fields: [{name, sample_values}]} for field selector UI.
    Accepts first 256 KB only — lightweight, no disk write.
    """
    import io
    from src.anon.utils import detect_fields_from_stream

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    
    # Handle XLSX separately as it needs a full engine
    if ext == "xlsx":
        import openpyxl
        try:
            chunk = await file.read(256 * 1024)
            wb = openpyxl.load_workbook(io.BytesIO(chunk), read_only=True, data_only=True)
            ws = wb.active
            headers: list[str] = []
            if ws is not None:
                first_row = next(ws.iter_rows(max_row=1), None)  # type: ignore[arg-type]
                if first_row:
                    headers = [str(c.value) for c in first_row if c.value is not None]
            wb.close()
            return {"fields": [{"name": h} for h in headers]}
        except Exception as e:
            return {"fields": [], "error": str(e)}

    # Use unified detection for text formats
    try:
        # We need to wrap the bytes in a BytesIO for the utility
        chunk = await file.read(256 * 1024)
        field_names = detect_fields_from_stream(io.BytesIO(chunk), ext)
        return {"fields": [{"name": n} for n in field_names]}
    except Exception as e:
        return {"fields": [], "error": str(e)}
