import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from groq import APIStatusError, BadRequestError

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.errors import AgentRuntimeError
from hr_agent.llm import GroqLLMClient
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
        response = await agent.process_request(question, context={"employee_id": "SYN-001"})
        trace = path.read_text(encoding="utf-8")
        for secret in (question, "SYN-001", "Alex Example", "California", "Written approval"):
            assert secret not in trace
        assert "HR-004" in trace
        assert "tool_evidence" in trace
        assert response.status == "answered"
        assert all(
            "disposition" not in event
            for event in response.operational_trace.events
            if event.get("event") == "completion"
        )

    asyncio.run(exercise())


def test_human_review_disposition_is_recorded_without_answer_or_private_data(tmp_path):
    private_answer = (
        "The evidence is insufficient. Please ask People Operations to review "
        "PRIVATE-ANSWER-DETAIL."
    )
    mcp = FakeMCPClient(results={"search_policy_documents": policy_result()})
    llm = ScriptedLLM(
        [
            tool_completion(
                "search_policy_documents",
                {"question": "Can this employee work remotely?"},
                "remote-policy",
            ),
            final_completion(
                private_answer,
                final_disposition="human_review_recommended",
            ),
        ]
    )
    path = tmp_path / "trace.jsonl"

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig(trace_path=path))
        response = await agent.process_request(
            "Can this synthetic employee work remotely?"
        )
        events = [
            event
            for event in response.operational_trace.events
            if event.get("event") == "completion"
        ]
        trace_contents = path.read_text(encoding="utf-8")

        assert response.status == "partial"
        assert "People Operations to review" in response.answer
        assert not hasattr(response, "final_disposition")
        assert events
        assert all(event["outcome"] == "partial" for event in events)
        assert all(
            event["disposition"] == "human_review_recommended" for event in events
        )
        assert private_answer not in trace_contents
        assert "PRIVATE-ANSWER-DETAIL" not in trace_contents

    asyncio.run(exercise())


@pytest.mark.parametrize("http_status", [400, 401, 429])
def test_provider_diagnostic_is_persisted_without_provider_or_employee_data(tmp_path, http_status):
    private = "PRIVATE-REQUEST-PROVIDER-EMPLOYEE-DETAIL"
    request = httpx.Request("POST", "https://example.invalid/chat/completions")
    response = httpx.Response(http_status, request=request)
    error_class = BadRequestError if http_status == 400 else APIStatusError
    error = error_class(
        private,
        response=response,
        body={"error": {"type": "invalid_request_error", "code": "tool_use_failed",
                        "message": private}},
    )

    class FakeCompletions:
        async def create(self, **kwargs):
            raise error

    client = GroqLLMClient()
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    path = tmp_path / "trace.jsonl"

    async def exercise():
        agent = await HRAgent.create(FakeMCPClient(), client, AgentConfig(trace_path=path))
        with pytest.raises(AgentRuntimeError, match="llm_request_failed"):
            await agent.process_request(private)
        persisted = path.read_text(encoding="utf-8")
        assert private not in persisted
        event = json.loads(persisted)["events"][-1]
        assert event["outcome"] == "provider_failure"
        diagnostic = event["provider_diagnostic"]
        assert diagnostic["http_status"] == http_status
        if http_status == 400:
            assert diagnostic["message_roles"] == ["system", "user"]
            assert diagnostic["tool_call_result_ids_match"] is True
            assert diagnostic["tool_definition_count"] == 5

    asyncio.run(exercise())


def test_bad_request_after_tool_result_records_matching_ids_without_raw_messages(tmp_path):
    private = "PRIVATE-EMPLOYEE-CALL-RESULT"
    request = httpx.Request("POST", "https://example.invalid/chat/completions")
    response = httpx.Response(400, request=request)
    error = BadRequestError(
        private,
        response=response,
        body={"message": private, "type": private, "code": private},
    )

    class FakeCompletions:
        def __init__(self):
            self.count = 0

        async def create(self, **kwargs):
            self.count += 1
            if self.count > 1:
                raise error
            call = SimpleNamespace(
                id=private,
                function=SimpleNamespace(
                    name="lookup_employee_profile",
                    arguments=json.dumps({"employee_id": private}),
                ),
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=None, tool_calls=[call]
            ))])

    client = GroqLLMClient()
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    path = tmp_path / "trace.jsonl"

    async def exercise():
        mcp = FakeMCPClient(results={"lookup_employee_profile": {
            "status": "found", "employee": {"employee_id": private, "name": private}
        }})
        agent = await HRAgent.create(mcp, client, AgentConfig(trace_path=path))
        with pytest.raises(AgentRuntimeError, match="llm_request_failed"):
            await agent.process_request(private, context={"employee_id": private})
        persisted = path.read_text(encoding="utf-8")
        assert private not in persisted
        diagnostic = json.loads(persisted)["events"][-1]["provider_diagnostic"]
        assert diagnostic["message_roles"] == ["system", "user", "assistant", "tool"]
        assert diagnostic["assistant_tool_call_count"] == diagnostic["tool_result_count"] == 1
        assert diagnostic["tool_call_result_ids_match"] is True
        assert diagnostic["provider_error_type"] == diagnostic["provider_error_code"] == "other"

    asyncio.run(exercise())
