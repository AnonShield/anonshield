"""Rate limiting service using SlowAPI."""
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize limiter with Redis storage for persistence across restarts
limiter = Limiter(
    enabled=os.getenv("ANON_RATE_LIMIT_ENABLED", "true").lower() not in {"false", "0", "no"},
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    strategy="fixed-window"
)
