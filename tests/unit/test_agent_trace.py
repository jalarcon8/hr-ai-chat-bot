import asyncio
import json

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


def test_draft_trace_is_persisted_without_request_arguments_or_draft(tmp_path):
    secret = "PRIVATE-REQUEST-CREDENTIAL-DRAFT-BODY"
    mcp = FakeMCPClient(
        results={"draft_hr_email": {"status": "found", "draft": {"subject": secret, "body": secret}}}
    )
    llm = ScriptedLLM(
        [tool_completion("draft_hr_email", {"recipient_name": secret, "purpose": secret}, "one")]
    )
    path = tmp_path / "trace.jsonl"

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig(trace_path=path))
        response = await agent.process_request(secret)
        encoded = json.dumps(response.operational_trace.events)
        persisted = path.read_text(encoding="utf-8")
        for value in (secret, "PRIVATE", "internal prompt", "chain-of-thought"):
            assert value not in encoded and value not in persisted
        events = response.operational_trace.events
        call = next(event for event in events if event["event"] == "tool_call")
        assert call["tool"] == "draft_hr_email"
        assert call["arguments_summary"]["argument_names"] == ["purpose", "recipient_name"]
        assert call["result_summary"]["outcome"] == "found"
        assert events[-1]["answer_basis"] == "draft_confirmation"

    asyncio.run(exercise())


def test_employee_and_policy_trace_excludes_raw_records_and_question(tmp_path):
    question = "PRIVATE full employee question"
    mcp = FakeMCPClient(
        results={"lookup_employee_profile": EMPLOYEE_RESULT, "search_policy_documents": policy_result()}
    )
    llm = ScriptedLLM(
        [
            tool_completion("lookup_employee_profile", {"employee_id": "SYN-001"}, "employee"),
            tool_completion("search_policy_documents", {"question": question}, "policy"),
            final_completion("A fictional profile and candidate policy evidence were returned."),
        ]
    )
    path = tmp_path / "trace.jsonl"

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig(trace_path=path))
        response = await agent.process_request(question)
        trace = path.read_text(encoding="utf-8")
        for secret in (question, "SYN-001", "Alex Example", "California", "Written approval"):
            assert secret not in trace
        assert "HR-004" in trace
        assert "tool_evidence" in trace
        assert response.status == "answered"

    asyncio.run(exercise())
