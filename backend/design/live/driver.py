"""Drives a visible FreeCAD GUI window for live design demos.

The headless pipeline stays the source of truth for artefacts and previews; this
module is an extra presentation layer that replays the same generated script into
a real FreeCAD window, one step at a time, so an audience can watch the solid
appear.

The in-GUI listener (``pilot_live.py``) is injected as a startup script when the
window is launched, so nothing is installed into the user's FreeCAD profile.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from backend.config import PilotConfig, get_config

logger = logging.getLogger("pilot.design.live")

HOST = "127.0.0.1"
LIVE_MODULE = Path(__file__).resolve().parent / "pilot_live.py"
TOKEN_PATH = Path(os.path.expanduser("~")) / ".pilot" / "live_token"

# Scripts are split on these markers so each feature lands as its own visible step.
_STEP_RE = re.compile(r"^[ \t]*#[ \t]*STEP:[ \t]*(.*)$", re.MULTILINE)

# Live replay runs the generated script unmodified. Rather than stripping its
# export calls -- which breaks enclosing if/for blocks and leaves invalid Python --
# the listener is told to set __file__ to a throwaway scratch path, so the script
# derives its own output dir there and never touches the real artefacts.
LIVE_SCRATCH = Path(os.path.expanduser("~")) / ".pilot" / "live_scratch"

#: Loads one exported stage solid into the live document, replacing the previous
#: stage so the part appears to grow in place.
_STAGE_CODE = """
import FreeCAD as _App
import Part as _Part

_name = "PilotPart"
if {reset} or _App.ActiveDocument is None:
    for _d in list(_App.listDocuments().keys()):
        _App.closeDocument(_d)
    _doc = _App.newDocument("PilotDesign")
else:
    _doc = _App.ActiveDocument

_sh = _Part.Shape()
_sh.read(r"{brep}")

_obj = None
for _o in _doc.Objects:
    if _o.Name == _name:
        _obj = _o
        break
if _obj is None:
    _obj = _doc.addObject("Part::Feature", _name)
