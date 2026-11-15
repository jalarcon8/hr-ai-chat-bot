import asyncio

import pytest
from mcp.types import Tool

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.errors import AgentInitializationError
from hr_agent.types import LLMCompletion
from hr_mcp.client import ClientError


def _tool(name, schema=None):
    return Tool(
        name=name,
        description=f"Tool {name}.",
        inputSchema=schema
        or {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    )


def _catalog():
    return [
        _tool("search_policy_documents"),
        _tool("lookup_employee_profile"),
        _tool("check_pto_balance"),
        _tool("draft_hr_email"),
    ]


class FakeMCPClient:
    def __init__(self, tools=None, *, discovery_error=None):
        self.tools = tools or _catalog()
        self.discovery_error = discovery_error
        self.discover_calls = 0

    async def discover(self):
        self.discover_calls += 1
        if self.discovery_error is not None:
            raise self.discovery_error
        return self.tools

    async def call(self, name, arguments):
        raise AssertionError("No tool call is expected in this discovery test.")


class FinalLLM:
    async def complete(self, messages, tools, *, config):
        return LLMCompletion(
            content="No evidence was retrieved.",
            tool_call=None,
            assistant_message={"role": "assistant", "content": "No evidence was retrieved."},
        )


def test_agent_discovers_and_refreshes_tools_before_each_request():
    mcp_client = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp_client, FinalLLM(), AgentConfig())
        assert set(agent.available_tool_names) == {
            "search_policy_documents",
            "lookup_employee_profile",
            "check_pto_balance",
            "draft_hr_email",
        }
        response = await agent.process_request("What is the policy?")
        assert response.status == "error"
        assert mcp_client.discover_calls == 2

    asyncio.run(exercise())


def test_agent_reports_mcp_discovery_failure_without_fallback():
    mcp_client = FakeMCPClient(discovery_error=ClientError("transport_failure"))

    async def exercise():
        with pytest.raises(AgentInitializationError, match="mcp_discovery_failed"):
            await HRAgent.create(mcp_client, FinalLLM(), AgentConfig())
        assert mcp_client.discover_calls == 1

    asyncio.run(exercise())


def test_agent_rejects_invalid_discovered_schema():
    tools = _catalog()
    tools[0] = _tool(
        "search_policy_documents",
        {"type": "not-a-json-schema-type", "properties": {}},
    )
    mcp_client = FakeMCPClient(tools)

    async def exercise():
        with pytest.raises(AgentInitializationError, match="invalid_discovered_tool_schema"):
            await HRAgent.create(mcp_client, FinalLLM(), AgentConfig())

    asyncio.run(exercise())


def test_agent_requires_four_discovered_tools():
    mcp_client = FakeMCPClient([_tool("search_policy_documents")])

    async def exercise():
        with pytest.raises(AgentInitializationError, match="insufficient_discovered_tools"):
            await HRAgent.create(mcp_client, FinalLLM(), AgentConfig())

    asyncio.run(exercise())
