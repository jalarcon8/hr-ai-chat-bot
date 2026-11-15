import asyncio

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


def test_synthesis_receives_and_cites_all_policy_and_employee_evidence():
    conflicting_evidence = [
        {
            "document_id": "HR-004",
            "title": "Synthetic Remote Work Policy",
            "section": "2.2 Out-of-State Work",
            "chunk_id": "evidence-1",
            "generation_id": "fixture-generation",
            "snippet": "Written approval is required before travel.",
        },
        {
            "document_id": "HR-004",
            "title": "Synthetic Remote Work Policy",
            "section": "2.2 Out-of-State Work",
            "chunk_id": "evidence-2",
            "generation_id": "fixture-generation",
            "snippet": "No approval is required before travel.",
        },
    ]
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "policy for employee SYN-001"},
                "policy",
            ),
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-001"},
                "profile",
            ),
            final_completion(
                "The candidate policy excerpts conflict, so I cannot resolve the approval "
                "requirement. The employee profile reports a hybrid arrangement."
            ),
        ]
    )
    mcp_client = FakeMCPClient(
        results={
            "search_policy_documents": policy_result(conflicting_evidence),
            "lookup_employee_profile": EMPLOYEE_RESULT,
        }
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request(
            "Compare the policy evidence with the profile for SYN-001."
        )

        assert response.status == "answered"
        assert len(response.citations) == 3
        assert [citation.source_type for citation in response.citations] == [
            "policy_evidence",
            "policy_evidence",
            "tool_result",
        ]
        assert "candidate policy excerpts conflict" in response.answer
        assert "MCP tool lookup_employee_profile" in response.answer
        final_messages = llm_client.requests[-1]["messages"]
        tool_results = [
            message for message in final_messages if message["role"] == "tool"
        ]
        assert len(tool_results) == 2
        assert "evidence-2" in tool_results[0]["content"]
        assert "SYN-001" in tool_results[1]["content"]

    asyncio.run(exercise())


def test_missing_policy_evidence_is_not_presented_as_a_supported_finding():
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "unknown policy"},
                "no-evidence",
            ),
            final_completion("No policy finding can be supported from the returned evidence."),
        ]
    )
    mcp_client = FakeMCPClient(
        results={"search_policy_documents": policy_result([])}
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("What is the unknown policy?")

        assert response.status == "partial"
        assert "no candidate evidence" in response.evidence_limitations
        assert "Evidence limitations:" in response.answer
        assert not response.citations
        assert len(llm_client.requests) == 2

    asyncio.run(exercise())


def test_missing_structured_record_is_preserved_and_reported():
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-MISSING"},
                "missing-profile",
            ),
            final_completion("The requested employee profile was not found."),
        ]
    )
    mcp_client = FakeMCPClient(
        results={
            "lookup_employee_profile": {
                "status": "not_found",
                "missing": "employee",
            }
        }
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("Look up synthetic employee SYN-MISSING.")

        assert response.status == "partial"
        assert response.tool_calls[0].status == "not_found"
        assert "employee was not found" in response.evidence_limitations
        tool_result = llm_client.requests[-1]["messages"][-1]
        assert '"status": "not_found"' in tool_result["content"]

    asyncio.run(exercise())
