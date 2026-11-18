"""Helpers for terminating asyncio subprocesses together with their children.

``Process.kill()`` only signals the direct child. On Windows that is a real
problem: the Claude Code CLI (and FreeCAD) spawn their own child processes, so
killing only the parent on timeout leaves orphans that keep running, burning CPU
and, for the CLI, usage quota. ``kill_process_tree`` kills the whole tree.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys

logger = logging.getLogger("pilot.process")


async def kill_process_tree(
    proc: asyncio.subprocess.Process, wait_timeout: float = 10.0
) -> None:
    """Kill ``proc`` and every process it spawned, then reap it.

    Never kills anything by image name, only the tree rooted at ``proc.pid``.
    Safe to call on a process that has already exited.
    """
    if proc.returncode is not None:
        return

    if sys.platform == "win32":
        # /T walks the tree via parent PIDs, so it must run while the parent is
        # still alive, i.e. before the plain kill() below.
        try:
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/PID", str(proc.pid), "/T", "/F",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            await asyncio.wait_for(killer.wait(), timeout=wait_timeout)
        except (OSError, asyncio.TimeoutError) as exc:
            logger.warning("PROCESS_TREE_KILL_FAILED pid=%s err=%s", proc.pid, exc)

    # Fallback (and the only step on POSIX): make sure the direct child is gone.
    try:
        proc.kill()
    except ProcessLookupError:
        pass

    try:
        await asyncio.wait_for(proc.wait(), timeout=wait_timeout)
    except asyncio.TimeoutError:
        logger.warning("PROCESS_KILL_SLOW pid=%s", proc.pid)
