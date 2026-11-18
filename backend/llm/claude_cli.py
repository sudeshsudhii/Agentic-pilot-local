"""Claude Code CLI LLM provider implementation for Agentic Pilot.

Drives the locally installed `claude` executable in headless print mode
(`claude -p --output-format json`) and treats it as an inference backend. This
reuses the operator's existing Claude Code authentication, so no
ANTHROPIC_API_KEY is required.

Design notes
------------
* Prompts are written to the subprocess on **stdin**, not argv. DOM extracts
  routinely exceed the Windows command-line length limit.
* Claude Code is an agentic harness, so its built-in tools are disabled for
  text calls to stop it exploring the filesystem instead of answering. The
  exception is vision, which needs `Read` to open the screenshot.
* Structured calls use the CLI's native `--json-schema`, which returns an
  already-validated object in the `structured_output` field.
* `--bare` is deliberately NOT used: it forces ANTHROPIC_API_KEY/apiKeyHelper
  auth and never reads the OAuth credentials this provider exists to reuse.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from backend.config import PilotConfig, get_config
from backend.llm.base import (
    BaseLLMProvider,
    ClaudeRefusalError,
    ClaudeResponseError,
    ClaudeTimeoutError,
    LLMProviderError,
    MissingClaudeCliError,
)
from backend.llm.parser import parse_model_response
from backend.process_utils import kill_process_tree

logger = logging.getLogger("pilot.llm.claude_cli")

CLI_DESTINATION = "local:claude-code-cli"

# Built-in Claude Code tools suppressed for plain text/structured inference, so
# the harness answers directly instead of acting as an agent.
_DISABLED_TOOLS = (
    "Bash", "Edit", "Write", "Read", "Glob", "Grep",
    "WebFetch", "WebSearch", "NotebookEdit", "Task", "TodoWrite",
)

# Minimum turn budget for a vision call: the CLI needs a Read tool round-trip
# before it can answer, which cannot fit in a single turn.
_VISION_MIN_TURNS = 8

# Minimum turn budget for a text/structured call. One turn is too brittle: even
# with tools disallowed the model may still emit a tool_use block, which burns
# the only turn and fails the call with error_max_turns. A small budget lets the
# refusal come back and the model answer on the next turn.
_TEXT_MIN_TURNS = 4

# Local Ollama model tags the dynamic router may propose; the CLI cannot serve
# them, so they are mapped back onto the configured Claude Code model.
_LOCAL_MODEL_TAGS = ("qwen", "moondream", "deepseek", "llama", "mistral", "phi", "gemma")


class ClaudeCLIGateway(BaseLLMProvider):
    """Inference provider backed by the local Claude Code CLI in print mode."""

    def __init__(self, config: PilotConfig | None = None) -> None:
        self.config = config or get_config()
        self._resolved_binary: str | None = None
        self._workdir: Path | None = None
        self._last_latency_ms: int = 0
        self._last_input_tokens: int | None = None
        self._last_output_tokens: int | None = None
        self._last_cost_usd: float | None = None

    @property
    def provider_name(self) -> str:
        return "claude_cli"

    # -------------------------------------------------------------------------
    # Binary / workspace resolution
    # -------------------------------------------------------------------------
    def _binary(self) -> str:
        """Locate the `claude` executable, preferring explicit configuration."""
        if self._resolved_binary:
            return self._resolved_binary

        candidates = [
            self.config.claude_cli_path,
            os.environ.get("CLAUDE_CODE_EXECPATH"),
            "claude",
        ]
        for cand in candidates:
            if not cand:
                continue
            if os.path.isabs(cand) and os.path.exists(cand):
                self._resolved_binary = cand
                break
            found = shutil.which(cand)
            if found:
                self._resolved_binary = found
                break

        if not self._resolved_binary:
            raise MissingClaudeCliError(
                "The Claude Code CLI ('claude') was not found on PATH. "
                "Install it from https://claude.com/claude-code, or set "
                "CLAUDE_CLI_PATH in .env to the full path of claude.exe."
            )
        logger.debug("CLAUDE_CLI_BINARY resolved=%s", self._resolved_binary)
        return self._resolved_binary

    def _work_dir(self) -> Path:
        """Return an isolated scratch directory used as the CLI working dir.

        Running the CLI outside the project tree keeps project CLAUDE.md files
        and local .claude settings out of the inference context.
        """
        if self._workdir is None:
            d = Path(tempfile.gettempdir()) / "pilot_claude_cli"
            d.mkdir(parents=True, exist_ok=True)
            self._workdir = d
        return self._workdir

    def _resolve_model(self, model_override: str | None = None) -> str:
        """Resolve the CLI model, mapping local model overrides to Claude Code."""
        if not model_override:
            return self.config.claude_cli_model
        override_lower = model_override.lower()
        if any(tag in override_lower for tag in _LOCAL_MODEL_TAGS):
            return self.config.claude_cli_model
        return model_override

    # -------------------------------------------------------------------------
    # Invocation
    # -------------------------------------------------------------------------
    def _build_argv(
        self,
        model_name: str,
        system: str,
        json_schema: dict[str, Any] | None,
        allow_read: bool,
    ) -> list[str]:
        """Assemble the headless CLI argument vector."""
        argv = [
            self._binary(),
            "-p",
            "--output-format", "json",
            "--model", model_name,
            "--system-prompt", system,
            "--max-turns", str(
                max(
                    self.config.claude_cli_max_turns,
                    _VISION_MIN_TURNS if allow_read else _TEXT_MIN_TURNS,
                )
            ),
            # Keep the harness lean: no MCP servers, no skills, no shell/code tools.
            "--strict-mcp-config",
            "--disable-slash-commands",
        ]

        if allow_read:
            # Vision needs Read to open the screenshot from the scratch dir.
            argv += ["--allowedTools", "Read", "--permission-mode", "bypassPermissions"]
        else:
            argv += ["--restricted", "--disallowedTools", *_DISABLED_TOOLS]

        if json_schema is not None:
            argv += ["--json-schema", json.dumps(json_schema)]

        if self.config.claude_cli_fallback_model:
            argv += ["--fallback-model", self.config.claude_cli_fallback_model]

        return argv

    async def _invoke(self, argv: list[str], prompt: str) -> dict[str, Any]:
        """Run the CLI once and return its parsed JSON result envelope."""
        started = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._work_dir()),
            )
        except FileNotFoundError as exc:
            raise MissingClaudeCliError(
                f"Failed to launch the Claude Code CLI at {argv[0]!r}: {exc}"
            ) from exc

        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(input=prompt.encode("utf-8")),
                timeout=float(self.config.claude_cli_timeout_seconds),
            )
        except (TimeoutError, asyncio.TimeoutError) as exc:
            # proc.kill() alone orphans the CLI's own child processes on Windows.
            await kill_process_tree(proc)
            raise ClaudeTimeoutError(
                f"Claude Code CLI timed out after {self.config.claude_cli_timeout_seconds}s"
            ) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        self._last_latency_ms = duration_ms
        stdout = stdout_b.decode("utf-8", errors="replace").strip()
        stderr = stderr_b.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0 and not stdout:
            raise LLMProviderError(
                f"Claude Code CLI exited with code {proc.returncode}: "
                f"{stderr[:500] or '<no stderr>'}"
            )

        envelope = self._parse_envelope(stdout, stderr, proc.returncode)

        if envelope.get("is_error"):
            subtype = envelope.get("subtype") or envelope.get("api_error_status")
            if subtype == "error_max_turns":
                raise LLMProviderError(
                    "Claude Code CLI ran out of turns before answering "
                    f"(num_turns={envelope.get('num_turns')}). Raise CLAUDE_CLI_MAX_TURNS in .env."
                )
            raise LLMProviderError(
                f"Claude Code CLI reported an error (subtype={subtype}): "
                f"{str(envelope.get('result'))[:300]}"
            )
        if envelope.get("stop_reason") == "refusal":
            raise ClaudeRefusalError(
                "Claude declined this request. Rephrase the task or adjust the instructions."
            )
        return envelope

    @staticmethod
    def _parse_envelope(stdout: str, stderr: str, returncode: int | None) -> dict[str, Any]:
        """Extract the JSON result object from CLI stdout.

        The CLI may emit incidental lines before the result object, so each line
        is tried from the last backwards.
        """
        if not stdout:
            raise ClaudeResponseError(
                f"Claude Code CLI produced no output (exit={returncode}): "
                f"{stderr[:300] or '<no stderr>'}"
            )
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and parsed.get("type") == "result":
                return parsed

        raise ClaudeResponseError(
            f"Could not parse Claude Code CLI output as JSON: {stdout[:300]}"
        )

    def _record_call(
        self,
        model_name: str,
        system: str,
        user: str,
        content: str,
        envelope: dict[str, Any],
        duration_ms: int,
    ) -> None:
        """Emit telemetry and privacy-audit records for one completed call."""
        usage = envelope.get("usage") or {}
        self._last_input_tokens = usage.get("input_tokens")
        self._last_output_tokens = usage.get("output_tokens")
        self._last_cost_usd = envelope.get("total_cost_usd")

        logger.info(
            "CLAUDE_CLI_CALL model=%s latency_ms=%d turns=%s tokens_in=%s tokens_out=%s "
            "cache_create=%s cost_usd=%s",
            model_name,
            duration_ms,
            envelope.get("num_turns"),
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            usage.get("cache_creation_input_tokens"),
            envelope.get("total_cost_usd"),
        )

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
            destination=CLI_DESTINATION,
            prompt_bytes=len(system) + len(user),
            response_bytes=len(content),
            latency_ms=duration_ms,
        )

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
        """Return completion text from the Claude Code CLI with bounded retries."""
        model_name = self._resolve_model(model_override)

        effective_system = system
        if json_mode:
            effective_system = (
                f"{system}\n\n"
                "Respond with a single valid JSON value and nothing else. "
                "Do not wrap it in markdown fences and do not add explanation."
            )

        prompt, shot_path = self._stage_prompt(user, image_bytes)
        last_error: Exception | None = None
        try:
            for attempt in range(self.config.max_retry_count + 1):
                try:
                    argv = self._build_argv(
                        model_name,
                        effective_system,
                        json_schema=None,
                        allow_read=image_bytes is not None,
                    )
                    envelope = await self._invoke(argv, prompt)
                    text = str(envelope.get("result") or "")
                    if not text.strip():
                        raise ClaudeResponseError(
                            "Claude Code CLI returned an empty result "
                            f"(stop_reason={envelope.get('stop_reason')})."
                        )
                    self._record_call(
                        model_name, system, user, text, envelope, self._last_latency_ms
                    )
                    return text

                except (MissingClaudeCliError, ClaudeRefusalError):
                    raise
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "CLAUDE_CLI_RETRY attempt=%d/%d model=%s error_type=%s error=%s",
                        attempt + 1,
                        self.config.max_retry_count + 1,
                        model_name,
                        type(exc).__name__,
                        exc,
                    )
                    if attempt < self.config.max_retry_count:
                        await asyncio.sleep(0.5 * (2**attempt))
        finally:
            self._cleanup(shot_path)

        logger.critical(
            "CLAUDE_CLI_EXHAUSTED model=%s retries=%d last_error=%s",
            model_name,
            self.config.max_retry_count + 1,
            last_error,
        )
        raise last_error or LLMProviderError(
            f"Claude Code CLI completion failed for model {model_name}"
        )

    def _stage_prompt(self, user: str, image_bytes: bytes | None) -> tuple[str, Path | None]:
        """Write any screenshot to the scratch dir and point the prompt at it."""
        if not image_bytes:
            return user, None
        shot = self._work_dir() / f"shot_{uuid.uuid4().hex}.png"
        shot.write_bytes(image_bytes)
        prompt = (
            f"Read the image file {shot.name} in the current directory, then answer "
            f"using only what is visible in it.\n\n{user}"
        )
        return prompt, shot

    @staticmethod
    def _cleanup(shot_path: Path | None) -> None:
        """Delete a staged screenshot, ignoring failures."""
        if shot_path is None:
            return
        try:
            shot_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("CLAUDE_CLI_CLEANUP_FAILED path=%s error=%s", shot_path, exc)

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
        """Return a validated Pydantic model, using the CLI's native --json-schema.

        Falls back to the prompt-described-schema path shared with the other
        providers if the CLI rejects the generated schema.
        """
        model_name = self._resolve_model(model_override)
        prompt, shot_path = self._stage_prompt(user, image_bytes)
        try:
            envelope = await self._invoke(
                self._build_argv(
                    model_name,
                    system,
                    json_schema=schema.model_json_schema(),
                    allow_read=image_bytes is not None,
                ),
                prompt,
            )
            structured = envelope.get("structured_output")
            if isinstance(structured, dict):
                result = schema.model_validate(structured)
                logger.info(
                    "CLAUDE_CLI_STRUCTURED schema=%s model=%s latency_ms=%d native=True success=True",
                    schema.__name__,
                    model_name,
                    self._last_latency_ms,
                )
                self._record_call(
                    model_name, system, user, json.dumps(structured),
                    envelope, self._last_latency_ms,
                )
                return result

            # Schema accepted but no structured payload -- parse the text instead.
            return parse_model_response(str(envelope.get("result") or ""), schema)

        except (MissingClaudeCliError, ClaudeRefusalError):
            raise
        except Exception as exc:
            logger.warning(
                "CLAUDE_CLI_STRUCTURED_NATIVE_FAILED schema=%s model=%s error_type=%s error=%s "
                "-- falling back to prompt-described schema",
                schema.__name__,
                model_name,
                type(exc).__name__,
                exc,
            )
        finally:
            self._cleanup(shot_path)

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
                    "CLAUDE_CLI_STRUCTURED schema=%s attempt=%d native=False success=True",
                    schema.__name__,
                    attempt + 1,
                )
                return result
            except ValueError as exc:
                last_error = exc
                logger.warning(
                    "CLAUDE_CLI_STRUCTURED_RETRY schema=%s attempt=%d/%d error=%s",
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
            "CLAUDE_CLI_STRUCTURED_EXHAUSTED schema=%s retries=%d",
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
        """Verify the CLI is installed and responding, without spending tokens."""
        try:
            binary = self._binary()
        except MissingClaudeCliError as exc:
            logger.debug("CLAUDE_CLI_HEALTH_CHECK_FAILED: %s", exc)
            return False
        proc: asyncio.subprocess.Process | None = None
        try:
            proc = await asyncio.create_subprocess_exec(
                binary, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, _ = await asyncio.wait_for(proc.communicate(), timeout=20.0)
            except (TimeoutError, asyncio.TimeoutError):
                # Previously the hung process was left running here.
                await kill_process_tree(proc)
                raise
            ok = proc.returncode == 0
            if ok:
                logger.debug(
                    "CLAUDE_CLI_VERSION %s",
                    stdout_b.decode("utf-8", errors="replace").strip(),
                )
            return ok
        except Exception as exc:
            logger.debug("CLAUDE_CLI_HEALTH_CHECK_FAILED: %s", exc)
            return False
