"""AnonShield Web: FastAPI application."""
import os

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
    # The app is served under /api (the host proxy routes /api/* here), so the
    # OpenAPI spec must live under /api too; otherwise the Swagger UI at
    # /api/docs fetches /openapi.json at the root and gets a 404.
    openapi_url="/api/openapi.json",
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
    # ANON_VERSION is the deployed commit (set by the deploy); the deploy checks
    # that the public site reports it, so a stale stack cannot pass as healthy.
    return {"status": "ok", "version": os.getenv("ANON_VERSION", "dev")}


@app.get("/api/config")
def get_config() -> dict:
    """Public configuration for the frontend (file size limits, etc.)."""
    from src.anon.config import NerDefaults
    return {
        "limit_no_key_mb": jobs.LIMIT_NO_KEY // 1024 // 1024,
        "limit_with_key_mb": jobs.LIMIT_WITH_KEY // 1024 // 1024,
        "ner_defaults": {
            "score_threshold": NerDefaults.SCORE_THRESHOLD,
            "aggregation_strategy": NerDefaults.AGGREGATION_STRATEGY,
            "aggregation_choices": list(NerDefaults.AGGREGATION_CHOICES),
        },
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
    Text formats use the first 256 KB; XLSX uses the seekable upload.
    """
    import io
    from src.anon.utils import detect_fields_from_stream

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    
    # Handle XLSX separately as it needs a full engine
    if ext == "xlsx":
        import openpyxl
        try:
            wb = openpyxl.load_workbook(file.file, read_only=True, data_only=True)
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
