import asyncio
import json

import pytest

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


@pytest.mark.parametrize(
    "question",
    [
        "What does the handbook say about workplace conduct?",
        "How does the remote-work policy describe out-of-state work?",
        "Which policy covers reimbursement documentation?",
    ],
)
def test_policy_only_acceptance_requests_use_only_policy_search(question):
    mcp_client = FakeMCPClient(results={"search_policy_documents": policy_result()})
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": question, "k": 3},
                f"policy-{len(question)}",
            ),
            final_completion("The candidate policy evidence is returned for review."),
        ]
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request(question)

        assert response.status == "answered"
        assert response.citations
        assert [name for name, _ in mcp_client.calls] == ["search_policy_documents"]

    asyncio.run(exercise())


def _employee_result(employee_id):
    return {
        "status": "found",
        "employee": {
            "employee_id": employee_id,
            "name": "Synthetic Fixture",
            "role": "Analyst",
            "department": "Operations",
            "work_arrangement": "hybrid",
            "work_state": "CA",
        },
    }


@pytest.mark.parametrize(
    ("tool_name", "arguments", "result"),
    [
        (
            "lookup_employee_profile",
            {"employee_id": "TEST-001"},
            _employee_result("TEST-001"),
        ),
        (
            "lookup_employee_profile",
            {"employee_id": "TEST-002"},
            _employee_result("TEST-002"),
        ),
        (
            "check_pto_balance",
            {"employee_id": "TEST-001"},
            {
                "status": "found",
                "pto": {
                    "employee_id": "TEST-001",
                    "available_hours": 40,
                    "as_of": "2026-01-01",
                },
            },
        ),
    ],
)
def test_structured_data_acceptance_requests_use_the_selected_tool(
    tool_name, arguments, result
):
    mcp_client = FakeMCPClient(results={tool_name: result})
    llm_client = ScriptedLLM(
        [
            tool_completion(tool_name, arguments, "data-lookup"),
            final_completion("The requested synthetic structured result was returned."),
        ]
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("Look up the requested synthetic record.")

        assert response.status == "answered"
        assert response.citations
        assert [name for name, _ in mcp_client.calls] == [tool_name]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("scenario", "calls"),
    [
        (
            "profile-then-policy",
            [
                ("lookup_employee_profile", {"employee_id": "TEST-001"}),
                ("search_policy_documents", {"question": "remote work policy", "k": 2}),
            ],
        ),
        (
            "policy-then-profile",
            [
                ("search_policy_documents", {"question": "policy for TEST-001", "k": 2}),
                ("lookup_employee_profile", {"employee_id": "TEST-001"}),
            ],
        ),
        (
            "pto-then-policy",
            [
                ("check_pto_balance", {"employee_id": "TEST-001"}),
                ("search_policy_documents", {"question": "PTO policy", "k": 2}),
            ],
        ),
    ],
)
def test_multistep_acceptance_requests_pass_each_result_to_the_next_turn(scenario, calls):
    results = {
        "lookup_employee_profile": EMPLOYEE_RESULT,
        "check_pto_balance": {
            "status": "found",
            "pto": {
                "employee_id": "TEST-001",
                "available_hours": 40,
                "as_of": "2026-01-01",
            },
        },
        "search_policy_documents": policy_result(),
    }
    llm_client = ScriptedLLM(
        [
            *[
                tool_completion(name, arguments, f"{scenario}-{index}")
                for index, (name, arguments) in enumerate(calls)
            ],
            final_completion("The policy and structured results were considered together."),
        ]
    )
    mcp_client = FakeMCPClient(results=results)

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("Combine policy evidence with synthetic data.")

        assert response.status == "answered"
        assert {citation.source_type for citation in response.citations} == {
            "policy_evidence",
            "tool_result",
        }
        assert [name for name, _ in mcp_client.calls] == [name for name, _ in calls]
        assert len(response.tool_calls) == len(calls)
        for index in range(1, len(calls)):
            previous_turn = llm_client.requests[index]["messages"]
            assert previous_turn[-1]["role"] == "tool"
            previous_result = json.loads(previous_turn[-1]["content"])
            assert previous_result == results[calls[index - 1][0]]

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("tool_name", "user_request"),
    [
        ("lookup_employee_profile", "Look up this employee."),
        ("check_pto_balance", "Check the employee's PTO balance."),
    ],
)
def test_missing_required_identifiers_are_clarified_without_tool_calls(
    tool_name, user_request
):
    llm_client = ScriptedLLM([tool_completion(tool_name, {}, f"missing-{tool_name}")])
    mcp_client = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request(user_request)

        assert response.status == "clarification_needed"
        assert response.clarification_prompt
        assert not mcp_client.calls

    asyncio.run(exercise())


