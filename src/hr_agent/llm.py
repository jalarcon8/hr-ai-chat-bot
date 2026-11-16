"""Minimal Groq adapter for native MCP-schema tool calling."""

from __future__ import annotations

import json
from collections.abc import Sequence
from copy import deepcopy
from typing import Any

from groq import APIError, AsyncGroq, BadRequestError
from mcp.types import Tool

from .config import AgentConfig, get_agent_setting
from .errors import AgentRuntimeError, ProviderRequestError
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


def _bad_request_diagnostic(
    error: BadRequestError, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> dict[str, object]:
    body = error.body
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body = body["error"]
    error_type = body.get("type") if isinstance(body, dict) else None
    error_code = body.get("code") if isinstance(body, dict) else None
    roles: list[str] = []
    pending: set[str] = set()
    seen: set[str] = set()
    calls = results = 0
    matches = True
    for message in messages:
        role = message.get("role")
        roles.append(role if role in ("system", "user", "assistant", "tool") else "other")
        if pending and role != "tool":
            matches = False
        if role == "assistant":
            tool_calls = message.get("tool_calls", [])
            if not isinstance(tool_calls, list):
                matches = False
                continue
            for call in tool_calls:
                calls += 1
                call_id = call.get("id") if isinstance(call, dict) else None
                if not isinstance(call_id, str) or not call_id or call_id in seen:
                    matches = False
                else:
                    seen.add(call_id)
                    pending.add(call_id)
        elif role == "tool":
            results += 1
            call_id = message.get("tool_call_id")
            if not isinstance(call_id, str) or call_id not in pending:
                matches = False
            else:
                pending.remove(call_id)
    return {
        "category": "bad_request",
        "http_status": 400,
        "provider_error_type": (
            error_type if error_type == "invalid_request_error" else "other"
        ),
        "provider_error_code": (
            error_code if error_code == "tool_use_failed" else "other"
        ),
        "endpoint": "chat.completions.create",
        "request_fields": [
            "model", "messages", "tools", "tool_choice", "parallel_tool_calls", "n",
            "temperature", "max_tokens",
        ],
        "tool_definition_count": len(tools),
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "n": 1,
        "response_format_present": False,
        "reasoning_parameters_present": False,
        "message_roles": roles,
        "assistant_tool_call_count": calls,
        "tool_result_count": results,
        "tool_call_result_ids_match": matches and not pending,
    }


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
            api_key = get_agent_setting("GROQ_API_KEY")
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
        except BadRequestError as exc:
            raise ProviderRequestError(
                "llm_request_failed", _bad_request_diagnostic(exc, messages, tools)
            ) from None
        except APIError:
            raise AgentRuntimeError("llm_request_failed") from None

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
        try:
            final_payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AgentRuntimeError("invalid_llm_completion") from exc
        if (
            not isinstance(final_payload, dict)
            or set(final_payload) - {"answer", "final_disposition", "clarification_needed"}
            or "answer" not in final_payload
        ):
            raise AgentRuntimeError("invalid_llm_completion")
        answer = final_payload["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise AgentRuntimeError("invalid_llm_completion")
        final_disposition = final_payload.get("final_disposition")
        if final_disposition not in (None, "human_review_recommended"):
            raise AgentRuntimeError("invalid_final_disposition")
        clarification = final_payload.get("clarification_needed")
        if clarification not in (None, "employee_id") or (
            clarification is not None and final_disposition is not None
        ):
            raise AgentRuntimeError("invalid_clarification")
        return LLMCompletion(
            content=answer.strip(),
            tool_call=None,
            assistant_message=assistant_message,
            final_disposition=final_disposition,
            clarification_needed=clarification,
        )
