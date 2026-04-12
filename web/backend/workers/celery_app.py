"""Celery application configuration."""
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "anonshield",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["workers.tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_routes={
        "workers.tasks.process_job": {"queue": "gpu"},
        "workers.tasks.process_job_fast": {"queue": "fast"},
    },
    beat_schedule={
        "sweep-orphaned-jobs": {
            "task": "workers.tasks.sweep_jobs",
            "schedule": 900.0,  # every 15 min
        },
    },
)
