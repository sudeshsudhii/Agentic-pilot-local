"""Local language model integration package for Pilot."""

from backend.llm.analyzer import CapabilityAnalyzer, TaskCapabilityRequirements, capability_analyzer
from backend.llm.base import (
    BaseLLMProvider,
    ClaudeAuthenticationError,
    ClaudeRateLimitError,
    ClaudeRefusalError,
    ClaudeResponseError,
    ClaudeTimeoutError,
    LLMProviderError,
    MissingAnthropicApiKeyError,
    MissingClaudeCliError,
)
from backend.llm.claude import ClaudeGateway
from backend.llm.claude_cli import ClaudeCLIGateway
from backend.llm.gateway import LLMGateway, OllamaGateway, get_llm_provider
from backend.llm.parser import ActionResult, ParsedIntent, PlannedAction, TaskPlan, TaskStep
from backend.llm.registry import ModelCapability, ModelMetadata, ModelRegistry, ModelRole, model_registry
from backend.llm.router import ModelRouter, RoutingDecision, model_router

__all__ = [
    "BaseLLMProvider",
    "ClaudeGateway",
    "ClaudeCLIGateway",
    "LLMGateway",
    "OllamaGateway",
    "get_llm_provider",
    "LLMProviderError",
    "MissingAnthropicApiKeyError",
    "MissingClaudeCliError",
    "ClaudeAuthenticationError",
    "ClaudeRateLimitError",
    "ClaudeTimeoutError",
    "ClaudeResponseError",
    "ClaudeRefusalError",
    "ParsedIntent",
    "PlannedAction",
    "ActionResult",
    "TaskPlan",
    "TaskStep",
    "ModelCapability",
    "ModelRole",
    "ModelMetadata",
    "ModelRegistry",
    "model_registry",
    "CapabilityAnalyzer",
    "capability_analyzer",
    "TaskCapabilityRequirements",
    "ModelRouter",
    "RoutingDecision",
    "model_router",
]

