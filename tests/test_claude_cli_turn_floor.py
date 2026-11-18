"""Regression test for the Claude Code CLI turn-floor guard.

A single turn is too brittle for a headless call: even with tools disallowed,
the model can still emit a tool_use block, which burns the turn and fails the
call with `error_max_turns` before it ever answers. This happened on live
Sonnet traffic during this project. `_build_argv` must always request at
least a minimum turn budget, regardless of a lower configured value.
"""

from __future__ import annotations

from unittest.mock import patch

from backend.config import PilotConfig
from backend.llm.claude_cli import ClaudeCLIGateway


def _argv_max_turns(gateway: ClaudeCLIGateway, allow_read: bool) -> int:
    with patch.object(ClaudeCLIGateway, "_binary", return_value="claude"):
        argv = gateway._build_argv("sonnet", "system prompt", None, allow_read)
    idx = argv.index("--max-turns")
    return int(argv[idx + 1])


def test_text_calls_get_at_least_four_turns_even_when_configured_lower():
    """The bug: a configured max-turns of 1 caused error_max_turns on real calls."""
    gateway = ClaudeCLIGateway(PilotConfig(llm_provider="claude_cli", claude_cli_max_turns=1))
    assert _argv_max_turns(gateway, allow_read=False) >= 4


def test_vision_calls_get_at_least_eight_turns():
    """Vision needs a Read tool round-trip, which needs more turns than text."""
    gateway = ClaudeCLIGateway(PilotConfig(llm_provider="claude_cli", claude_cli_max_turns=1))
    assert _argv_max_turns(gateway, allow_read=True) >= 8


def test_a_higher_configured_value_is_still_respected():
    gateway = ClaudeCLIGateway(PilotConfig(llm_provider="claude_cli", claude_cli_max_turns=20))
    assert _argv_max_turns(gateway, allow_read=False) == 20
