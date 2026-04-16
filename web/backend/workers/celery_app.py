"""Celery application configuration."""
import logging
import os

from celery import Celery
from celery.signals import worker_process_init

logger = logging.getLogger(__name__)

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
    # Recycle worker after N tasks to release VRAM held by VLM OCR engines
    # (models stay cached on the engine instance + PyTorch allocator keeps
    # VRAM even after `del`). 1 = kill after every job (safe on small GPUs,
    # ~5-30s reload latency per job). 0 = never recycle (keep warm; right for
    # big-RAM servers where latency matters more than memory churn).
    worker_max_tasks_per_child=int(os.getenv("WORKER_MAX_TASKS_PER_CHILD", "1")) or None,
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


@worker_process_init.connect
def warm_up_default_model(sender, **kwargs):  # noqa: ARG001
    """Pre-load the default NER model inside each worker process after fork.

    worker_process_init fires INSIDE each forked worker — unlike worker_ready
    which fires in the MainProcess (before workers exist). This ensures the
    loaded engine lives in the same process that will serve jobs, so
    _ENGINE_CACHE hits on every subsequent call.

    Set WARMUP_MODEL=none to disable (regex-only deployments).
    Set WARMUP_MODEL=<model_id> to pre-load a non-default model.
    Set WARMUP_LANG=pt to also warm up Portuguese spaCy pipeline.
    """
    model = os.getenv("WARMUP_MODEL", "Davlan/xlm-roberta-base-ner-hrl")
    lang  = os.getenv("WARMUP_LANG", "en")

    if model.lower() == "none":
        return

    logger.info("Worker process init — warming up '%s' (lang=%s) …", model, lang)
    try:
        from src.anon.engine import warm_up_model
        warm_up_model(transformer_model=model, lang=lang)
        logger.info("Warm-up complete for '%s'.", model)
    except Exception as exc:
        logger.warning("Warm-up failed — first job will be slow: %s", exc)
