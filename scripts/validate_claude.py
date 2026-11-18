"""Validate the Anthropic Claude provider end-to-end.

Exercises the three paths the agent actually depends on -- health probe, text
completion, and schema-constrained structured output -- against the live API.

Usage:
    python scripts/validate_claude.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Force the Claude provider for this probe regardless of the .env setting, so the
# script can validate Claude without the operator having to switch providers first.
os.environ["LLM_PROVIDER"] = "claude"

from pydantic import BaseModel, Field  # noqa: E402

from backend.config import get_config  # noqa: E402
from backend.llm.base import MissingAnthropicApiKeyError  # noqa: E402
from backend.llm.claude import ClaudeGateway  # noqa: E402


class _Plan(BaseModel):
    """Minimal planning schema mirroring the agent's structured-output usage."""

    intent: str = Field(description="One-line restatement of the goal")
    steps: list[str] = Field(description="Ordered actions to take")
    requires_browser: bool = Field(description="Whether a browser is needed")


def _ok(label: str, detail: str = "") -> None:
    print(f"  [OK]   {label}" + (f" -- {detail}" if detail else ""))


def _fail(label: str, detail: str = "") -> None:
    print(f"  [FAIL] {label}" + (f" -- {detail}" if detail else ""))


async def main() -> int:
    get_config.cache_clear()
    cfg = get_config()
    gateway = ClaudeGateway(cfg)

    print()
    print("=" * 64)
    print("  Agentic Pilot -- Claude Provider Validation")
    print("=" * 64)
    print(f"  model          : {cfg.claude_model}")
    print(f"  effort         : {cfg.claude_effort}")
    print(f"  thinking       : {'adaptive' if cfg.claude_thinking else 'disabled'}")
    print(f"  max_tokens     : {cfg.claude_max_tokens}")
    print(f"  refusal fallback: {cfg.claude_fallback_enabled}")
    print("-" * 64)

    try:
        key = gateway._get_api_key()
    except MissingAnthropicApiKeyError as exc:
        _fail("API key", str(exc))
        print("-" * 64)
        print("  Set ANTHROPIC_API_KEY in .env, then re-run this script.")
        return 2
    _ok("API key", f"present ({len(key)} chars)")

    failures = 0

    # 1. Health probe -- validates credentials and model id without spending tokens.
    if await gateway.health_check():
        _ok("health_check", f"{cfg.claude_model} reachable")
    else:
        _fail("health_check", "model unreachable or key rejected")
        failures += 1
        print("-" * 64)
        return 1

    # 2. Plain text completion.
    try:
        text = await gateway.complete(
            system="You are a terse assistant. Answer in exactly one word.",
            user="What is the capital of France?",
        )
        if "paris" in text.lower():
            _ok("complete", f"{text.strip()!r} in {gateway._last_latency_ms} ms")
        else:
            _fail("complete", f"unexpected answer {text.strip()!r}")
            failures += 1
    except Exception as exc:
        _fail("complete", f"{type(exc).__name__}: {exc}")
        failures += 1

    # 3. Structured output against a Pydantic schema.
    try:
        plan = await gateway.complete_structured(
            system="You plan web automation tasks. Be concise.",
            user="Goal: find today's weather for Chennai on a search engine.",
            schema=_Plan,
        )
        _ok(
            "complete_structured",
            f"{len(plan.steps)} steps, requires_browser={plan.requires_browser}",
        )
        print(f"         intent: {plan.intent}")
        for i, step in enumerate(plan.steps, 1):
            print(f"         {i}. {step}")
    except Exception as exc:
        _fail("complete_structured", f"{type(exc).__name__}: {exc}")
        failures += 1

    print("-" * 64)
    if failures:
        print(f"  RESULT: {failures} check(s) FAILED")
    else:
        print("  RESULT: all checks passed -- Claude provider is ready.")
        print("  Set LLM_PROVIDER=claude in .env to make it the active provider.")
    print("=" * 64)
    print()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
