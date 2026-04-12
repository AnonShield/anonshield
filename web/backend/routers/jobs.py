"""Job endpoints — create, status, download."""
import json
import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from services import job_service, storage
from services.profile import validate_profile

from services.limiter import limiter

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Limits are configurable via env vars (values in MB)
# ANON_MAX_SIZE_MB      — without key (default: 1 MB)
# ANON_MAX_SIZE_KEY_MB  — with key     (default: 1 MB)
LIMIT_NO_KEY  = int(os.getenv("ANON_MAX_SIZE_MB",     "1"))  * 1024 * 1024
LIMIT_WITH_KEY = int(os.getenv("ANON_MAX_SIZE_KEY_MB", "1")) * 1024 * 1024

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
    ocr_engine: Annotated[str, Form()] = "tesseract",
    fields: Annotated[str, Form()] = "",
) -> dict:
    limit = LIMIT_WITH_KEY if key else LIMIT_NO_KEY

    # Refuse if disk free space < 3× the upload limit (safety margin for output + ZIP)
    disk = shutil.disk_usage(storage.JOBS_ROOT.parent if storage.JOBS_ROOT.exists() else "/tmp")
    if disk.free < limit * 3:
        raise HTTPException(
            status_code=507,
            detail="Insufficient storage. Try again later or use a smaller file.",
        )

    ext = (Path(file.filename or "upload").suffix.lstrip(".") or "bin").lower()
    job_id = str(uuid.uuid4())
    storage.create_job_dir(job_id)
    inp = storage.input_path(job_id, ext)

    size = 0
    try:
        async with aiofiles.open(inp, "wb") as out:
            chunk_size = 256 * 1024  # 256 KB
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Limit: {limit // 1024 // 1024} MB",
                    )
                await out.write(chunk)
    except HTTPException:
        storage.delete_job(job_id)
        raise

    # Parse entities JSON array if provided
    entities_list: list[str] = []
    if entities:
        try:
            entities_list = json.loads(entities)
        except json.JSONDecodeError:
            entities_list = [e.strip() for e in entities.split(",") if e.strip()]

    # Parse inline YAML config if provided
    anon_config: dict = {}
    if config:
        result = validate_profile(config)
        if not result["valid"]:
            storage.delete_job(job_id)
            raise HTTPException(status_code=422, detail=result["error"])
        import yaml
        anon_config = yaml.safe_load(config) or {}
        if not strategy or strategy == "filtered":
            strategy = anon_config.get("strategy", strategy)
        if not lang or lang == "en":
            lang = anon_config.get("lang", lang)
        if not entities_list:
            entities_list = anon_config.get("entities", [])

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
        "entities": entities_list,
        "anonymization_config": anon_config,
        "ocr_engine": ocr_engine or "tesseract",
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
def job_status(job_id: str) -> dict:
    status = job_service.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@router.get("/{job_id}/download")
async def download_job(job_id: str) -> StreamingResponse:
    status = job_service.get_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if status.get("status") != "done":
        raise HTTPException(status_code=409, detail="Job not ready")

    out_file = storage.get_output_file(job_id)
    if out_file is None or not out_file.exists():
        raise HTTPException(status_code=404, detail="Output file not found")

    meta = job_service.get_meta(job_id) or {}
    original_filename = meta.get('filename', 'output')
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
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Output-Size": str(out_file.stat().st_size),
        },
    )


@router.delete("/{job_id}", status_code=204)
def cancel_job(job_id: str) -> None:
    storage.delete_job(job_id)
    job_service.delete_job_keys(job_id)
