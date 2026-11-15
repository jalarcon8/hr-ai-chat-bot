import asyncio
import sys

import pytest

from hr_mcp.client import ClientError, MCPClient
from tests.fixtures.mcp.protocol_server import MOCK_RESULTS

TOOLS = {
    "search_policy_documents": {"question": "policy"},
    "get_policy_section": {"document_id": "HR-004", "section": "2.2 Out-of-State Work"},
    "lookup_employee_profile": {"employee_id": "TEST-001"},
    "check_pto_balance": {"employee_id": "TEST-001"},
    "check_policy_compliance": {"check_id": "out_of_state_prior_approval"},
    "draft_hr_email": {"recipient_name": "Taylor", "purpose": "PTO"},
}


@pytest.fixture(autouse=True)
def isolate_traces(tmp_path, monkeypatch):
    monkeypatch.setenv("HR_MCP_TRACE_PATH", str(tmp_path / "traces.jsonl"))


def test_real_stdio_discovery_and_six_calls_with_isolated_handlers():
    async def exercise():
        async with MCPClient(
            command=sys.executable,
            args=["-m", "tests.fixtures.mcp.protocol_server"],
        ) as client:
            tools = await client.discover()
            assert {tool.name for tool in tools} == set(TOOLS)
            for tool in tools:
                assert tool.description
                assert set(tool.inputSchema["required"]) == set(TOOLS[tool.name])
                properties = tool.inputSchema["properties"]
                for required in tool.inputSchema["required"]:
                    assert properties[required]["type"] == "string"
                result = await client.call(tool.name, TOOLS[tool.name])
                assert result.isError is not True
                assert result.structuredContent == MOCK_RESULTS[tool.name]
            with pytest.raises(ClientError, match="unknown_tool"):
                await client.call("unknown_tool", {})

    asyncio.run(exercise())


def test_unavailable_stdio_server_is_not_reported_as_success(tmp_path):
    async def exercise():
        with pytest.raises(ClientError, match="transport_failure"):
            async with MCPClient(command=str(tmp_path / "missing-server.exe")):
                pytest.fail("unavailable server connected successfully")

    asyncio.run(exercise())
