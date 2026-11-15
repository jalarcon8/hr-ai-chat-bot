import asyncio

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.errors import AgentRuntimeError
from tests.unit.agent_orchestration_helpers import (
    FakeMCPClient,
    ScriptedLLM,
    tool_completion,
)


def test_missing_required_employee_identifier_requests_clarification():
    llm_client = ScriptedLLM(
        [tool_completion("lookup_employee_profile", {}, "missing-id")]
    )
    mcp_client = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("Look up this employee.")

        assert response.status == "clarification_needed"
        assert response.clarification_prompt
        assert "employee identifier" in response.clarification_prompt
        assert mcp_client.calls == []
        assert len(llm_client.requests) == 1

    asyncio.run(exercise())


def test_invalid_discovered_schema_arguments_are_rejected_before_mcp_call():
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": 123},
                "invalid-id",
            )
        ]
    )
    mcp_client = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        with pytest.raises(AgentRuntimeError, match="invalid_tool_arguments"):
            await agent.process_request("Look up synthetic employee 123.")
        assert mcp_client.calls == []

    asyncio.run(exercise())
