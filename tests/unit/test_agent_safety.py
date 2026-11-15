import asyncio

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from tests.unit.agent_orchestration_helpers import (
    FakeMCPClient,
    ScriptedLLM,
    tool_completion,
)


@pytest.mark.parametrize("name", ["send_email", "approve_request", "update_employee", "update_ticket"])
def test_model_proposed_unsupported_operations_are_refused(name):
    mcp = FakeMCPClient()
    llm = ScriptedLLM([tool_completion(name, {}, "unsupported")])

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("Perform the requested action.")
        assert response.status == "out_of_scope"
        assert "cannot" in response.answer
        assert not mcp.calls

    asyncio.run(exercise())
