"""Job endpoints: create, status, download."""
import errno
import json
import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import Annotated
from uuid import UUID
from urllib.parse import quote

import aiofiles
from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from services import job_service, storage
from services.profile import validate_profile

from services.limiter import limiter

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Limits are configurable via env vars (values in MB; 0 disables the limit).
# ANON_MAX_SIZE_MB      : without key (default: 1 MB)
# ANON_MAX_SIZE_KEY_MB  : with key     (default: 1 MB)
LIMIT_NO_KEY  = int(os.getenv("ANON_MAX_SIZE_MB",     "1"))  * 1024 * 1024
LIMIT_WITH_KEY = int(os.getenv("ANON_MAX_SIZE_KEY_MB", "1")) * 1024 * 1024
if LIMIT_NO_KEY < 0 or LIMIT_WITH_KEY < 0:
    raise ValueError("ANON_MAX_SIZE_MB and ANON_MAX_SIZE_KEY_MB must be non-negative; use 0 for no limit.")

_GPU_STRATEGIES = {"filtered", "standalone", "hybrid", "presidio"}


def _queue_for(strategy: str) -> str:
    return "gpu" if strategy in _GPU_STRATEGIES else "fast"


@router.post("", status_code=202)
@limiter.limit("5/minute")
async def create_job(
    request: Request,
    file: UploadFile,
    key: Annotated[str, Form()] = "",
    strategy: Annotated[str, Form()] = "filtered",
    lang: Annotated[str, Form()] = "en",
    entities: Annotated[str, Form()] = "",
    config: Annotated[str, Form()] = "",
    fields: Annotated[str, Form()] = "",
    model: Annotated[str, Form()] = "",
    ner_score_threshold: Annotated[float | None, Form()] = None,
    ner_aggregation_strategy: Annotated[str | None, Form()] = None,
    slug_length: Annotated[int | None, Form()] = None,
) -> dict:
    limit = LIMIT_WITH_KEY if key else LIMIT_NO_KEY

    if limit and file.size is not None and file.size > limit:
        raise HTTPException(status_code=413, detail=f"File too large. Limit: {limit // 1024 // 1024} MB")

    _probe = next(p for p in (storage.JOBS_ROOT, *storage.JOBS_ROOT.parents) if p.exists())
    disk = shutil.disk_usage(_probe)
    if disk.free < (file.size or 256 * 1024) * 3:
        raise HTTPException(
            status_code=507,
            detail="Not enough free disk space to process this file. Free space on the machine running AnonShield or upload a smaller file.",
        )

    ext = (Path(file.filename or "upload").suffix.lstrip(".") or "bin").lower()
    job_id = str(uuid.uuid4())
    inp = storage.input_path(job_id, ext)

    size = 0
    try:
        storage.create_job_dir(job_id)
        async with aiofiles.open(inp, "wb") as out:
            chunk_size = 256 * 1024  # 256 KB
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if limit and size > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Limit: {limit // 1024 // 1024} MB",
                    )
                await out.write(chunk)
    except HTTPException:
        storage.delete_job(job_id)
        raise
    except OSError as exc:
        storage.delete_job(job_id)
        if exc.errno in {errno.ENOSPC, errno.EDQUOT}:
            raise HTTPException(status_code=507, detail="Upload storage is full. Free disk space on the machine running AnonShield and try again.") from exc
        raise

    # Parse entities JSON array if provided
    entities_list: list[str] | None = None
    if entities:
        try:
            entities_list = json.loads(entities)
        except json.JSONDecodeError:
            entities_list = [e.strip() for e in entities.split(",") if e.strip()]
        if not isinstance(entities_list, list) or not all(isinstance(e, str) for e in entities_list):
            storage.delete_job(job_id)
            raise HTTPException(status_code=422, detail="Entities must be a list of entity type names.")

    # Parse inline YAML config if provided
    anon_config: dict = {}
    profile: dict = {}
    if config:
        result = validate_profile(config)
        if not result["valid"]:
            storage.delete_job(job_id)
            raise HTTPException(status_code=422, detail=result["error"])
        import yaml
        profile = yaml.safe_load(config) or {}
        anon_config = profile.get("anonymization_config") or {}
        if not isinstance(anon_config, dict):
            storage.delete_job(job_id)
            raise HTTPException(status_code=422, detail="The web profile's anonymization_config must contain field rules, not a file path.")
        if not strategy or strategy == "filtered":
            strategy = profile.get("strategy", strategy)
        if not lang or lang == "en":
            lang = profile.get("lang", lang)
        if entities_list is None:
            entities_list = profile.get("entities")

    from src.anon.config import NerDefaults
    from services.profile import VALID_STRATEGIES
    slug_length = slug_length if slug_length is not None else profile.get("slug_length", 8)
    ner_score_threshold = ner_score_threshold if ner_score_threshold is not None else profile.get("ner_score_threshold", NerDefaults.SCORE_THRESHOLD)
    ner_aggregation_strategy = ner_aggregation_strategy or profile.get("ner_aggregation_strategy", NerDefaults.AGGREGATION_STRATEGY)
    if strategy not in VALID_STRATEGIES or not isinstance(slug_length, int) or not 0 <= slug_length <= 64:
        storage.delete_job(job_id)
        raise HTTPException(status_code=422, detail="Choose a supported strategy and a slug_length between 0 and 64.")
    if not isinstance(ner_score_threshold, (int, float)) or not 0 <= ner_score_threshold <= 1 or ner_aggregation_strategy not in NerDefaults.AGGREGATION_CHOICES:
        storage.delete_job(job_id)
        raise HTTPException(status_code=422, detail="NER confidence must be between 0 and 1; choose a supported aggregation strategy.")

    # Handle UI-selected fields (mapping to anonymization_config)
    if fields:
        try:
            parsed_fields = json.loads(fields)
            if isinstance(parsed_fields, dict):
                # Full Anonymization Config object
                anon_config.update(parsed_fields)
            elif isinstance(parsed_fields, list):
                # Legacy / simple field list
                anon_config["fields_to_anonymize"] = parsed_fields
        except json.JSONDecodeError:
            # Fallback for comma-separated string
            anon_config["fields_to_anonymize"] = [f.strip() for f in fields.split(",") if f.strip()]

    meta = {
        "filename": file.filename,
        "ext": ext,
        "size": size,
        "strategy": strategy,
        "lang": lang,
        "model": model or profile.get("transformer_model"),
        "entities": entities_list,
        "custom_patterns": profile.get("custom_patterns"),
        "allow_list": profile.get("allow_list"),
        "preserve_entities": profile.get("preserve_entities"),
        "anonymization_config": anon_config,
        "ocr_engine": "tesseract",
        "ner_score_threshold": ner_score_threshold,
        "ner_aggregation_strategy": ner_aggregation_strategy,
        "slug_length": slug_length,
    }
    job_service.store_meta(job_id, meta)
    job_service.set_status(job_id, "queued")
    if key:
        job_service.store_key(job_id, key)

    queue = "fast"
    task_name = "workers.tasks.process_job_fast"

    from workers.celery_app import app as celery_app
    celery_app.send_task(task_name, args=[job_id], queue=queue)

    return {"job_id": job_id, "status": "queued", "queue": queue}


