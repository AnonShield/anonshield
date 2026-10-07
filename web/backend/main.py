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
from services.logs import quiet_third_party_logs

quiet_third_party_logs()

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
    CSV reads its header; JSON and JSONL are streamed through every record, so
    a field that only some records have is listed; XLSX opens the workbook.
    """
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
        field_names = detect_fields_from_stream(file.file, ext)
        return {"fields": [{"name": n} for n in field_names]}
    except Exception as e:
        return {"fields": [], "error": str(e)}


# The local image (web/backend/Dockerfile, target "local") serves the interface
# itself from the static build of web/frontend, so it needs no proxy and no Node.
_STATIC_DIR = os.getenv("ANON_STATIC_DIR")
if _STATIC_DIR:
    from pathlib import Path

    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    _static_root = Path(_STATIC_DIR).resolve()

    @app.get("/{path:path}", include_in_schema=False)
    def interface(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        for candidate in (_static_root / path, _static_root / f"{path}.html"):
            candidate = candidate.resolve()
            if candidate.is_file() and candidate.is_relative_to(_static_root):
                return FileResponse(candidate)
        return FileResponse(_static_root / "index.html")