_obj.Label = "{label}"
_obj.Shape = _sh
_doc.recompute()
"""


@dataclass
class LiveStep:
    """One replayable chunk of the generated script."""

    label: str
    code: str


@dataclass
class LiveSession:
    """Outcome of replaying a script into the GUI."""

    started_window: bool = False
    steps_sent: int = 0
    steps_failed: int = 0
    errors: list[str] = field(default_factory=list)
    step_labels: list[str] = field(default_factory=list)


def read_token() -> str:
    """Return the shared localhost token, creating it if absent."""
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_PATH.exists():
        tok = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    tok = secrets.token_hex(32)
    TOKEN_PATH.write_text(tok, encoding="utf-8")
    return tok


def _compiles(code: str) -> bool:
    """Return True when a chunk is valid standalone Python."""
    try:
        compile(code, "<live_step>", "exec")
        return True
    except SyntaxError:
        return False


def split_steps(script: str) -> list[LiveStep]:
    """Split a generated script into labelled steps for staged replay.

    Code before the first ``# STEP:`` marker is treated as the preamble (imports
    and document setup). Export/IO statements are dropped: the headless run owns
    the files, and re-running them from the GUI would overwrite them.
    """
    matches = list(_STEP_RE.finditer(script))
    chunks: list[LiveStep] = []

    if not matches:
        # No markers: replay the whole body as a single step.
        chunks.append(LiveStep(label="Build model", code=script))
    else:
        preamble = script[: matches[0].start()]
        if preamble.strip():
            chunks.append(LiveStep(label="Setup", code=preamble))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(script)
            body = script[m.end() : end]
            label = (m.group(1) or "").strip() or f"Step {i + 1}"
            if body.strip():
                chunks.append(LiveStep(label=label, code=body))

    cleaned = [ch for ch in chunks if ch.code.strip()]

    # A staged split is only usable if every chunk is valid standalone Python.
    # Generated scripts sometimes place a marker inside a function body or split a
    # docstring, which yields fragments that cannot execute on their own. In that
    # case fall back to one whole-script step: the window still shows the finished
    # part, just without the stage-by-stage reveal.
    if not cleaned or not all(_compiles(ch.code) for ch in cleaned):
        logger.info("LIVE_SPLIT_FALLBACK reason=chunks_not_standalone chunks=%d", len(cleaned))
        return [LiveStep(label="Build model", code=script)] if script.strip() else []
    return cleaned


def _probe(port: int, timeout: float = 1.0) -> bool:
    """Return True when something is accepting connections on the live port."""
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


def _request(port: int, payload: dict, timeout: float) -> dict:
    """Send one newline-delimited JSON request and return the response."""
    with socket.create_connection((HOST, port), timeout=timeout) as s:
        s.settimeout(timeout)
        s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    if not buf.strip():
        return {"ok": False, "error": "empty response from FreeCAD"}
    return json.loads(buf.decode("utf-8").strip())


class LiveDriver:
    """Launches and feeds a visible FreeCAD window."""

    def __init__(self, config: PilotConfig | None = None) -> None:
        self.config = config or get_config()

    @property
    def port(self) -> int:
        return int(self.config.freecad_live_port)

    def gui_binary(self) -> str | None:
        """Resolve the FreeCAD GUI executable next to the configured headless one."""
        configured = getattr(self.config, "freecad_gui_path", None)
        if configured and Path(configured).exists():
            return configured
        bindir = Path(self.config.freecad_path).parent
        for name in ("freecad.exe", "FreeCAD.exe", "freecad"):
            cand = bindir / name
            if cand.exists():
                return str(cand)
        return None

    async def ping(self) -> bool:
        """Return True when the in-GUI listener answers."""
        if not _probe(self.port):
            return False
        try:
            resp = await asyncio.to_thread(
                _request, self.port, {"token": read_token(), "op": "ping"}, 10.0
            )
            return bool(resp.get("ok"))
        except Exception as exc:
            logger.debug("LIVE_PING_FAILED error=%r", exc)
            return False

    async def ensure_window(self, wait_seconds: float = 90.0) -> bool:
        """Start the FreeCAD GUI with the listener injected, unless already up."""
        if await self.ping():
            logger.info("LIVE_WINDOW_REUSED port=%d", self.port)
            return True

        binary = self.gui_binary()
        if not binary:
            logger.error("LIVE_GUI_NOT_FOUND searched_next_to=%s", self.config.freecad_path)
            return False

        read_token()  # make sure the token exists before the GUI reads it
        env = dict(os.environ, PILOT_LIVE_PORT=str(self.port))
        logger.info("LIVE_WINDOW_LAUNCHING binary=%s module=%s", binary, LIVE_MODULE)
        subprocess.Popen(
            [binary, str(LIVE_MODULE)],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = asyncio.get_running_loop().time() + wait_seconds
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(1.5)
            if await self.ping():
                logger.info("LIVE_WINDOW_READY port=%d", self.port)
                return True
        logger.error("LIVE_WINDOW_TIMEOUT waited=%.0fs", wait_seconds)
        return False

    async def send_step(self, step: LiveStep) -> tuple[bool, str | None]:
        """Execute one step inside the GUI and report success."""
        try:
            resp = await asyncio.to_thread(
                _request,
                self.port,
                {
                    "token": read_token(),
                    "op": "exec",
                    "code": step.code,
                    "label": step.label,
                    "file_path": str(LIVE_SCRATCH / "live_run.py"),
                },
                150.0,
            )
        except Exception as exc:
            return False, repr(exc)
        return bool(resp.get("ok")), resp.get("error")

    async def replay_stages(
        self,
        job_dir: Path,
        stages: list[object],
        step_delay: float | None = None,
        on_step: object | None = None,
    ) -> LiveSession:
        """Build the part in the FreeCAD window one recorded stage at a time.

        Each stage loads the real solid the generated script exported during its
        headless run, so the window shows genuine intermediate geometry rather
        than a re-execution of the script.
        """

        session = LiveSession()
        delay = self.config.freecad_live_step_delay if step_delay is None else step_delay

        usable = [st for st in stages if getattr(st, "solid", "")]
        if not usable:
            session.errors.append("No stage geometry was exported for this design.")
            return session

        if not await self.ensure_window():
            session.errors.append("Could not start or reach the FreeCAD window.")
            return session
        session.started_window = True
        session.step_labels = [getattr(st, "label", "") for st in usable]
        logger.info("LIVE_STAGES_START count=%d delay=%.2fs", len(usable), delay)

        for i, st in enumerate(usable, 1):
            label = getattr(st, "label", f"Stage {i}")
            if callable(on_step):
                try:
                    on_step(i, len(usable), label)
                except Exception:
                    pass
            brep = (job_dir / getattr(st, "solid")).as_posix()
            first = i == 1
            code = _STAGE_CODE.format(
                brep=brep,
                label=label.replace("\\", " ").replace('"', "'"),
                reset="True" if first else "False",
            )
            ok, err = await self.send_step(LiveStep(label=label, code=code))
            session.steps_sent += 1
            if ok:
                logger.info("LIVE_STAGE_OK %d/%d label=%s", i, len(usable), label)
            else:
                session.steps_failed += 1
                session.errors.append(f"{label}: {err}")
                logger.warning("LIVE_STAGE_FAILED %d/%d label=%s error=%s", i, len(usable), label, err)
            if i < len(usable):
                await asyncio.sleep(delay)

        logger.info(
            "LIVE_STAGES_DONE sent=%d failed=%d", session.steps_sent, session.steps_failed
        )
        return session

    async def replay(
        self,
        script: str,
        step_delay: float | None = None,
        on_step: object | None = None,
    ) -> LiveSession:
        """Replay a generated script into the GUI, one visible step at a time.

        Failures are recorded but do not abort the replay: live mode is a
        presentation layer, and the headless artefacts are unaffected either way.
        """
        session = LiveSession()
        delay = self.config.freecad_live_step_delay if step_delay is None else step_delay

        LIVE_SCRATCH.mkdir(parents=True, exist_ok=True)
        if not await self.ensure_window():
            session.errors.append("Could not start or reach the FreeCAD window.")
            return session
        session.started_window = True

        steps = split_steps(script)
        session.step_labels = [s.label for s in steps]
        logger.info("LIVE_REPLAY_START steps=%d delay=%.2fs", len(steps), delay)

        for i, step in enumerate(steps, 1):
            if callable(on_step):
                try:
                    on_step(i, len(steps), step.label)
                except Exception:
                    pass
            ok, err = await self.send_step(step)
            session.steps_sent += 1
            if ok:
                logger.info("LIVE_STEP_OK %d/%d label=%s", i, len(steps), step.label)
            else:
                session.steps_failed += 1
                session.errors.append(f"{step.label}: {err}")
                logger.warning("LIVE_STEP_FAILED %d/%d label=%s error=%s", i, len(steps), step.label, err)
            if i < len(steps):
                await asyncio.sleep(delay)

        logger.info(
            "LIVE_REPLAY_DONE sent=%d failed=%d", session.steps_sent, session.steps_failed
        )
        return session


_driver: LiveDriver | None = None


def get_live_driver() -> LiveDriver:
    """Return the process-wide live driver."""
    global _driver
    if _driver is None:
        _driver = LiveDriver()
    return _driver
