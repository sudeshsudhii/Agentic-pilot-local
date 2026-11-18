"""Abstract base interface and exceptions for LLM providers in Agentic Pilot."""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("pilot.llm.base")


class LLMProviderError(Exception):
    """Base exception for all LLM provider failures."""
    pass


class MissingAnthropicApiKeyError(LLMProviderError):
    """Raised when Claude provider is selected but ANTHROPIC_API_KEY is not set."""
    pass


class ClaudeAuthenticationError(LLMProviderError):
    """Raised when the Anthropic API key is invalid or unauthorized."""
    pass


class ClaudeRateLimitError(LLMProviderError):
    """Raised when Claude returns HTTP 429 Rate Limit / quota exhaustion."""
    pass


class ClaudeTimeoutError(LLMProviderError):
    """Raised when a Claude API request times out."""
    pass


class ClaudeResponseError(LLMProviderError):
    """Raised when Claude returns an empty or unparsable response."""
    pass


class MissingClaudeCliError(LLMProviderError):
    """Raised when the Claude Code CLI provider is selected but `claude` is absent."""
    pass


class ClaudeRefusalError(LLMProviderError):
    """Raised when Claude declines a request on policy grounds."""
    pass


class BaseLLMProvider(ABC):
    """Abstract base provider interface implemented by the Claude and Ollama gateways.
    
    Provides uniform text generation, structured parsing, and health probing.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'claude' or 'ollama')."""
        ...

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        image_bytes: bytes | None = None,
        model_override: str | None = None,
    ) -> str:
        """Return raw completion text from the active model."""
        ...

    @abstractmethod
    async def complete_structured(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        image_bytes: bytes | None = None,
        model_override: str | None = None,
    ) -> BaseModel:
        """Return a validated Pydantic model parsed from the active model's response."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Probe the liveness and readiness of the provider."""
        ...

    # Common aliases matching Requirement 2:
    # generate(...)
    # generate_structured(...)
    async def generate(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        image_bytes: bytes | None = None,
        model_override: str | None = None,
    ) -> str:
        """Alias for complete(...)."""
        return await self.complete(
            system=system,
            user=user,
            json_mode=json_mode,
            image_bytes=image_bytes,
            model_override=model_override,
        )

    async def generate_structured(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        image_bytes: bytes | None = None,
        model_override: str | None = None,
    ) -> BaseModel:
        """Alias for complete_structured(...)."""
        return await self.complete_structured(
            system=system,
            user=user,
            schema=schema,
            image_bytes=image_bytes,
            model_override=model_override,
        )
