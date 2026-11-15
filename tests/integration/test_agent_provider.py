"""Opt-in live validation of native tool calling for the configured Groq model."""

import asyncio
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from hr_agent.config import AgentConfig, get_agent_setting
from hr_agent.errors import AgentRuntimeError
from hr_agent.llm import GroqLLMClient, mcp_tools_to_provider
from tests.fixtures.mcp.harness import build_context, connect


def test_configured_provider_model_supports_tool_calling(tmp_path):
    if get_agent_setting("AGENT_RUN_PROVIDER_SMOKE") != "1":
        pytest.skip("Set AGENT_RUN_PROVIDER_SMOKE=1 to run the live provider check.")
    if not get_agent_setting("GROQ_API_KEY"):
        pytest.skip("BLOCKED: GROQ_API_KEY is not configured.")
    if AgentConfig.from_environment().model_provider.lower() != "groq":
        pytest.fail("Configured provider is not supported by the Milestone 1 Groq adapter.")

    config = AgentConfig.from_environment()
    llm_client = GroqLLMClient()
    context = build_context(tmp_path)

    async def exercise():
        async with connect(context, "provided") as mcp_client:
            discovered = await mcp_client.discover()
            policy_tool = next(
                (tool for tool in discovered if tool.name == "search_policy_documents"),
                None,
            )
            if policy_tool is None:
                pytest.fail("MCP discovery did not provide search_policy_documents.")
            tools = mcp_tools_to_provider([policy_tool])
            messages = [
                {
                    "role": "system",
                    "content": (
                        "For the user's HR policy question, call search_policy_documents once. "
                        "After receiving its result, provide a concise answer using only that "
                        "evidence and finish without another tool call."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "What written approval is required before work travel to another "
                        "US state?"
                    ),
                },
            ]
            selected = await llm_client.complete(messages, tools, config=config)
            if selected.tool_call is None:
                pytest.fail("Provider did not return a native tool call for the policy request.")
            if selected.tool_call.name != policy_tool.name:
                pytest.fail("Provider selected a tool other than search_policy_documents.")
            try:
                Draft202012Validator(policy_tool.inputSchema).validate(
                    selected.tool_call.arguments
                )
            except ValidationError:
                pytest.fail("Provider arguments do not match the discovered MCP schema.")
            question = selected.tool_call.arguments.get("question")
            if not isinstance(question, str) or not question.strip():
                pytest.fail("Provider returned no usable policy-search question.")

            result = await mcp_client.call(
                selected.tool_call.name,
                selected.tool_call.arguments,
            )
            if result.isError or not isinstance(result.structuredContent, dict):
                pytest.fail("MCP policy search did not return a structured success.")
            messages.extend(
                [
                    selected.assistant_message,
                    {
                        "role": "tool",
                        "tool_call_id": selected.tool_call.call_id,
                        "content": json.dumps(result.structuredContent, ensure_ascii=False),
                    },
                ]
            )
            final = await llm_client.complete(messages, tools, config=config)
            if final.tool_call is not None:
                pytest.fail("Provider did not finish synthesis after receiving the MCP result.")
            if not final.content or not final.content.strip():
                pytest.fail("Provider returned no final response after receiving the MCP result.")

    try:
        asyncio.run(exercise())
    except AgentRuntimeError as exc:
        pytest.fail(f"Configured provider/model check failed: {exc.code}", pytrace=False)
