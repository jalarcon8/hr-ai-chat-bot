import asyncio

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.errors import AgentRuntimeError
from hr_agent.types import LLMCompletion, LLMToolCall
from tests.unit.agent_orchestration_helpers import (
    FakeMCPClient,
    ScriptedLLM,
    tool_completion,
)


def test_multiple_native_tool_calls_are_rejected_before_execution():
    mcp = FakeMCPClient()
    llm = ScriptedLLM([
        LLMCompletion(None, None, {"role": "assistant", "tool_calls": [{"id": "1"}, {"id": "2"}]})
    ])

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        with pytest.raises(AgentRuntimeError, match="multiple_tool_calls"):
            await agent.process_request("Test request.")
        assert not mcp.calls

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "completion",
    [
        LLMCompletion(
            "Please ask People Operations to review.",
            None,
            {"role": "assistant", "content": "Please ask People Operations to review."},
            final_disposition="unsupported",
        ),
        LLMCompletion(
            None,
            LLMToolCall("call-1", "search_policy_documents", {"question": "policy"}),
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "search_policy_documents",
                            "arguments": '{"question":"policy"}',
                        },
                    }
                ],
            },
            final_disposition="human_review_recommended",
        ),
    ],
)
def test_agent_rejects_invalid_or_tool_call_disposition_before_mcp(completion):
    mcp = FakeMCPClient()
    llm = ScriptedLLM([completion])

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        with pytest.raises(AgentRuntimeError, match="invalid_final_disposition"):
            await agent.process_request("Check the synthetic policy.")
        assert not mcp.calls

    asyncio.run(exercise())


def test_trace_write_failure_is_explicit(tmp_path):
    mcp = FakeMCPClient()
    llm = ScriptedLLM([tool_completion("send_email", {}, "unsupported")])

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig(trace_path=tmp_path))
        with pytest.raises(AgentRuntimeError, match="trace_persistence_failure"):
            await agent.process_request("Test request.")
        assert not mcp.calls

    asyncio.run(exercise())


def test_provider_failure_is_reported_and_traced_without_details(tmp_path):
    class FailedLLM:
        async def complete(self, messages, tools, *, config):
            raise AgentRuntimeError("llm_request_failed") from RuntimeError("PRIVATE-PROVIDER-DATA")

    path = tmp_path / "trace.jsonl"

    async def exercise():
        agent = await HRAgent.create(FakeMCPClient(), FailedLLM(), AgentConfig(trace_path=path))
        with pytest.raises(AgentRuntimeError, match="llm_request_failed") as failure:
            await agent.process_request("PRIVATE-QUESTION")
        assert failure.value.__suppress_context__
        trace = path.read_text(encoding="utf-8")
        assert "provider_failure" in trace
        assert "PRIVATE" not in trace

    asyncio.run(exercise())
