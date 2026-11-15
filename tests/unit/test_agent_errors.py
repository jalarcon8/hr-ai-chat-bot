import asyncio

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_mcp.client import ClientError
from tests.unit.agent_orchestration_helpers import (
    EMPLOYEE_RESULT,
    FakeMCPClient,
    ScriptedLLM,
    final_completion,
    policy_result,
    tool_completion,
)


def test_tool_failure_is_partial_and_a_new_request_can_try_again():
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "policy for SYN-001"},
                "policy",
            ),
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-001"},
                "profile-fails",
            ),
            final_completion(
                "Candidate policy evidence was retrieved, but the employee profile is unavailable."
            ),
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-001"},
                "profile-retry-new-request",
            ),
            final_completion("The synthetic employee profile was retrieved."),
        ]
    )
    mcp_client = FakeMCPClient(
        results={
            "search_policy_documents": policy_result(),
            "lookup_employee_profile": EMPLOYEE_RESULT,
        },
        failures={
            "lookup_employee_profile": [
                ClientError("transport_failure"),
                None,
            ]
        },
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        first_response = await agent.process_request(
            "Use policy evidence and the profile for SYN-001."
        )

        assert first_response.status == "partial"
        assert first_response.tool_calls[0].status == "success"
        assert first_response.tool_calls[1].status == "error"
        assert "transport_failure" in first_response.evidence_limitations
        assert "unavailable" in first_response.answer
        assert [name for name, _ in mcp_client.calls] == [
            "search_policy_documents",
            "lookup_employee_profile",
        ]
        assert "SYN-001" not in str(first_response.operational_trace.events)
        assert "Alex Example" not in str(first_response.operational_trace.events)
        failure_message = llm_client.requests[2]["messages"][-1]
        assert '"status": "error"' in failure_message["content"]

        second_response = await agent.process_request(
            "Retry the profile lookup for synthetic employee SYN-001."
        )
        assert second_response.status == "answered"
        assert [name for name, _ in mcp_client.calls] == [
            "search_policy_documents",
            "lookup_employee_profile",
            "lookup_employee_profile",
        ]

    asyncio.run(exercise())


def test_model_reselection_does_not_retry_failed_call_in_same_request():
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-001"},
                "first-profile",
            ),
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-001"},
                "duplicate-profile",
            ),
        ]
    )
    mcp_client = FakeMCPClient(
        failures={
            "lookup_employee_profile": [ClientError("transport_failure")]
        }
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request(
            "Look up the profile for SYN-001."
        )

        assert response.status == "error"
        assert response.error_code == "mcp_tool_call_failed"
        assert len(mcp_client.calls) == 1
        assert response.operational_trace.events[-1]["outcome"] == "automatic_retry_suppressed"

    asyncio.run(exercise())


def test_tool_timeout_is_reported_as_partial_failure():
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "policy for SYN-001"},
                "policy",
            ),
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-001"},
                "profile-timeout",
            ),
            final_completion("The profile is unavailable because its lookup timed out."),
        ]
    )
    mcp_client = FakeMCPClient(
        results={"search_policy_documents": policy_result()},
        failures={"lookup_employee_profile": [TimeoutError()]},
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request(
            "Use policy evidence and the profile for SYN-001."
        )

        assert response.status == "partial"
        assert response.tool_calls[1].status == "timeout"
        assert "failed (timeout)" in response.evidence_limitations

    asyncio.run(exercise())
