"""Headless FreeCAD subprocess runner for generated design scripts.

``freecadcmd.exe`` exits with code 0 even when the script raises, and it floods stdout
with STEP transfer statistics and save-progress percentages. Success is therefore
determined solely by the sentinel markers the generated script prints.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import time
from xml.etree import ElementTree

from backend.config import PilotConfig, get_config
from backend.design.prompts import (
    SENTINEL_METRICS_BEGIN,
    SENTINEL_METRICS_END,
    SENTINEL_OK,
)
from backend.process_utils import kill_process_tree

logger = logging.getLogger("pilot.design")

#: Artefacts the generated script is contracted to produce.
EXPECTED_ARTIFACTS: tuple[str, ...] = ("model.FCStd", "model.step", "model.stl", "preview.svg")

#: Content types served for each artefact extension.
CONTENT_TYPES: dict[str, str] = {
    ".svg": "image/svg+xml",
    ".step": "model/step",
    ".stp": "model/step",
    ".stl": "model/stl",
    ".fcstd": "application/octet-stream",
}

#: Logical artefact kind reported to the frontend per extension.
ARTIFACT_KINDS: dict[str, str] = {
    ".svg": "svg",
    ".step": "step",
    ".stp": "step",
    ".stl": "stl",
    ".fcstd": "fcstd",
}


@dataclass(slots=True)
class FreeCADRunResult:
    """Outcome of one headless FreeCAD script execution."""

    ok: bool
    returncode: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool = False
    metrics: dict[str, object] | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)

    def failure_report(self) -> str:
        """Return a compact failure description suitable for a repair prompt."""

        parts: list[str] = []
        if self.error:
            parts.append("FAILURE: " + self.error)
        if self.stderr.strip():
            parts.append("--- stderr ---\n" + _tail(self.stderr, 4000))
        if self.stdout.strip():
            parts.append("--- stdout (tail) ---\n" + _tail(self.stdout, 2000))
        return "\n\n".join(parts) or "The script produced no output at all."


def _tail(text: str, limit: int) -> str:
    """Return at most the last ``limit`` characters of ``text``."""

    text = text.strip()
    if len(text) <= limit:
        return text
    return "...(truncated)...\n" + text[-limit:]


def content_type_for(filename: str) -> str:
    """Return the HTTP content type for a design artefact filename."""

    return CONTENT_TYPES.get(Path(filename).suffix.lower(), "application/octet-stream")


def artifact_kind_for(filename: str) -> str:
    """Return the logical artefact kind for a design artefact filename."""

    return ARTIFACT_KINDS.get(Path(filename).suffix.lower(), "other")


def _parse_metrics(stdout: str) -> dict[str, object] | None:
    """Extract the metrics JSON printed between the metrics sentinels."""

    start = stdout.find(SENTINEL_METRICS_BEGIN)
    if start == -1:
        return None
    end = stdout.find(SENTINEL_METRICS_END, start)
    if end == -1:
        return None
    blob = stdout[start + len(SENTINEL_METRICS_BEGIN) : end].strip()
    for line in blob.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def validate_preview_svg(path: Path) -> str | None:
    """Return an error string when ``path`` is not a usable standalone SVG, else None."""

    if not path.exists():
        return "preview.svg was not written"
    if path.stat().st_size == 0:
        return "preview.svg is empty"
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        return "preview.svg is not valid XML: " + str(exc)
    tag = root.tag.rsplit("}", 1)[-1]
    if tag != "svg":
        return "preview.svg root element is <" + tag + ">, expected <svg>"
    if not root.get("viewBox"):
        return "preview.svg has no viewBox attribute"
    return None


async def run_freecad_script(
    script_path: Path,
    job_dir: Path,
    config: PilotConfig | None = None,
) -> FreeCADRunResult:
    """Execute ``script_path`` under headless FreeCAD and verify the artefacts.

    The subprocess is killed when it exceeds ``freecad_timeout_seconds``.
    """

    cfg = config or get_config()
    binary = Path(cfg.freecad_path).expanduser()
    started = time.perf_counter()

    if not binary.exists():
        return FreeCADRunResult(
            ok=False,
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=0,
            error="FreeCAD executable was not found at " + str(binary),
        )

    try:
        process = await asyncio.create_subprocess_exec(
            str(binary),
            str(script_path),
            cwd=str(job_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except OSError as exc:
        return FreeCADRunResult(
            ok=False,
            returncode=None,
            stdout="",
            stderr="",
            duration_ms=int((time.perf_counter() - started) * 1000),
            error="Could not launch FreeCAD: " + str(exc),
        )

    timed_out = False
    try:
        raw_out, raw_err = await asyncio.wait_for(
            process.communicate(), timeout=cfg.freecad_timeout_seconds
        )
    except asyncio.TimeoutError:
        timed_out = True
        raw_out, raw_err = b"", b""
        await kill_process_tree(process)

    duration_ms = int((time.perf_counter() - started) * 1000)
    stdout = raw_out.decode("utf-8", errors="replace")
    stderr = raw_err.decode("utf-8", errors="replace")

    if timed_out:
        return FreeCADRunResult(
            ok=False,
            returncode=None,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            timed_out=True,
            error=(
                "FreeCAD run exceeded the "
                + str(cfg.freecad_timeout_seconds)
                + "s timeout and was killed"
            ),
        )

    metrics = _parse_metrics(stdout)

    if SENTINEL_OK not in stdout:
        return FreeCADRunResult(
            ok=False,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            metrics=metrics,
            error="The script did not reach completion (sentinel " + SENTINEL_OK + " missing)",
        )

    missing = [
        name
        for name in EXPECTED_ARTIFACTS
        if not (job_dir / name).exists() or (job_dir / name).stat().st_size == 0
    ]
    if missing:
        return FreeCADRunResult(
            ok=False,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            metrics=metrics,
            error="Missing or empty output files: " + ", ".join(missing),
        )

    svg_error = validate_preview_svg(job_dir / "preview.svg")
    if svg_error:
        return FreeCADRunResult(
            ok=False,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            metrics=metrics,
            error=svg_error,
        )

    return FreeCADRunResult(
        ok=True,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
        metrics=metrics,
        artifacts=list(EXPECTED_ARTIFACTS),
    )
