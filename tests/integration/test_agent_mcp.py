import asyncio
import json

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.types import LLMCompletion, LLMToolCall
from tests.fixtures.mcp.harness import build_context, connect

EXPECTED_TOOLS = {
    "search_policy_documents",
    "get_policy_section",
    "lookup_employee_profile",
    "check_pto_balance",
    "check_policy_compliance",
    "draft_hr_email",
}


class PolicySearchLLM:
    def __init__(self):
        self.requests = []

    async def complete(self, messages, tools, *, config):
        self.requests.append((messages.copy(), tools))
        if len(self.requests) == 1:
            arguments = {
                "question": "What approval is required before out-of-state work travel?",
                "k": 2,
            }
            call = LLMToolCall(
                call_id="policy-search-1",
                name="search_policy_documents",
                arguments=arguments,
            )
            return LLMCompletion(
                content=None,
                tool_call=call,
                assistant_message={
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call.call_id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(arguments),
                            },
                        }
                    ],
                },
            )

        tool_result = json.loads(self.requests[-1][0][-1]["content"])
        assert tool_result["status"] == "found"
        assert tool_result["evidence"]
        return LLMCompletion(
            content=(
                "Written People Operations approval is required before travel for work in "
                "another US state."
            ),
            tool_call=None,
            assistant_message={
                "role": "assistant",
                "content": (
                    "Written People Operations approval is required before travel for work in "
                    "another US state."
                ),
            },
        )


@pytest.fixture
def context(tmp_path):
    return build_context(tmp_path)


def test_agent_discovers_tools_and_invokes_policy_search_over_mcp(context):
    llm = PolicySearchLLM()

    async def exercise():
        async with connect(context, "provided") as mcp_client:
            discovered = await mcp_client.discover()
            assert len(discovered) >= 4
            assert {tool.name for tool in discovered} == EXPECTED_TOOLS
            assert all(tool.description and tool.inputSchema["type"] == "object" for tool in discovered)
            agent = await HRAgent.create(mcp_client, llm, AgentConfig(top_k=2))
            assert set(agent.available_tool_names) == EXPECTED_TOOLS
            response = await agent.process_request(
                "What approval is required before out-of-state work travel?"
            )
            assert response.status == "answered"
            assert "Written People Operations approval" in response.answer
            assert response.citations
            assert response.citations[0].document_id == "HR-004"
            assert response.citations[0].section == "2.2 Out-of-State Work"
            assert response.citations[0].snippet
            assert [record.tool_name for record in response.tool_calls] == [
                "search_policy_documents"
            ]
            assert response.operational_trace.events[0]["tool_count"] == 6
            assert len(llm.requests) == 2
            assert llm.requests[1][0][-1]["role"] == "tool"
            assert context.calls() == ["search_policy_documents"]

    asyncio.run(exercise())
