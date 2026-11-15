import asyncio

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from tests.unit.agent_orchestration_helpers import (
    EMPLOYEE_RESULT,
    FakeMCPClient,
    ScriptedLLM,
    final_completion,
    policy_result,
    tool_completion,
)


@pytest.mark.parametrize(
    ("first_tool", "second_tool"),
    [
        ("lookup_employee_profile", "search_policy_documents"),
        ("search_policy_documents", "lookup_employee_profile"),
    ],
)
def test_agent_executes_result_dependent_policy_and_employee_sequences(first_tool, second_tool):
    profile_call = tool_completion(
        "lookup_employee_profile",
        {"employee_id": "SYN-001"},
        "profile-call",
    )
    policy_call = tool_completion(
        "search_policy_documents",
        {"question": "policy for the employee's California work location"},
        "policy-call",
    )
    completions = (
        [profile_call, policy_call]
        if first_tool == "lookup_employee_profile"
        else [policy_call, profile_call]
    )
    llm_client = ScriptedLLM(
        [
            *completions,
            final_completion(
                "The profile and candidate policy evidence are both considered below."
            ),
        ]
    )
    mcp_client = FakeMCPClient(
        results={
            "lookup_employee_profile": EMPLOYEE_RESULT,
            "search_policy_documents": policy_result(),
        }
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request(
            "Use the policy evidence and the profile for synthetic employee SYN-001."
        )

        assert response.status == "answered"
        assert [name for name, _ in mcp_client.calls] == [first_tool, second_tool]
        assert len(response.tool_calls) == 2
        assert {citation.source_type for citation in response.citations} == {
            "policy_evidence",
            "tool_result",
        }
        assert "candidate evidence" in response.answer
        assert [
            tool["function"]["name"] for tool in llm_client.requests[0]["tools"]
        ] == [
            "search_policy_documents",
            "lookup_employee_profile",
            "check_pto_balance",
            "draft_hr_email",
        ]
        second_turn_messages = llm_client.requests[1]["messages"]
        assert second_turn_messages[-1]["role"] == "tool"
        third_turn_messages = llm_client.requests[2]["messages"]
        assert [message["role"] for message in third_turn_messages[-4:]] == [
            "assistant",
            "tool",
            "assistant",
            "tool",
        ]

    asyncio.run(exercise())
