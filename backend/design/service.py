"""Design job orchestration: prompt -> Claude -> headless FreeCAD -> CAD artefacts.

Jobs live in an in-memory registry keyed by uuid4. Each job owns an isolated output
directory ``<design_output_dir>/<job_id>/`` that holds the generated script and every
artefact it produces; the prompt never influences any path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import time
import uuid

from backend.config import PilotConfig, get_config
from backend.design.freecad_runner import (
    EXPECTED_ARTIFACTS,
    FreeCADRunResult,
    artifact_kind_for,
    run_freecad_script,
)
from backend.design.models import DesignFile, DesignJobResponse, DesignStatus, DesignStepInfo
from backend.design import prompts

logger = logging.getLogger("pilot.design")

#: Maximum jobs returned by the list endpoint.
MAX_LISTED_JOBS = 20

#: Name of the generated script inside each job directory.
SCRIPT_NAME = "model_script.py"

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_+-]*\s*\n(.*?)\n?\s*```\s*$", re.DOTALL)


def strip_code_fences(text: str) -> str:
    """Return ``text`` with a surrounding Markdown code fence removed.

    Handles a fully fenced response, a response with prose around one fenced block,
    and an unterminated opening fence.
    """

    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    match = _FENCE_RE.match(cleaned)
    if match:
        return match.group(1).strip("\n")

    # Prose around a fenced block: take the largest fenced block present.
    blocks = re.findall(r"```[a-zA-Z0-9_+-]*\s*\n(.*?)```", cleaned, re.DOTALL)
    if blocks:
        return max(blocks, key=len).strip("\n")

    # Unterminated opening fence.
    lines = cleaned.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
        while lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip("\n")

    return cleaned


@dataclass(slots=True)
class DesignJob:
    """Mutable in-memory state of one design job."""

    job_id: str
    prompt: str
    job_dir: Path
    status: DesignStatus = "queued"
    error: str | None = None
    created_at: str = ""
    started_monotonic: float = 0.0
    duration_ms: int = 0
    metrics: dict[str, object] | None = None
    script: str | None = None
    attempts: int = 0
    artifacts: list[str] = field(default_factory=list)
    steps: list[object] = field(default_factory=list)
    live: bool = False
    live_status: str | None = None
    live_step: str | None = None
    live_step_index: int = 0
    live_step_total: int = 0

    def mark_done(self, status: DesignStatus, error: str | None = None) -> None:
        """Freeze the job duration and record its terminal status."""

        self.status = status
        self.error = error
        self.duration_ms = int((time.perf_counter() - self.started_monotonic) * 1000)

    def elapsed_ms(self) -> int:
        """Return the frozen duration when finished, else the live elapsed time."""

        if self.status in ("succeeded", "failed"):
            return self.duration_ms
        return int((time.perf_counter() - self.started_monotonic) * 1000)

    def to_response(self, include_script: bool = True) -> DesignJobResponse:
        """Render the job into its public API representation."""

        files: list[DesignFile] = []
        preview_url: str | None = None
        for name in self.artifacts:
            path = self.job_dir / name
            if not path.exists():
                continue
            url = "/api/design/jobs/" + self.job_id + "/files/" + name
            files.append(
                DesignFile(
                    name=name,
                    kind=artifact_kind_for(name),
                    size_bytes=path.stat().st_size,
                    url=url,
                )
            )
            if name == "preview.svg":
                preview_url = url
        return DesignJobResponse(
            job_id=self.job_id,
            status=self.status,
            prompt=self.prompt,
            error=self.error,
            created_at=self.created_at,
            duration_ms=self.elapsed_ms(),
            metrics=self.metrics,
            script=self.script if include_script else None,
            preview_url=preview_url,
            files=files,
            steps=[
                DesignStepInfo(
                    index=s.index,
                    label=s.label,
                    preview_url="/api/design/jobs/" + self.job_id + "/files/" + s.filename,
                )
                for s in self.steps
            ],
            live=self.live,
            live_status=self.live_status,
            live_step=self.live_step,
            live_step_index=self.live_step_index,
            live_step_total=self.live_step_total,
        )


class DesignService:
    """Creates, runs and tracks prompt-to-CAD design jobs."""

    def __init__(self, config: PilotConfig | None = None) -> None:
        """Create the service and ensure the design output root exists."""

        self.config = config or get_config()
        self.root = Path(self.config.design_output_dir).expanduser()
        self.root.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, DesignJob] = {}
        self._order: list[str] = []

    def create_job(self, prompt: str, live: bool = False) -> DesignJob:
        """Register a queued job with its own isolated output directory."""

        job_id = str(uuid.uuid4())
        job_dir = self.root / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        job = DesignJob(
            job_id=job_id,
            prompt=prompt,
            live=live,
            job_dir=job_dir,
            created_at=datetime.now(timezone.utc).isoformat(),
            started_monotonic=time.perf_counter(),
        )
        self._jobs[job_id] = job
        self._order.append(job_id)
        logger.info("DESIGN_JOB_QUEUED job_id=%s prompt_chars=%d live=%s", job_id, len(prompt), live)
        return job

    def get_job(self, job_id: str) -> DesignJob | None:
        """Return a job by id, or None when unknown."""

        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = MAX_LISTED_JOBS) -> list[DesignJob]:
        """Return the most recent jobs, newest first."""

        recent = list(reversed(self._order))[:limit]
        return [self._jobs[job_id] for job_id in recent if job_id in self._jobs]

    async def run_job(self, job_id: str) -> None:
        """Drive one design job to a terminal state, retrying a failed script once."""

        job = self._jobs.get(job_id)
        if job is None:
            logger.warning("DESIGN_JOB_MISSING job_id=%s", job_id)
            return

        try:
            await self._execute(job)
        except Exception as exc:  # noqa: BLE001 - a background job must never escape
            logger.exception("DESIGN_JOB_CRASHED job_id=%s", job.job_id)
            job.mark_done("failed", str(exc) or type(exc).__name__)

        if job.status == "succeeded" and job.script:
            await self._capture_steps(job)

        if job.status == "succeeded" and job.steps and self.config.freecad_live_enabled:
            await self._show_in_freecad(job)

    async def _capture_steps(self, job: DesignJob) -> None:
        """Render each construction stage so the UI can play the build back.

        Purely presentational: a failure here leaves the finished job untouched.
        """

        from backend.design.steps import collect_steps

        try:
            captured = collect_steps(job.job_dir)
            job.steps = list(captured)
            for step in captured:
                if step.filename not in job.artifacts:
                    job.artifacts.append(step.filename)
            logger.info("DESIGN_STEPS_ATTACHED job_id=%s count=%d", job.job_id, len(captured))
        except Exception as exc:  # noqa: BLE001 - stages must never fail a finished job
            logger.exception("DESIGN_STEPS_CRASHED job_id=%s error=%r", job.job_id, exc)

    async def _show_in_freecad(self, job: DesignJob) -> None:
        """Build the finished part in a visible FreeCAD window, stage by stage.

        Presentational: the artefacts are already final, so any failure here is
        recorded on the job without changing its terminal status.
        """

        from backend.design.live import get_live_driver

        def _progress(index: int, total: int, label: str) -> None:
            job.live_step_index, job.live_step_total, job.live_step = index, total, label

        job.live = True
        job.live_status = "starting"
        try:
            driver = get_live_driver()
            session = await driver.replay_stages(job.job_dir, job.steps, on_step=_progress)
            if not session.started_window:
                job.live_status = "unavailable"
            elif session.steps_failed:
                job.live_status = "partial"
            else:
                job.live_status = "shown"
            if session.errors:
                logger.warning("DESIGN_LIVE_ISSUES job_id=%s errors=%s", job.job_id, session.errors[:3])
            logger.info(
                "DESIGN_LIVE_DONE job_id=%s status=%s sent=%d failed=%d",
                job.job_id, job.live_status, session.steps_sent, session.steps_failed,
            )
        except Exception as exc:  # noqa: BLE001 - never fail a finished job
            job.live_status = "unavailable"
            logger.exception("DESIGN_LIVE_CRASHED job_id=%s error=%r", job.job_id, exc)

    async def _replay_live(self, job: DesignJob) -> None:
        """Replay a succeeded job into a visible FreeCAD window.

        Presentation only: the headless artefacts are already final, so any live
        failure is recorded on the job without changing its terminal status.
        """

        from backend.design.live import get_live_driver

        def _progress(index: int, total: int, label: str) -> None:
            job.live_step_index, job.live_step_total, job.live_step = index, total, label

        job.live_status = "starting"
        try:
            driver = get_live_driver()
            session = await driver.replay(job.script or "", on_step=_progress)
            if not session.started_window:
                job.live_status = "unavailable"
            elif session.steps_failed:
                job.live_status = "partial"
            else:
                job.live_status = "shown"
            if session.errors:
                job.live_step = None
                logger.warning("DESIGN_LIVE_ISSUES job_id=%s errors=%s", job.job_id, session.errors[:3])
            logger.info(
                "DESIGN_LIVE_DONE job_id=%s status=%s sent=%d failed=%d",
                job.job_id, job.live_status, session.steps_sent, session.steps_failed,
            )
        except Exception as exc:  # noqa: BLE001 - live mode must never fail the job
            job.live_status = "unavailable"
            logger.exception("DESIGN_LIVE_CRASHED job_id=%s error=%r", job.job_id, exc)

    async def _repair_syntax(
        self, job: DesignJob, gateway: object, script: str
    ) -> str | None:
        """Return a syntactically valid script, asking Claude to fix one if needed.

        Returns None when the job has been failed outright.
        """

        try:
            compile(script, "model_script.py", "exec")
            return script
        except SyntaxError as exc:
            detail = f"{type(exc).__name__}: {exc.msg} (line {exc.lineno})"
            logger.warning(
                "DESIGN_JOB_SYNTAX_INVALID job_id=%s %s", job.job_id, detail
            )

        repaired_raw = await gateway.complete(  # type: ignore[attr-defined]
            system=prompts.SYSTEM_PROMPT,
            user=prompts.build_repair_prompt(
                job.prompt,
                script,
                f"The script is not valid Python and was never executed. {detail}. "
                "Return the corrected complete script.",
            ),
            json_mode=False,
        )
        repaired = strip_code_fences(repaired_raw)
        if not repaired:
            job.mark_done("failed", f"Claude returned an invalid script ({detail})")
            return None
        try:
            compile(repaired, "model_script.py", "exec")
        except SyntaxError as exc:
            job.mark_done(
                "failed",
                f"Claude returned an invalid script twice ({detail}; then "
                f"{type(exc).__name__}: {exc.msg} line {exc.lineno})",
            )
            return None
        job.attempts += 1
        logger.info("DESIGN_JOB_SYNTAX_REPAIRED job_id=%s", job.job_id)
        return repaired

    async def _execute(self, job: DesignJob) -> None:
        """Generate, run and - on failure - repair and re-run the design script."""

        from backend.llm.gateway import get_llm_provider

        gateway = get_llm_provider(self.config)
        script_path = job.job_dir / SCRIPT_NAME

        job.status = "generating"
        logger.info("DESIGN_JOB_GENERATING job_id=%s provider=%s", job.job_id, gateway.provider_name)
        started = time.perf_counter()
        raw = await gateway.complete(
            system=prompts.SYSTEM_PROMPT,
            user=prompts.build_user_prompt(job.prompt),
            json_mode=False,
        )
        script = strip_code_fences(raw)
        logger.info(
            "DESIGN_JOB_GENERATED job_id=%s script_chars=%d llm_ms=%d",
            job.job_id,
            len(script),
            int((time.perf_counter() - started) * 1000),
        )
        if not script:
            job.mark_done("failed", "Claude returned an empty script")
            return

        job.script = script

        # Syntax-check before spending a FreeCAD run. A malformed script is a
        # common first-shot failure (orphaned `return`, unterminated string), and
        # the compiler names the exact line, which repairs far more reliably than
        # a FreeCAD traceback.
        script = await self._repair_syntax(job, gateway, script)
        if script is None:
            return
        job.script = script
        script_path.write_text(script, encoding="utf-8")

        result = await self._run_once(job, script_path)
        if result.ok:
            self._finish_success(job, result)
            return

        # One repair round-trip: the first-shot script often has a small API mistake.
        logger.warning(
            "DESIGN_JOB_RUN_FAILED job_id=%s attempt=%d error=%s",
            job.job_id,
            job.attempts,
            result.error,
        )
        job.status = "generating"
        started = time.perf_counter()
        raw_fix = await gateway.complete(
            system=prompts.SYSTEM_PROMPT,
            user=prompts.build_repair_prompt(job.prompt, script, result.failure_report()),
            json_mode=False,
        )
        repaired = strip_code_fences(raw_fix)
        logger.info(
            "DESIGN_JOB_REPAIRED job_id=%s script_chars=%d llm_ms=%d",
            job.job_id,
            len(repaired),
            int((time.perf_counter() - started) * 1000),
        )
        if not repaired:
            job.mark_done("failed", "Repair attempt returned an empty script. " + (result.error or ""))
            return

        job.script = repaired
        script_path.write_text(repaired, encoding="utf-8")
        retry = await self._run_once(job, script_path)
        if retry.ok:
            self._finish_success(job, retry)
            return

        job.metrics = retry.metrics or result.metrics
        job.mark_done(
            "failed",
            "FreeCAD run failed after one repair attempt. "
            + (retry.error or "unknown error")
            + _stderr_hint(retry),
        )
        logger.error(
            "DESIGN_JOB_FAILED job_id=%s attempts=%d error=%s", job.job_id, job.attempts, job.error
        )

    async def _run_once(self, job: DesignJob, script_path: Path) -> FreeCADRunResult:
        """Run the current script under headless FreeCAD and log the outcome."""

        job.attempts += 1
        job.status = "running"
        logger.info("DESIGN_JOB_RUNNING job_id=%s attempt=%d", job.job_id, job.attempts)
        result = await run_freecad_script(script_path, job.job_dir, self.config)
        logger.info(
            "DESIGN_JOB_RUN_DONE job_id=%s attempt=%d ok=%s timed_out=%s freecad_ms=%d",
            job.job_id,
            job.attempts,
            result.ok,
            result.timed_out,
            result.duration_ms,
        )
        return result

    def _finish_success(self, job: DesignJob, result: FreeCADRunResult) -> None:
        """Record metrics and artefacts for a successful run."""

        job.metrics = result.metrics
        job.artifacts = [name for name in EXPECTED_ARTIFACTS if (job.job_dir / name).exists()]
        job.mark_done("succeeded")
        logger.info(
            "DESIGN_JOB_SUCCEEDED job_id=%s attempts=%d duration_ms=%d files=%s metrics=%s",
            job.job_id,
            job.attempts,
            job.duration_ms,
            ",".join(job.artifacts),
            job.metrics,
        )


def _stderr_hint(result: FreeCADRunResult) -> str:
    """Return a short parenthetical with the last stderr line, when there is one."""

    lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
    if not lines:
        return ""
    return " (" + lines[-1][:300] + ")"


_service: DesignService | None = None


def get_design_service() -> DesignService:
    """Return the process-wide design service, creating it on first use."""

    global _service
    if _service is None:
        _service = DesignService()
    return _service
