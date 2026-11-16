import asyncio
import json

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.errors import AgentRuntimeError
from hr_mcp.client import ClientError
from tests.unit.agent_orchestration_helpers import (
    FakeMCPClient,
    ScriptedLLM,
    final_completion,
    policy_result,
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
            await agent.process_request(
                "Look up synthetic employee 123.", context={"employee_id": "123"}
            )
        assert mcp_client.calls == []

    asyncio.run(exercise())


@pytest.mark.parametrize("tool_name", ["lookup_employee_profile", "check_pto_balance"])
@pytest.mark.parametrize("employee_id", ["SYN-001", "opaque id / #"])
def test_employee_lookup_requires_matching_caller_context(tool_name, employee_id):
    llm = ScriptedLLM([
        tool_completion(tool_name, {"employee_id": employee_id}, "employee"),
        final_completion("The synthetic result was returned."),
    ])
    mcp = FakeMCPClient(results={tool_name: {"status": "found"}})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            "Look up this employee.", context={"employee_id": employee_id}
        )
        assert response.status == "answered"
        assert mcp.calls == [(tool_name, {"employee_id": employee_id})]
        assert employee_id not in json.dumps(response.operational_trace.events)

    asyncio.run(exercise())


@pytest.mark.parametrize("tool_name", ["lookup_employee_profile", "check_pto_balance"])
@pytest.mark.parametrize("context", [None, {}, {"employee_id": None}, {"employee_id": ""},
                                     {"employee_id": "  "}, {"employee_id": 123},
                                     {"employee_id": True},
                                     {"employee_id": ["SYN-001"]}])
def test_employee_lookup_requires_valid_context_even_if_id_is_in_user_text(tool_name, context):
    llm = ScriptedLLM([tool_completion(tool_name, {"employee_id": "SYN-001"}, "employee")])
    mcp = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("Look up employee SYN-001.", context=context)
        assert response.status == "clarification_needed"
        assert "employee identifier" in response.clarification_prompt
        assert not mcp.calls
        assert "SYN-001" not in json.dumps(response.operational_trace.events)

    asyncio.run(exercise())


@pytest.mark.parametrize("tool_name", ["lookup_employee_profile", "check_pto_balance"])
@pytest.mark.parametrize("model_id", ["MODEL-ID", "CALLER-ID ", "caller-id"])
def test_employee_lookup_rejects_mismatched_model_id_before_execution(
    tool_name, model_id, tmp_path
):
    llm = ScriptedLLM([tool_completion(tool_name, {"employee_id": model_id}, "employee")])
    mcp = FakeMCPClient()
    path = tmp_path / "trace.jsonl"

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig(trace_path=path))
        with pytest.raises(AgentRuntimeError, match="employee_id_mismatch"):
            await agent.process_request(
                "Look up this employee.", context={"employee_id": "CALLER-ID"}
            )
        assert not mcp.calls
        trace = path.read_text(encoding="utf-8")
        assert "employee_id_mismatch" in trace
        assert model_id not in trace and "CALLER-ID" not in trace

    asyncio.run(exercise())


def test_context_does_not_fill_in_a_missing_model_tool_argument():
    llm = ScriptedLLM([tool_completion("lookup_employee_profile", {}, "employee")])
    mcp = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            "Look up the employee.", context={"employee_id": "SYN-001"}
        )
        assert response.status == "clarification_needed"
        assert not mcp.calls

    asyncio.run(exercise())


def test_context_binding_is_rechecked_after_successful_employee_lookup():
    llm = ScriptedLLM([
        tool_completion("lookup_employee_profile", {"employee_id": "CALLER-ID"}, "profile"),
        tool_completion("check_pto_balance", {"employee_id": "MODEL-ID"}, "balance"),
    ])
    mcp = FakeMCPClient(results={"lookup_employee_profile": {"status": "found"}})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        with pytest.raises(AgentRuntimeError, match="employee_id_mismatch"):
            await agent.process_request(
                "Check the employee's profile and PTO.", context={"employee_id": "CALLER-ID"}
            )
        assert mcp.calls == [("lookup_employee_profile", {"employee_id": "CALLER-ID"})]

    asyncio.run(exercise())


def test_missing_identity_after_policy_search_does_not_prevent_policy_lookup():
    llm = ScriptedLLM([
        tool_completion("search_policy_documents", {"question": "PTO policy"}, "policy"),
        tool_completion("check_pto_balance", {"employee_id": "SYN-001"}, "employee"),
    ])
    mcp = FakeMCPClient(results={"search_policy_documents": policy_result()})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("What is the PTO policy for SYN-001?")
        assert response.status == "clarification_needed"
        assert [name for name, _ in mcp.calls] == ["search_policy_documents"]

    asyncio.run(exercise())


def test_policy_only_request_does_not_require_valid_employee_context():
    llm = ScriptedLLM([
        tool_completion("search_policy_documents", {"question": "PTO policy"}, "policy"),
        final_completion("The candidate policy evidence is available."),
    ])
    mcp = FakeMCPClient(results={"search_policy_documents": policy_result()})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            "What is the PTO policy?", context={"employee_id": ""}
        )
        assert response.status == "answered"
        assert [name for name, _ in mcp.calls] == ["search_policy_documents"]

    asyncio.run(exercise())


def test_policy_failure_is_not_hidden_by_missing_identity_context():
    llm = ScriptedLLM([
        tool_completion("search_policy_documents", {"question": "PTO policy"}, "policy"),
        tool_completion("check_pto_balance", {"employee_id": "SYN-001"}, "employee"),
    ])
    mcp = FakeMCPClient(failures={"search_policy_documents": ClientError("transport_failure")})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("What is the PTO policy for SYN-001?")
        assert response.status == "error"
        assert response.error_code == "transport_failure"
        assert [name for name, _ in mcp.calls] == ["search_policy_documents"]

    asyncio.run(exercise())
