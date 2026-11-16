import asyncio
import json

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from tests.fixtures.mcp.harness import build_context, connect
from tests.unit.agent_orchestration_helpers import (
    ScriptedLLM,
    final_completion,
    tool_completion,
)

EXPECTED_TOOLS = {
    "search_policy_documents",
    "get_policy_section",
    "lookup_employee_profile",
    "check_pto_balance",
    "check_policy_compliance",
    "draft_hr_email",
}


@pytest.fixture
def context(tmp_path):
    return build_context(tmp_path)


def test_agent_discovers_tools_and_invokes_policy_search_over_mcp(context):
    llm = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {
                    "question": "What approval is required before out-of-state work travel?",
                    "k": 2,
                },
                "policy-search-1",
            ),
            final_completion(
                "Written People Operations approval is required before travel for work in "
                "another US state."
            ),
        ]
    )

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
            assert llm.requests[1]["messages"][-1]["role"] == "tool"
            assert context.calls() == ["search_policy_documents"]

    asyncio.run(exercise())


def test_agent_invokes_five_distinct_tools_over_mcp_with_confirmed_draft(context):
    approval_facts = {
        "status": "approved",
        "authority": "people_operations",
        "format": "written",
        "approval_timestamp": "2026-01-01T00:00:00Z",
        "travel_start_timestamp": "2026-02-01T00:00:00Z",
        "no_other_approvals": True,
    }
    llm = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "What approval is required for out-of-state travel?", "k": 2},
                "all-tools-policy",
            ),
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "TEST-001"},
                "all-tools-profile",
            ),
            tool_completion(
                "check_pto_balance",
                {"employee_id": "TEST-001"},
                "all-tools-pto",
            ),
            tool_completion(
                "check_policy_compliance",
                {
                    "check_id": "out_of_state_prior_approval",
                    "approval_facts": approval_facts,
                },
                "all-tools-compliance",
            ),
            final_completion(
                "Policy search returned candidate evidence, and the synthetic profile, "
                "PTO, and compliance tools returned structured results."
            ),
            tool_completion(
                "draft_hr_email",
                {
                    "recipient_name": "Synthetic Manager",
                    "purpose": "Synthetic policy follow-up",
                    "supporting_details": "This protocol test sends no email.",
                },
                "all-tools-draft",
            ),
        ]
    )

    async def exercise():
        async with connect(context, "provided") as mcp_client:
            agent = await HRAgent.create(
                mcp_client,
                llm,
                AgentConfig(max_tool_calls=4),
            )
            response = await agent.process_request(
                "Use policy evidence and synthetic employee data for TEST-001.",
                context={"employee_id": "TEST-001"},
            )

            assert response.status == "answered"
            assert {citation.source_type for citation in response.citations} == {
                "policy_evidence",
                "tool_result",
            }
            assert [record.tool_name for record in response.tool_calls] == [
                "search_policy_documents",
                "lookup_employee_profile",
                "check_pto_balance",
                "check_policy_compliance",
            ]
            assert all(record.status == "success" for record in response.tool_calls)
            chained_results = [
                json.loads(request["messages"][-1]["content"])
                for request in llm.requests[1:5]
            ]
            assert all(result["status"] == "found" for result in chained_results)
            assert chained_results[0]["evidence"]
            assert "employee" in chained_results[1]
            assert "pto" in chained_results[2]
            assert chained_results[3]["conclusion"] == "compliant"

            draft = await agent.process_request("Prepare a synthetic email draft.")
            assert draft.status == "confirmation_required"
            assert draft.tool_calls[0].tool_name == "draft_hr_email"
            assert draft.tool_calls[0].status == "success"
            confirmed = await agent.confirm_action(
                draft.action_id,
                True,
                {"pending_action": draft.pending_action},
            )
            assert confirmed.status == "answered"
            assert "No email was sent" in confirmed.answer

            expected_calls = [
                "search_policy_documents",
                "lookup_employee_profile",
                "check_pto_balance",
                "check_policy_compliance",
                "draft_hr_email",
            ]
            assert context.calls() == expected_calls
            assert len(set(context.calls())) == 5

    asyncio.run(exercise())


def test_agent_records_human_review_disposition_after_successful_mcp_call(context):
    llm = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "Can this arrangement be approved?", "k": 2},
                "review-policy",
            ),
            final_completion(
                "The candidate evidence does not establish eligibility. Please ask People "
                "Operations to review the arrangement.",
                final_disposition="human_review_recommended",
            ),
        ]
    )

    async def exercise():
        async with connect(context, "provided") as mcp_client:
            agent = await HRAgent.create(mcp_client, llm, AgentConfig())
            response = await agent.process_request(
                "Can this synthetic arrangement be approved?"
            )

            completion_events = [
                event
                for event in response.operational_trace.events
                if event.get("event") == "completion"
            ]
            assert response.status == "partial"
            assert response.citations
            assert response.tool_calls[0].status == "success"
            assert context.calls() == ["search_policy_documents"]
            assert len(llm.requests) == 2
            assert completion_events
            assert all(event["outcome"] == "partial" for event in completion_events)
            assert all(
                event["disposition"] == "human_review_recommended"
                for event in completion_events
            )

    asyncio.run(exercise())
