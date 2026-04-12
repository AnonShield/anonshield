"""AnonShield Web — FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import jobs, entities

app = FastAPI(
    title="AnonShield Web API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(entities.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/profiles/validate")
def validate_profile(body: dict) -> dict:
    from services.profile import validate_profile as _validate
    content = body.get("content", "")
    return _validate(content)
