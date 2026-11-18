"""Anthropic Claude cloud LLM provider implementation for Agentic Pilot.

Uses the official Anthropic Python SDK (`anthropic`) with adaptive thinking,
native Pydantic structured outputs, multimodal vision grounding, server-side
refusal fallbacks, and zero local laptop hardware overhead.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import time
from typing import Any

from pydantic import BaseModel

from backend.config import PilotConfig, get_config
from backend.llm.base import (
    BaseLLMProvider,
    ClaudeAuthenticationError,
    ClaudeRateLimitError,
    ClaudeRefusalError,
    ClaudeResponseError,
    ClaudeTimeoutError,
    LLMProviderError,
    MissingAnthropicApiKeyError,
)
from backend.llm.parser import parse_model_response

logger = logging.getLogger("pilot.llm.claude")

ANTHROPIC_ENDPOINT = "https://api.anthropic.com"

# Beta flag required for the server-side refusal fallback parameter.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# Local Ollama model tags the dynamic router may propose. Claude cannot serve
# them, so they are mapped back onto the configured Claude model instead.
_LOCAL_MODEL_TAGS = ("qwen", "moondream", "deepseek", "llama", "mistral", "phi", "gemma")

# Effort levels that are incompatible with explicitly disabled thinking.
_HIGH_EFFORT_LEVELS = ("xhigh", "max")


class ClaudeGateway(BaseLLMProvider):
    """Async client wrapper for Anthropic Claude cloud inference."""

    def __init__(self, config: PilotConfig | None = None) -> None:
        self.config = config or get_config()
        self._client = None
        self._last_latency_ms: int = 0
        self._last_input_tokens: int | None = None
        self._last_output_tokens: int | None = None

    @property
    def provider_name(self) -> str:
        return "claude"

    # -------------------------------------------------------------------------
    # Client construction
    # -------------------------------------------------------------------------
    def _get_api_key(self) -> str:
        """Resolve the Anthropic API key ONLY from environment, never hardcoded."""
        key = (
            self.config.anthropic_api_key
            or os.environ.get("ANTHROPIC_API_KEY")
            or os.environ.get("PILOT_ANTHROPIC_API_KEY")
        )
        if not key or not key.strip():
            raise MissingAnthropicApiKeyError(
                "ANTHROPIC_API_KEY is missing from the environment. "
                "Set ANTHROPIC_API_KEY in your system environment or .env file "
                "to enable Claude cloud inference."
            )
        return key.strip()

    def _client_instance(self):
        """Return a lazily-created Anthropic async client."""
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(
                api_key=self._get_api_key(),
                timeout=float(self.config.claude_timeout_seconds),
                max_retries=0,  # retries are handled by this gateway's own loop
            )
        return self._client

    def _resolve_model(self, model_override: str | None = None) -> str:
        """Resolve the Claude model name, mapping local model overrides to Claude."""
        if not model_override:
            return self.config.claude_model
        override_lower = model_override.lower()
        if any(tag in override_lower for tag in _LOCAL_MODEL_TAGS):
            return self.config.claude_model
        return model_override

    # -------------------------------------------------------------------------
    # Request assembly
    # -------------------------------------------------------------------------
    def _thinking_and_effort(self) -> tuple[dict[str, Any], str]:
        """Resolve the thinking config and effort level, keeping the pair legal.

        Explicitly disabled thinking is rejected by the API at 'xhigh'/'max'
        effort, so the effort is clamped to 'high' in that combination.
        """
        effort = (self.config.claude_effort or "high").lower().strip()
        if self.config.claude_thinking:
            return {"type": "adaptive"}, effort
        if effort in _HIGH_EFFORT_LEVELS:
            logger.warning(
                "CLAUDE_EFFORT_CLAMPED effort=%s -> high (disabled thinking rejects xhigh/max)",
                effort,
            )
            effort = "high"
        return {"type": "disabled"}, effort

    def _build_content(self, user: str, image_bytes: bytes | None) -> list[dict[str, Any]]:
        """Build the user content blocks, placing any image before the text."""
        blocks: list[dict[str, Any]] = []
        if image_bytes:
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
                    },
                }
            )
        blocks.append({"type": "text", "text": user})
        return blocks

    def _common_kwargs(self, model_name: str, system: str) -> dict[str, Any]:
        """Assemble request kwargs shared by text and structured calls.

        Note: `temperature` is deliberately never sent -- sampling parameters are
        removed on Claude Opus 5 / Sonnet 5 / Opus 4.7+ and return HTTP 400.
        """
        thinking, effort = self._thinking_and_effort()
        kwargs: dict[str, Any] = {
            "model": model_name,
            "max_tokens": self.config.claude_max_tokens,
            "system": system,
            "thinking": thinking,
            "output_config": {"effort": effort},
        }
        if self.config.claude_fallback_enabled:
            # Server-side refusal fallback: on a policy decline the API transparently
            # re-runs the same request on a suitable fallback model in the same call.
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        return kwargs

    def _record_call(
        self,
        model_name: str,
        system: str,
        user: str,
        content: str,
        duration_ms: int,
    ) -> None:
        """Emit telemetry and privacy-audit records for one completed call."""
        from backend.telemetry.tracer import tracer

        tracer.record_llm_call(
            task_id="global",
            prompt=system + "\n" + user,
            response=content,
            latency_ms=duration_ms,
            model=model_name,
        )

        from backend.security.audit import privacy_auditor

        privacy_auditor.record_llm_call(
            model=model_name,
            destination=ANTHROPIC_ENDPOINT,
            prompt_bytes=len(system) + len(user),
            response_bytes=len(content),
            latency_ms=duration_ms,
        )

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Concatenate the text blocks of a Claude response, skipping thinking."""
        parts: list[str] = []
        for block in getattr(response, "content", None) or []:
            if getattr(block, "type", None) == "text":
                parts.append(getattr(block, "text", "") or "")
        return "".join(parts)

    @staticmethod
    def _usage_tokens(response: Any) -> tuple[int | None, int | None]:
        """Return (input_tokens, output_tokens) from a response, when reported."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return None, None
        return getattr(usage, "input_tokens", None), getattr(usage, "output_tokens", None)

    def _guard_refusal(self, response: Any, model_name: str) -> None:
        """Raise a descriptive error when the whole fallback chain refused."""
        if getattr(response, "stop_reason", None) != "refusal":
            return
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None) if details else None
        explanation = getattr(details, "explanation", None) if details else None
        logger.error(
            "CLAUDE_REFUSAL model=%s category=%s explanation=%s",
            model_name,
            category,
            explanation,
        )
        raise ClaudeRefusalError(
            f"Claude declined this request (category={category or 'unknown'}). "
            f"{explanation or 'Rephrase the task or adjust the instructions.'}"
        )

    def _classify(self, exc: Exception, model_name: str) -> tuple[Exception, bool]:
        """Map an SDK exception to a Pilot error plus whether it is retryable."""
        import anthropic

        if isinstance(exc, anthropic.AuthenticationError):
            logger.error("CLAUDE_AUTH_ERROR: Invalid or unauthorized Anthropic API key.")
            return (
                ClaudeAuthenticationError(
                    "Anthropic API authentication failed. "
                    "Verify that your ANTHROPIC_API_KEY is valid."
                ),
                False,
            )
        if isinstance(exc, anthropic.RateLimitError):
            return ClaudeRateLimitError(f"Claude rate limit / quota exceeded: {exc}"), True
        if isinstance(exc, anthropic.APITimeoutError):
            return (
                ClaudeTimeoutError(
                    f"Claude API request timed out after {self.config.claude_timeout_seconds}s"
                ),
                True,
            )
        if isinstance(exc, anthropic.APIConnectionError):
            return LLMProviderError(f"Claude API connection failed: {exc}"), True
        if isinstance(exc, anthropic.BadRequestError):
            # Malformed request (bad model name, illegal parameter pair) -- retrying
            # the identical payload cannot succeed.
            return (
                LLMProviderError(f"Claude API rejected the request for {model_name}: {exc}"),
                False,
            )
        if isinstance(exc, anthropic.APIStatusError):
            status = getattr(exc, "status_code", 0) or 0
            return (
                LLMProviderError(f"Claude API error {status} for {model_name}: {exc}"),
                status >= 500,
            )
        return LLMProviderError(f"Claude API error ({type(exc).__name__}): {exc}"), False

    # -------------------------------------------------------------------------
    # Text completion
    # -------------------------------------------------------------------------
    async def complete(
        self,
        system: str,
        user: str,
        json_mode: bool = False,
        image_bytes: bytes | None = None,
        model_override: str | None = None,
    ) -> str:
        """Return completion text from the Anthropic Claude API with bounded retries."""
        model_name = self._resolve_model(model_override)
        client = self._client_instance()

        effective_system = system
        if json_mode:
            effective_system = (
                f"{system}\n\n"
                "Respond with a single valid JSON value and nothing else. "
                "Do not wrap it in markdown fences and do not add explanation."
            )

        content = self._build_content(user, image_bytes)
        last_error: Exception | None = None

        for attempt in range(self.config.max_retry_count + 1):
            started = time.perf_counter()
            try:
                response = await client.beta.messages.create(
                    messages=[{"role": "user", "content": content}],
                    **self._common_kwargs(model_name, effective_system),
                )
                duration_ms = int((time.perf_counter() - started) * 1000)
                self._last_latency_ms = duration_ms

                self._guard_refusal(response, model_name)

                text = self._extract_text(response)
                in_tokens, out_tokens = self._usage_tokens(response)
                self._last_input_tokens = in_tokens
                self._last_output_tokens = out_tokens

                if not text.strip():
                    stop_reason = getattr(response, "stop_reason", None)
                    raise ClaudeResponseError(
                        f"Claude returned an empty response (stop_reason={stop_reason})."
                    )

                logger.info(
                    "CLAUDE_CALL model=%s served_by=%s latency_ms=%d tokens_in=%s "
                    "tokens_out=%s attempt=%d",
                    model_name,
                    getattr(response, "model", model_name),
                    duration_ms,
                    in_tokens if in_tokens is not None else len(system.split()) + len(user.split()),
                    out_tokens if out_tokens is not None else len(text.split()),
                    attempt + 1,
                )

                self._record_call(model_name, system, user, text, duration_ms)
                return text

            except (ClaudeAuthenticationError, ClaudeRefusalError):
                raise
            except ClaudeResponseError as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                last_error = exc
                logger.warning(
                    "CLAUDE_EMPTY_RESPONSE attempt=%d/%d model=%s latency_ms=%d",
                    attempt + 1,
                    self.config.max_retry_count + 1,
                    model_name,
                    duration_ms,
                )
            except Exception as exc:
                duration_ms = int((time.perf_counter() - started) * 1000)
                mapped, retryable = self._classify(exc, model_name)
                if isinstance(mapped, ClaudeAuthenticationError):
                    raise mapped from exc
                last_error = mapped
                logger.warning(
                    "CLAUDE_RETRY attempt=%d/%d model=%s error_type=%s retryable=%s "
                    "latency_ms=%d error=%s",
                    attempt + 1,
                    self.config.max_retry_count + 1,
                    model_name,
                    type(exc).__name__,
                    retryable,
                    duration_ms,
                    exc,
                )
                if not retryable:
                    break

            if attempt < self.config.max_retry_count:
                is_rate_limited = isinstance(last_error, ClaudeRateLimitError)
                backoff = max(5.0, 1.0 * (2**attempt)) if is_rate_limited else 0.5 * (2**attempt)
                await asyncio.sleep(backoff)

        logger.critical(
            "CLAUDE_EXHAUSTED model=%s retries=%d last_error=%s",
            model_name,
            self.config.max_retry_count + 1,
            last_error,
        )
        raise last_error or LLMProviderError(f"Claude completion failed for model {model_name}")

    # -------------------------------------------------------------------------
    # Structured completion
    # -------------------------------------------------------------------------
    async def complete_structured(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        image_bytes: bytes | None = None,
        model_override: str | None = None,
    ) -> BaseModel:
        """Return a validated Pydantic model parsed from a Claude response.

        Uses native structured outputs, which constrain the response to the schema
        server-side. If the schema is not expressible as a strict JSON schema, this
        degrades to the prompt-described-schema path shared with the other providers.
        """
        model_name = self._resolve_model(model_override)
        client = self._client_instance()
        content = self._build_content(user, image_bytes)

        started = time.perf_counter()
        try:
            response = await client.beta.messages.parse(
                messages=[{"role": "user", "content": content}],
                output_format=schema,
                **self._common_kwargs(model_name, system),
            )
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._last_latency_ms = duration_ms

            self._guard_refusal(response, model_name)

            parsed = getattr(response, "parsed_output", None)
            if isinstance(parsed, schema):
                logger.info(
                    "CLAUDE_STRUCTURED schema=%s model=%s latency_ms=%d native=True success=True",
                    schema.__name__,
                    model_name,
                    duration_ms,
                )
                self._record_call(
                    model_name, system, user, self._extract_text(response), duration_ms
                )
                return parsed

            # Structured mode guarantees schema-valid JSON text even if the SDK
            # could not hydrate it -- parse the text with the shared parser.
            return parse_model_response(self._extract_text(response), schema)

        except (ClaudeAuthenticationError, ClaudeRefusalError):
            raise
        except Exception as exc:
            logger.warning(
                "CLAUDE_STRUCTURED_NATIVE_FAILED schema=%s model=%s error_type=%s error=%s "
                "-- falling back to prompt-described schema",
                schema.__name__,
                model_name,
                type(exc).__name__,
                exc,
            )

        return await self._complete_structured_via_prompt(
            system, user, schema, image_bytes, model_override
        )

    async def _complete_structured_via_prompt(
        self,
        system: str,
        user: str,
        schema: type[BaseModel],
        image_bytes: bytes | None,
        model_override: str | None,
    ) -> BaseModel:
        """Describe the schema in the prompt and repair-retry until it parses."""
        fields = []
        for name, field in schema.model_fields.items():
            ann_str = str(field.annotation)
            type_info = "string"
            if "int" in ann_str:
                type_info = "integer"
            elif "float" in ann_str or "num" in ann_str:
                type_info = "number"
            elif "bool" in ann_str:
                type_info = "boolean"
            elif "list" in ann_str or "List" in ann_str:
                type_info = "array"
            elif "dict" in ann_str or "Dict" in ann_str:
                type_info = "object"

            is_optional = "None" in ann_str or "Optional" in ann_str
            req_str = "optional" if is_optional else "REQUIRED"
            desc = f" ({field.description})" if field.description else ""
            fields.append(f'  "{name}": {type_info} - {req_str}{desc}')

        fields_str = "{\n" + ",\n".join(fields) + "\n}"
        system_with_schema = (
            f"{system}\n\n"
            f"You MUST respond with a single valid JSON object containing exactly these fields:\n"
            f"{fields_str}\n"
            f"Do not include any explanation or markdown formatting."
        )

        prompt = user
        last_error: Exception | None = None
        for attempt in range(self.config.max_retry_count + 1):
            try:
                raw = await self.complete(
                    system_with_schema,
                    prompt,
                    json_mode=True,
                    image_bytes=image_bytes,
                    model_override=model_override,
                )
                result = parse_model_response(raw, schema)
                logger.info(
                    "CLAUDE_STRUCTURED schema=%s attempt=%d native=False success=True",
                    schema.__name__,
                    attempt + 1,
                )
                return result
            except ValueError as exc:
                last_error = exc
                logger.warning(
                    "CLAUDE_STRUCTURED_RETRY schema=%s attempt=%d/%d error=%s",
                    schema.__name__,
                    attempt + 1,
                    self.config.max_retry_count + 1,
                    exc,
                )
                prompt = (
                    f"{user}\n\n"
                    f"Your previous response was not valid JSON or did not match the schema:\n"
                    f"{exc}\n"
                    f"Respond with ONLY one JSON object matching the schema."
                )
                await asyncio.sleep(0.2 * (attempt + 1))

        logger.error(
            "CLAUDE_STRUCTURED_EXHAUSTED schema=%s retries=%d",
            schema.__name__,
            self.config.max_retry_count + 1,
        )
        raise ClaudeResponseError(
            f"Structured LLM response could not be parsed into {schema.__name__}: {last_error}"
        ) from last_error

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------
    async def health_check(self) -> bool:
        """Probe Claude API reachability without consuming output tokens."""
        try:
            key = self._get_api_key()
            if not key or len(key) < 10:
                return False
            client = self._client_instance()
            await asyncio.wait_for(
                client.models.retrieve(self.config.claude_model),
                timeout=10.0,
            )
            return True
        except Exception as exc:
            logger.debug("CLAUDE_HEALTH_CHECK_FAILED: %s", exc)
            return False
