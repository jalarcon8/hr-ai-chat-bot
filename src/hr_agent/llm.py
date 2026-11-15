"""Minimal Groq adapter for native MCP-schema tool calling."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from copy import deepcopy
from typing import Any

from groq import AsyncGroq
from mcp.types import Tool

from .config import AgentConfig
from .errors import AgentRuntimeError
from .types import LLMCompletion, LLMToolCall


def mcp_tools_to_provider(tools: Sequence[Tool]) -> list[dict[str, Any]]:
    definitions: list[dict[str, Any]] = []
    for tool in tools:
        if not tool.name or not isinstance(tool.inputSchema, dict):
            raise AgentRuntimeError("invalid_discovered_tool")
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": deepcopy(tool.inputSchema),
                },
            }
        )
    return definitions


class GroqLLMClient:
    def __init__(self) -> None:
        self._client: AsyncGroq | None = None

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        config: AgentConfig,
    ) -> LLMCompletion:
        if config.model_provider.lower() != "groq":
            raise AgentRuntimeError("unsupported_model_provider")
        if self._client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise AgentRuntimeError("missing_llm_credentials")
            self._client = AsyncGroq(api_key=api_key)

        try:
            response = await self._client.chat.completions.create(
                model=config.model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                parallel_tool_calls=False,
                n=1,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
        except Exception as exc:
            raise AgentRuntimeError("llm_request_failed") from exc

        if not response.choices:
            raise AgentRuntimeError("empty_llm_response")
        message = response.choices[0].message
        calls = message.tool_calls or []
        if len(calls) > 1:
            raise AgentRuntimeError("multiple_tool_calls")

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": message.content,
        }
        if calls:
            call = calls[0]
            if not call.id or not call.function.name:
                raise AgentRuntimeError("invalid_tool_call")
            try:
                arguments = json.loads(call.function.arguments)
            except (TypeError, json.JSONDecodeError) as exc:
                raise AgentRuntimeError("invalid_tool_arguments") from exc
            if not isinstance(arguments, dict):
                raise AgentRuntimeError("invalid_tool_arguments")
            assistant_message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
            ]
            return LLMCompletion(
                content=message.content,
                tool_call=LLMToolCall(call.id, call.function.name, arguments),
                assistant_message=assistant_message,
            )

        content = message.content
        if not isinstance(content, str) or not content.strip():
            raise AgentRuntimeError("empty_llm_response")
        return LLMCompletion(
            content=content.strip(),
            tool_call=None,
            assistant_message=assistant_message,
        )
