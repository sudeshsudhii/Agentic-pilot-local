"""Collects the construction stages a generated design script recorded.

The script calls the supplied ``_pilot_snapshot`` helper after each construction
stage, which writes ``step_NN.svg`` plus a ``steps.json`` manifest into the job
directory during the single headless run. This module only reads that manifest,
so no extra FreeCAD work is needed and every frame is a real solid FreeCAD
computed mid-build.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("pilot.design.steps")

MANIFEST_NAME = "steps.json"

#: Ceiling on stages surfaced to the UI, so a very long build stays watchable.
MAX_STEPS = 12


@dataclass(frozen=True)
class DesignStep:
    """One recorded construction stage."""

    index: int
    label: str
    filename: str
    solid: str = ""


def collect_steps(job_dir: Path) -> list[DesignStep]:
    """Return the construction stages recorded for a finished job, in build order.

    Falls back to globbing ``step_*.svg`` when the manifest is missing or
    unreadable, so stages still surface if only the frames were written. Returns
    an empty list when the script recorded none.
    """

    manifest = job_dir / MANIFEST_NAME
    entries: list[DesignStep] = []

    if manifest.is_file():
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
            for item in raw if isinstance(raw, list) else []:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("file") or "")
                svg = job_dir / name
                # Only trust a plain basename that really exists in this job's dir.
                if not name or name != Path(name).name or not svg.is_file():
                    continue
                if svg.stat().st_size <= 0:
                    continue
                solid = str(item.get("solid") or "")
                if solid and (solid != Path(solid).name or not (job_dir / solid).is_file()):
                    solid = ""
                entries.append(
                    DesignStep(
                        index=int(item.get("index") or len(entries) + 1),
                        label=str(item.get("label") or f"Stage {len(entries) + 1}"),
                        filename=name,
                        solid=solid,
                    )
                )
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("DESIGN_STEPS_MANIFEST_BAD dir=%s error=%r", job_dir, exc)

    if not entries:
        for i, svg in enumerate(sorted(job_dir.glob("step_*.svg")), 1):
            if svg.is_file() and svg.stat().st_size > 0:
                entries.append(DesignStep(index=i, label=f"Stage {i}", filename=svg.name))

    entries.sort(key=lambda s: s.index)
    if len(entries) > MAX_STEPS:
        # Keep the first and last stage; sample the middle evenly.
        keep = {round(i * (len(entries) - 1) / (MAX_STEPS - 1)) for i in range(MAX_STEPS)}
        entries = [s for i, s in enumerate(entries) if i in keep]

    logger.info("DESIGN_STEPS_COLLECTED dir=%s count=%d", job_dir.name, len(entries))
    return entries
