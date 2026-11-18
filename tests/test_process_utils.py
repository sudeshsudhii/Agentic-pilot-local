"""kill_process_tree must also kill grandchildren, not just the direct child."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

import pytest

from backend.process_utils import kill_process_tree

# Parent spawns a long-sleeping grandchild, records its PID, then sleeps too.
_PARENT_CODE = r"""
import subprocess, sys, time
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
open(sys.argv[1], "w").write(str(child.pid))
time.sleep(120)
"""


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True,
        ).stdout
        return str(pid) in out
    try:
        import os
        os.kill(pid, 0)
    except OSError:
        return False
    return True


@pytest.mark.skipif(sys.platform != "win32", reason="tree kill via taskkill is Windows-only")
def test_kill_process_tree_kills_grandchild(tmp_path: Path) -> None:
    pid_file = tmp_path / "grandchild.pid"

    async def scenario() -> int:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-c", _PARENT_CODE, str(pid_file)
        )
        deadline = time.monotonic() + 15
        while not (pid_file.exists() and pid_file.read_text()):
            assert time.monotonic() < deadline, "grandchild never started"
            await asyncio.sleep(0.1)
        grandchild = int(pid_file.read_text())
        assert _pid_alive(grandchild)

        await kill_process_tree(proc)
        assert proc.returncode is not None
        return grandchild

    grandchild_pid = asyncio.run(scenario())
    time.sleep(0.5)
    assert not _pid_alive(grandchild_pid), "grandchild was orphaned"


def test_kill_process_tree_noop_on_exited_process() -> None:
    async def scenario() -> None:
        proc = await asyncio.create_subprocess_exec(sys.executable, "-c", "pass")
        await proc.wait()
        await kill_process_tree(proc)  # must not raise

    asyncio.run(scenario())
