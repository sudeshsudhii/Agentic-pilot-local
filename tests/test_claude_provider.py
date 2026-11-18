"""Comprehensive unit and integration test suite for the Claude LLM provider,
configuration, routing, structured output, error handling, and desktop planner
integration in Agentic Pilot.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import os
import anthropic
import httpx
import pytest
from pydantic import BaseModel, Field

from backend.config import PilotConfig, get_config
from backend.agent.desktop_nodes import desktop_plan_action_node
from backend.agent.graph import build_graph
from backend.agent.state import AgentState
from backend.desktop.models import DesktopAction, DesktopActionType
from backend.llm.base import (
    BaseLLMProvider,
    ClaudeAuthenticationError,
    ClaudeRateLimitError,
    ClaudeResponseError,
    ClaudeTimeoutError,
    LLMProviderError,
    MissingAnthropicApiKeyError,
)
from backend.llm.claude import ClaudeGateway
from backend.llm.gateway import LLMGateway, OllamaGateway, get_llm_provider
from backend.llm.router import model_router


class SamplePlanSchema(BaseModel):
    step: int
    action: str
    target: str


def _messages_request() -> httpx.Request:
    """Build the dummy request object that Anthropic SDK errors require."""
    return httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _text_response(text: str, input_tokens: int = 0, output_tokens: int = 0) -> MagicMock:
    """Build a minimal Claude Messages response carrying a single text block."""
    return MagicMock(
        content=[MagicMock(type="text", text=text)],
        stop_reason="end_turn",
        model="claude-opus-5",
        usage=MagicMock(input_tokens=input_tokens, output_tokens=output_tokens),
    )


# ---------------------------------------------------------------------------
# 1. Configuration & API Key Tests
# ---------------------------------------------------------------------------

def test_claude_config_defaults_and_env_aliases():
    """Verify Claude configuration defaults and environment variable resolution."""
    with patch.dict(os.environ, {
        "LLM_PROVIDER": "claude",
        "ANTHROPIC_API_KEY": "test_env_key_12345",
        "CLAUDE_MODEL": "claude-sonnet-4-5",
        "CLAUDE_EFFORT": "medium",
        "CLAUDE_TIMEOUT_SECONDS": "30",
    }, clear=False):
        cfg = PilotConfig()
        assert cfg.llm_provider == "claude"
        assert cfg.anthropic_api_key == "test_env_key_12345"
        assert cfg.claude_model == "claude-sonnet-4-5"
        assert cfg.claude_effort == "medium"
        assert cfg.claude_timeout_seconds == 30


def test_missing_api_key_raises_clear_error():
    """Verify MissingAnthropicApiKeyError is raised when ANTHROPIC_API_KEY is absent."""
    cfg = PilotConfig(anthropic_api_key=None)
    with patch.dict(os.environ, {}, clear=True):
        # Explicitly remove any ANTHROPIC_API_KEY from env
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("PILOT_ANTHROPIC_API_KEY", None)
        gateway = ClaudeGateway(config=cfg)
        with pytest.raises(MissingAnthropicApiKeyError) as exc_info:
            gateway._get_api_key()
        assert "ANTHROPIC_API_KEY is missing" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Provider Selection Tests
# ---------------------------------------------------------------------------

def test_provider_selection_ollama():
    """Verify get_llm_provider returns OllamaGateway when LLM_PROVIDER=ollama."""
    cfg = PilotConfig(llm_provider="ollama")
    provider = get_llm_provider(cfg)
    assert isinstance(provider, OllamaGateway)
    assert provider.provider_name == "ollama"


def test_provider_selection_claude():
    """Verify get_llm_provider returns ClaudeGateway when LLM_PROVIDER=claude."""
    cfg = PilotConfig(llm_provider="claude", anthropic_api_key="test_key")
    provider = get_llm_provider(cfg)
    assert isinstance(provider, ClaudeGateway)
    assert provider.provider_name == "claude"


def test_llm_gateway_proxy():
    """Verify LLMGateway correctly proxies to the active provider."""
    cfg = PilotConfig(llm_provider="claude", anthropic_api_key="test_key")
    gw = LLMGateway(cfg)
    assert gw.provider_name == "claude"


# ---------------------------------------------------------------------------
# 3. Model Router with Cloud Provider
# ---------------------------------------------------------------------------

def test_model_router_with_claude_provider():
    """Verify ClaudeGateway maps local model overrides back to the Claude model."""
    gateway = ClaudeGateway(config=PilotConfig(anthropic_api_key="test_key", claude_model="claude-opus-5"))
    assert gateway._resolve_model("qwen2.5:7b") == "claude-opus-5"
    assert gateway._resolve_model("moondream") == "claude-opus-5"
    assert gateway._resolve_model("deepseek-r1:1.5b") == "claude-opus-5"
    assert gateway._resolve_model("claude-sonnet-4-5") == "claude-sonnet-4-5"


# ---------------------------------------------------------------------------
# 4. Claude Text & Structured Generation Tests (Mocked API)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claude_complete_text():
    """Verify Claude complete() returns generated text and records telemetry."""
    cfg = PilotConfig(anthropic_api_key="fake_test_key_abc", claude_model="claude-opus-5")
    gateway = ClaudeGateway(config=cfg)

    mock_resp = _text_response("Navigation confirmed.", input_tokens=15, output_tokens=5)

    with patch.object(gateway, "_client_instance") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.beta.messages.create = AsyncMock(return_value=mock_resp)
        mock_client_factory.return_value = mock_client

        result = await gateway.complete(system="System instructions", user="User request")
        assert result == "Navigation confirmed."
        assert gateway._last_input_tokens == 15
        assert gateway._last_output_tokens == 5


@pytest.mark.asyncio
async def test_claude_complete_structured():
    """Verify Claude complete_structured() returns parsed Pydantic model."""
    cfg = PilotConfig(anthropic_api_key="fake_test_key_abc", claude_model="claude-opus-5")
    gateway = ClaudeGateway(config=cfg)

    mock_resp = _text_response(
        '{"step": 1, "action": "click_element", "target": "desktop-el-001"}',
        input_tokens=30,
        output_tokens=18,
    )
    # Native structured outputs hydrate the schema server-side
    mock_resp.parsed_output = SamplePlanSchema(step=1, action="click_element", target="desktop-el-001")

    with patch.object(gateway, "_client_instance") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.beta.messages.parse = AsyncMock(return_value=mock_resp)
        mock_client_factory.return_value = mock_client

        model_res = await gateway.complete_structured(
            system="Planner system",
            user="Plan next step",
            schema=SamplePlanSchema,
        )
        assert isinstance(model_res, SamplePlanSchema)
        assert model_res.step == 1
        assert model_res.action == "click_element"
        assert model_res.target == "desktop-el-001"


# ---------------------------------------------------------------------------
# 5. Claude Error Handling Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_claude_authentication_error_no_retry():
    """Verify a 401 invalid API key immediately raises ClaudeAuthenticationError."""
    cfg = PilotConfig(anthropic_api_key="invalid_key", max_retry_count=3)
    gateway = ClaudeGateway(config=cfg)

    auth_error = anthropic.AuthenticationError(
        "invalid x-api-key",
        response=httpx.Response(401, request=_messages_request()),
        body=None,
    )

    with patch.object(gateway, "_client_instance") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.beta.messages.create = AsyncMock(side_effect=auth_error)
        mock_client_factory.return_value = mock_client

        with pytest.raises(ClaudeAuthenticationError):
            await gateway.complete(system="sys", user="user")

        # Must not retry on permanent auth failure
        assert mock_client.beta.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_claude_timeout_handling():
    """Verify request timeout raises ClaudeTimeoutError."""
    cfg = PilotConfig(anthropic_api_key="valid_key", claude_timeout_seconds=1, max_retry_count=0)
    gateway = ClaudeGateway(config=cfg)

    with patch.object(gateway, "_client_instance") as mock_client_factory:
        mock_client = MagicMock()
        mock_client.beta.messages.create = AsyncMock(
            side_effect=anthropic.APITimeoutError(request=_messages_request())
        )
        mock_client_factory.return_value = mock_client

        with pytest.raises(ClaudeTimeoutError):
            await gateway.complete(system="sys", user="user")


@pytest.mark.asyncio
async def test_claude_invalid_structured_output_exhaustion():
    """Verify malformed JSON responses raise ClaudeResponseError after max retries."""
    cfg = PilotConfig(anthropic_api_key="valid_key", max_retry_count=1)
    gateway = ClaudeGateway(config=cfg)

    with patch.object(gateway, "_client_instance") as mock_client_factory:
        mock_client = MagicMock()
        # Native structured output unavailable -> prompt-described schema fallback
        mock_client.beta.messages.parse = AsyncMock(side_effect=Exception("structured outputs unsupported"))
        mock_client.beta.messages.create = AsyncMock(return_value=_text_response("NOT JSON AT ALL"))
        mock_client_factory.return_value = mock_client

        with pytest.raises(ClaudeResponseError):
            await gateway.complete_structured(system="sys", user="user", schema=SamplePlanSchema)


# ---------------------------------------------------------------------------
# 6. Desktop Planner Integration & Safety Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_desktop_planner_with_claude_provider():
    """Verify desktop_plan_action_node uses Claude and produces typed DesktopAction."""
    state: AgentState = {
        "task_id": "test-task-1",
        "input_text": "Open Windows Settings",
        "status": "running",
        "current_step_index": 1,
        "desktop_observation": {
            "active_window": {"title": "Desktop"},
            "elements": [
                {"id": "desktop-el-01", "name": "Start", "role": "button", "control_type": "ButtonControl"}
            ],
        },
    }

    mock_action = DesktopAction(
        action_type=DesktopActionType.LAUNCH_APPLICATION,
        application="settings",
        reasoning="Launching Windows Settings app",
    )

    with patch("backend.agent.desktop_nodes.get_llm_provider") as mock_get_provider:
        mock_gw = MagicMock()
        mock_gw.complete_structured = AsyncMock(return_value=mock_action)
        mock_get_provider.return_value = mock_gw

        result = await desktop_plan_action_node(state)
        assert result["desktop_action"]["action_type"] == "launch_application"
        assert result["desktop_action"]["application"] == "settings"


@pytest.mark.asyncio
async def test_desktop_planner_completion_authority_enforced():
    """Verify planner cannot directly return 'complete' (Requirement 10)."""
    state: AgentState = {
        "task_id": "test-task-2",
        "input_text": "Turn on Bluetooth",
        "status": "running",
        "desktop_observation": {"elements": []},
    }

    # Simulate an LLM attempting to set action_type or text to "complete"
    fake_action = DesktopAction(
        action_type=DesktopActionType.WAIT,
        reasoning="Task is complete",
    )
    # Monkeypatch action_type to simulate a raw string "complete"
    fake_action.action_type = "complete"  # type: ignore

    with patch("backend.agent.desktop_nodes.get_llm_provider") as mock_get_provider:
        mock_gw = MagicMock()
        mock_gw.complete_structured = AsyncMock(return_value=fake_action)
        mock_get_provider.return_value = mock_gw

        result = await desktop_plan_action_node(state)
        # Must be overridden to request_reobservation
        assert result["desktop_action"]["action_type"] == "request_reobservation"


@pytest.mark.asyncio
async def test_desktop_planner_rejects_arbitrary_code():
    """Verify planner rejects PowerShell, CMD, Python commands (Requirement 9)."""
    state: AgentState = {
        "task_id": "test-task-3",
        "input_text": "Open something",
        "status": "running",
        "desktop_observation": {"elements": []},
    }

    malicious_action = DesktopAction(
        action_type=DesktopActionType.TYPE_TEXT,
        text="powershell -Command Remove-Item -Force C:\\test",
        reasoning="Attempting script execution",
    )

    with patch("backend.agent.desktop_nodes.get_llm_provider") as mock_get_provider:
        mock_gw = MagicMock()
        mock_gw.complete_structured = AsyncMock(return_value=malicious_action)
        mock_get_provider.return_value = mock_gw

        result = await desktop_plan_action_node(state)
        # Must be rejected and safe request_reobservation returned
        assert result["desktop_action"]["action_type"] == "request_reobservation"


@pytest.mark.asyncio
async def test_desktop_planner_bluetooth_already_on_preservation():
    """Verify if Bluetooth is already ON, planner does NOT click toggle (Requirements 8 & 14)."""
    state: AgentState = {
        "task_id": "test-task-4",
        "input_text": "Open Windows Settings and make sure Bluetooth is ON",
        "status": "running",
        "desktop_observation": {
            "elements": [
                {
                    "id": "desktop-el-bt",
                    "name": "Bluetooth",
                    "role": "toggle",
                    "control_type": "ButtonControl",
                    "toggle_state": "On",
                }
            ]
        },
    }

    # LLM wrongly proposes clicking the toggle
    click_action = DesktopAction(
        action_type=DesktopActionType.CLICK_ELEMENT,
        target_id="desktop-el-bt",
        reasoning="Click Bluetooth toggle",
    )

    with patch("backend.agent.desktop_nodes.get_llm_provider") as mock_get_provider:
        mock_gw = MagicMock()
        mock_gw.complete_structured = AsyncMock(return_value=click_action)
        mock_get_provider.return_value = mock_gw

        result = await desktop_plan_action_node(state)
        # Must be overridden to wait to preserve On state!
        assert result["desktop_action"]["action_type"] == "wait"
        assert "already ON" in result["desktop_action"]["reasoning"]


# ---------------------------------------------------------------------------
# 7. Graph Architectural Routing Tests (Requirement 15)
# ---------------------------------------------------------------------------

def test_graph_desktop_recovery_routes_to_desktop_observe():
    """Verify desktop recovery loops back to desktop_observe, NOT extract_dom (Requirement 15)."""
    graph = build_graph()
    assert graph is not None

    # Inspect conditional branches in the graph
    branches = graph.builder.branches.get("error_recovery", {})
    assert len(branches) > 0

    # Test the branch routing function directly on desktop state
    branch = list(branches.values())[0]
    routing_fn = branch.path.func

    desktop_retry_state: AgentState = {
        "task_id": "t1",
        "input_text": "Settings task",
        "current_environment": "desktop",
        "status": "running",
    }
    assert routing_fn(desktop_retry_state) == "desktop_observe"

    browser_retry_state: AgentState = {
        "task_id": "t2",
        "input_text": "Browser task",
        "current_environment": "browser",
        "status": "running",
    }
    assert routing_fn(browser_retry_state) == "extract_dom"

    desktop_fail_state: AgentState = {
        "task_id": "t3",
        "input_text": "Settings task",
        "current_environment": "desktop",
        "status": "failed",
    }
    assert routing_fn(desktop_fail_state) == "desktop_complete"


def test_graph_mixed_task_step_aware():
    """Verify mixed task routes based on current step environment (Requirement 15)."""
    from backend.agent.environment import EnvironmentType, classify_environment
    from backend.llm.parser import TaskPlan, TaskStep

    browser_step = TaskStep(step_index=1, description="Navigate to https://example.com", action_type="navigate")
    desktop_step = TaskStep(step_index=2, description="Open Notepad and paste", action_type="launch_application")

    assert classify_environment(browser_step.description) == EnvironmentType.BROWSER
    assert classify_environment(desktop_step.description) == EnvironmentType.DESKTOP
