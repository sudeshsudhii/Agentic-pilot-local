"""Prompt-to-CAD design API routes.

A prompt is handed to Claude, which writes a FreeCAD Python script; the script runs
headless and its CAD artefacts plus an SVG preview are served back per job.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from backend.design.freecad_runner import content_type_for
from backend.design.models import (
    DesignGenerateRequest,
    DesignGenerateResponse,
    DesignJobListResponse,
    DesignJobResponse,
)
from backend.design.service import MAX_LISTED_JOBS, get_design_service

logger = logging.getLogger("pilot.design")

router = APIRouter(prefix="/api/design", tags=["design"])


@router.post("/generate", response_model=DesignGenerateResponse, status_code=202)
async def generate_design(
    request_body: DesignGenerateRequest,
    background_tasks: BackgroundTasks,
) -> DesignGenerateResponse:
    """Accept a design prompt and run the CAD generation in the background."""

    service = get_design_service()
    job = service.create_job(request_body.prompt, live=request_body.live)
    background_tasks.add_task(service.run_job, job.job_id)
    return DesignGenerateResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs", response_model=DesignJobListResponse)
async def list_design_jobs() -> DesignJobListResponse:
    """Return the most recent design jobs, newest first, without their scripts."""

    service = get_design_service()
    jobs = service.list_jobs(MAX_LISTED_JOBS)
    return DesignJobListResponse(jobs=[job.to_response(include_script=False) for job in jobs])


@router.get("/jobs/{job_id}", response_model=DesignJobResponse)
async def get_design_job(job_id: str) -> DesignJobResponse:
    """Return one design job including the script Claude wrote."""

    job = get_design_service().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Design job not found")
    return job.to_response(include_script=True)


@router.get("/jobs/{job_id}/files/{filename}")
async def get_design_file(job_id: str, filename: str) -> FileResponse:
    """Serve one artefact from a job's own output directory.

    Only a bare basename that already exists in that directory is served; any path
    separator, parent reference or absolute path is rejected with 400.
    """

    job = get_design_service().get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Design job not found")

    if (
        not filename
        or "/" in filename
        or "\\" in filename
        or filename in (".", "..")
        or ".." in filename
        or filename != Path(filename).name
        or Path(filename).is_absolute()
        or (len(filename) > 1 and filename[1] == ":")
    ):
        logger.warning(
            "DESIGN_FILE_REJECTED job_id=%s filename=%r reason=unsafe_name", job_id, filename
        )
        raise HTTPException(status_code=400, detail="Invalid filename")

    job_dir = job.job_dir.resolve()
    target = (job_dir / filename).resolve()
    if target.parent != job_dir:
        logger.warning(
            "DESIGN_FILE_REJECTED job_id=%s filename=%r reason=escapes_job_dir", job_id, filename
        )
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    inline = target.suffix.lower() == ".svg"
    return FileResponse(
        path=str(target),
        media_type=content_type_for(filename),
        filename=filename,
        content_disposition_type="inline" if inline else "attachment",
    )
