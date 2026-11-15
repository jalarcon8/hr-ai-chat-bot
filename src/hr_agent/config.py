"""Environment-backed configuration for Feature 003."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import overload

from dotenv import dotenv_values

_DEFAULT_MODEL = "openai/gpt-oss-20b"


@overload
def get_agent_setting(*names: str, default: str) -> str: ...


@overload
def get_agent_setting(*names: str, default: None = None) -> str | None: ...


def get_agent_setting(*names: str, default: str | None = None) -> str | None:
    """Read process variables before local .env values without modifying os.environ."""
    for name in names:
        if name in os.environ:
            return os.environ[name]
    values = dotenv_values(".env", encoding="utf-8", interpolate=False)
    for name in names:
        if name in values:
            value = values[name]
            if value is None:
                raise ValueError(f"{name} must have a value in .env.")
            return value
    return default


@dataclass(frozen=True)
class AgentConfig:
    model_provider: str = "groq"
    model_name: str = _DEFAULT_MODEL
    temperature: float = 0.0
    max_tokens: int = 1024
    top_k: int = 5
    max_tool_calls: int = 3
    mcp_server_command: str = sys.executable
    mcp_server_args: tuple[str, ...] = ("-m", "hr_mcp.server")
    trace_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.model_provider.strip() or not self.model_name.strip():
            raise ValueError("Model provider and name must not be blank.")
        if not 0 <= self.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2.")
        if self.max_tokens < 1:
            raise ValueError("max_tokens must be positive.")
        if self.top_k < 1:
            raise ValueError("top_k must be positive.")
        if self.max_tool_calls < 1:
            raise ValueError("max_tool_calls must be positive.")
        if not self.mcp_server_command.strip():
            raise ValueError("MCP server command must not be blank.")

    @classmethod
    def from_environment(cls) -> AgentConfig:
        try:
            temperature = float(get_agent_setting("AGENT_TEMPERATURE", default="0"))
            max_tokens = int(get_agent_setting("AGENT_MAX_TOKENS", default="1024"))
            top_k = int(get_agent_setting("AGENT_TOP_K", default="5"))
            max_tool_calls = int(get_agent_setting("AGENT_MAX_TOOL_CALLS", default="3"))
        except ValueError as exc:
            raise ValueError("Agent numeric environment settings are invalid.") from exc

        raw_args = get_agent_setting("AGENT_MCP_SERVER_ARGS")
        if raw_args is None:
            server_args = ("-m", "hr_mcp.server")
        else:
            try:
                parsed_args = json.loads(raw_args)
            except json.JSONDecodeError as exc:
                raise ValueError("AGENT_MCP_SERVER_ARGS must be a JSON string array.") from exc
            if not isinstance(parsed_args, list) or any(
                not isinstance(item, str) for item in parsed_args
            ):
                raise ValueError("AGENT_MCP_SERVER_ARGS must be a JSON string array.")
            server_args = tuple(parsed_args)

        raw_trace_path = get_agent_setting("AGENT_TRACE_PATH")
        return cls(
            model_provider=get_agent_setting("AGENT_MODEL_PROVIDER", default="groq"),
            model_name=get_agent_setting(
                "AGENT_MODEL_NAME",
                "GROQ_MODEL",
                default=_DEFAULT_MODEL,
            ),
            temperature=temperature,
            max_tokens=max_tokens,
            top_k=top_k,
            max_tool_calls=max_tool_calls,
            mcp_server_command=get_agent_setting("AGENT_MCP_SERVER_COMMAND", default=sys.executable),
            mcp_server_args=server_args,
            trace_path=Path(raw_trace_path) if raw_trace_path else None,
        )