@router.get("/{job_id}/status")
def job_status(job_id: UUID) -> dict:
    job_id = str(job_id)
    status = job_service.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.get("/{job_id}/download")
async def download_job(job_id: UUID) -> StreamingResponse:
    job_id = str(job_id)
    status = job_service.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if status.get("status") != "done":
        raise HTTPException(status_code=409, detail="Job not ready")

    out_file = storage.get_output_file(job_id)
    if out_file is None or not out_file.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    meta = job_service.get_meta(job_id) or {}
    original_filename = meta.get('filename') or 'output'
    name_part = Path(original_filename).stem
    actual_ext = out_file.suffix
    filename = f"anon_{name_part}{actual_ext}"
    
    media_type = mimetypes.guess_type(str(out_file))[0] or "application/octet-stream"

    async def _stream_and_delete():
        async with aiofiles.open(out_file, "rb") as f:
            while chunk := await f.read(64 * 1024):
                yield chunk
        storage.delete_output(job_id)
        job_service.set_status(job_id, "downloaded")

    return StreamingResponse(
        _stream_and_delete(),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='')}",
            "X-Output-Size": str(out_file.stat().st_size),
        },
    )


@router.delete("/{job_id}", status_code=204)
def cancel_job(job_id: UUID) -> None:
    job_id = str(job_id)
    storage.delete_job(job_id)
    job_service.delete_job_keys(job_id)
