"""Request and response schemas for the prompt-to-CAD design API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

#: The five statuses a design job may report, in lifecycle order.
DesignStatus = Literal["queued", "generating", "running", "succeeded", "failed"]


class DesignGenerateRequest(BaseModel):
    """Request body for starting a design job."""

    prompt: str = Field(min_length=1, description="Natural-language description of the part")
    live: bool = Field(
        default=False,
        description="Also replay the build in a visible FreeCAD window, step by step",
    )


class DesignGenerateResponse(BaseModel):
    """Immediate acknowledgement returned when a design job is accepted."""

    job_id: str
    status: DesignStatus


class DesignFile(BaseModel):
    """One downloadable artefact produced by a design job."""

    name: str
    kind: str
    size_bytes: int
    url: str


class DesignStepInfo(BaseModel):
    """One captured construction stage of a design job."""

    index: int
    label: str
    preview_url: str


class DesignJobResponse(BaseModel):
    """Full design job state."""

    job_id: str
    status: DesignStatus
    prompt: str
    error: str | None = None
    created_at: str
    duration_ms: int
    metrics: dict[str, Any] | None = None
    script: str | None = None
    preview_url: str | None = None
    files: list[DesignFile] = Field(default_factory=list)
    steps: list[DesignStepInfo] = Field(default_factory=list)
    live: bool = False
    live_status: str | None = None
    live_step: str | None = None
    live_step_index: int = 0
    live_step_total: int = 0


class DesignJobListResponse(BaseModel):
    """Recent design jobs, newest first."""

    jobs: list[DesignJobResponse] = Field(default_factory=list)
