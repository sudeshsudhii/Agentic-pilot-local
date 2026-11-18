"""Regression tests for the design pipeline's syntax pre-check.

A FreeCAD run was wasted whenever Claude's first-shot script had a syntax
error (e.g. an orphaned `return` outside a function) -- the broken script ran
headless, failed with an opaque FreeCAD traceback, and only then triggered a
repair attempt using that traceback as the error signal. `_repair_syntax`
catches this with `compile()` before any FreeCAD process starts, so Claude is
asked to fix a precise "SyntaxError: ... (line N)" message instead.
"""

from __future__ import annotations

import pytest

from backend.design.service import get_design_service


class _FakeGateway:
    """A minimal LLM gateway stand-in: no network, no subprocess."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def complete(self, system: str, user: str, json_mode: bool = False) -> str:
        self.calls += 1
        assert "line" in user.lower() or "syntax" in user.lower()
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_a_valid_script_passes_through_without_calling_the_gateway():
    svc = get_design_service()
    job = svc.create_job("valid script probe")
    gateway = _FakeGateway([])

    result = await svc._repair_syntax(job, gateway, "x = 1\n")

    assert result == "x = 1\n"
    assert gateway.calls == 0


@pytest.mark.asyncio
async def test_repairs_the_exact_orphaned_return_bug():
    """The bug: a script with `return` outside a function was never caught before running FreeCAD."""
    svc = get_design_service()
    job = svc.create_job("return-outside-function probe")
    broken = "import FreeCAD as App\nshape = None\nreturn shape\n"
    gateway = _FakeGateway(["import os\nshape = 1\nprint('PILOT_OK')\n"])

    result = await svc._repair_syntax(job, gateway, broken)

    assert result is not None
    compile(result, "repaired.py", "exec")  # must not raise
    assert gateway.calls == 1
    assert job.status != "failed"


@pytest.mark.asyncio
async def test_fails_the_job_cleanly_when_the_repair_is_also_invalid():
    svc = get_design_service()
    job = svc.create_job("double-failure probe")
    gateway = _FakeGateway(["still not valid python (((\n"])

    result = await svc._repair_syntax(job, gateway, "return shape\n")

    assert result is None
    assert job.status == "failed"
    assert "invalid script twice" in (job.error or "")
