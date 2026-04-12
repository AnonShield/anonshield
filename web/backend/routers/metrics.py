"""GET /api/metrics — anonymization benchmark data."""
from fastapi import APIRouter, Query
from services.metrics import get_summary

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
def metrics(limit: int = Query(100, le=1000)) -> dict:
    return get_summary()
