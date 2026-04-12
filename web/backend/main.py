"""AnonShield Web — FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import jobs, entities, metrics
from services.metrics import MetricsMiddleware, init_db

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

app.include_router(jobs.router)
app.include_router(entities.router)
app.include_router(metrics.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/profiles/validate")
def validate_profile(body: dict) -> dict:
    from services.profile import validate_profile as _validate
    content = body.get("content", "")
    return _validate(content)