@pytest.mark.parametrize("conflicting", [False, True])
def test_evidence_limitations_are_preserved(conflicting):
    if conflicting:
        evidence = [
            {
                **policy_result()["evidence"][0],
                "snippet": "Written approval is required before travel.",
            },
            {
                **policy_result()["evidence"][0],
                "chunk_id": "conflicting-evidence",
                "snippet": "No approval is required before travel.",
            },
        ]
        result = policy_result(evidence)
        answer = "The candidate policy excerpts conflict and cannot be resolved."
    else:
        result = policy_result([])
        answer = "No policy finding can be supported from the returned evidence."

    llm_client = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "What approval is required?"},
                f"evidence-{conflicting}",
            ),
            final_completion(answer),
        ]
    )
    mcp_client = FakeMCPClient(results={"search_policy_documents": result})

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("What approval is required?")

        assert response.status in {"answered", "partial"}
        if conflicting:
            assert "conflict" in response.answer
            assert len(response.citations) == 2
        else:
            assert response.status == "partial"
            assert response.evidence_limitations
            assert not response.citations

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (ClientError("transport_failure"), "error"),
        (TimeoutError(), "timeout"),
    ],
)
def test_tool_failures_are_reported_without_success_shaped_results(failure, expected_status):
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "TEST-001"},
                f"failure-{expected_status}",
            ),
            final_completion("The requested profile is unavailable."),
        ]
    )
    mcp_client = FakeMCPClient(
        failures={"lookup_employee_profile": [failure]},
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("Look up synthetic employee TEST-001.")

        assert response.status == "error"
        assert response.tool_calls[0].status in {"error", "timeout"}
        assert response.tool_calls[0].status == expected_status
        assert response.error_code

    asyncio.run(exercise())


def test_acceptance_trace_has_observable_fields_without_sensitive_values(tmp_path):
    private_values = (
        "PRIVATE_TRACE_QUESTION",
        "PRIVATE_TRACE_EMPLOYEE",
        "PRIVATE_TRACE_RECORD",
        "PRIVATE_TRACE_CREDENTIAL",
        "PRIVATE_TRACE_API_KEY",
    )
    question, employee_id, employee_name, private_record, credential = private_values
    result = _employee_result(employee_id)
    result["employee"]["name"] = employee_name
    result["employee"]["internal_record"] = private_record
    result["employee"]["api_key"] = credential
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": employee_id},
                "trace-profile",
            ),
            tool_completion(
                "search_policy_documents",
                {"question": question},
                "trace-policy",
            ),
            final_completion("The synthetic profile and policy evidence were returned."),
        ]
    )
    mcp_client = FakeMCPClient(
        results={
            "lookup_employee_profile": result,
            "search_policy_documents": policy_result(),
        }
    )
    trace_path = tmp_path / "agent-trace.jsonl"

    async def exercise():
        agent = await HRAgent.create(
            mcp_client,
            llm_client,
            AgentConfig(trace_path=trace_path),
        )
        response = await agent.process_request(question)
        trace = json.dumps(response.operational_trace.events) + trace_path.read_text(
            encoding="utf-8"
        )
        tool_events = [
            event
            for event in response.operational_trace.events
            if event.get("event") == "tool_call"
        ]

        assert response.status == "answered"
        assert {event["tool"] for event in tool_events} == {
            "lookup_employee_profile",
            "search_policy_documents",
        }
        assert all("arguments_summary" in event for event in tool_events)
        assert any(event.get("source_refs") for event in tool_events)
        assert all(value not in trace for value in private_values)
        assert all(employee_id not in str(event["arguments_summary"]) for event in tool_events)

    asyncio.run(exercise())


def test_draft_confirmation_and_unsupported_action_refusal():
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "draft_hr_email",
                {"recipient_name": "Synthetic Manager", "purpose": "Synthetic follow-up"},
                "draft-proposal",
            ),
            tool_completion("send_email", {}, "unsupported-send"),
        ]
    )
    mcp_client = FakeMCPClient(
        results={
            "draft_hr_email": {
                "status": "found",
                "draft": {"subject": "Synthetic follow-up", "body": "Synthetic draft only."},
            }
        }
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        proposal = await agent.process_request("Prepare a synthetic HR email draft.")
        confirmed = await agent.confirm_action(
            proposal.action_id,
            True,
            {"pending_action": proposal.pending_action},
        )
        refused = await agent.process_request("Send the email.")

        assert proposal.status == "confirmation_required"
        assert confirmed.status == "answered"
        assert "No email was sent" in confirmed.answer
        assert refused.status == "out_of_scope"
        assert len(mcp_client.calls) == 1
        assert mcp_client.calls[0][0] == "draft_hr_email"

    asyncio.run(exercise())


def test_failed_call_is_not_retried_until_a_new_request():
    arguments = {"employee_id": "TEST-001"}
    llm_client = ScriptedLLM(
        [
            tool_completion("lookup_employee_profile", arguments, "first-attempt"),
            tool_completion("lookup_employee_profile", arguments, "same-request-retry"),
            tool_completion("lookup_employee_profile", arguments, "new-request-retry"),
            final_completion("The synthetic profile was retrieved on the new request."),
        ]
    )
    mcp_client = FakeMCPClient(
        results={"lookup_employee_profile": EMPLOYEE_RESULT},
        failures={"lookup_employee_profile": [ClientError("transport_failure"), None]},
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        first = await agent.process_request("Look up synthetic employee TEST-001.")
        second = await agent.process_request("Retry the lookup for TEST-001.")

        assert first.status == "error"
        assert any(
            event.get("outcome") == "automatic_retry_suppressed"
            for event in first.operational_trace.events
        )
        assert second.status == "answered"
        assert [name for name, _ in mcp_client.calls] == [
            "lookup_employee_profile",
            "lookup_employee_profile",
        ]

    asyncio.run(exercise())
