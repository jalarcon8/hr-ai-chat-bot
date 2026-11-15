import asyncio
import json
from types import SimpleNamespace

import pytest
from mcp.types import Tool

from hr_agent.config import AgentConfig
from hr_agent.errors import AgentRuntimeError
from hr_agent.llm import GroqLLMClient, mcp_tools_to_provider


def test_model_config_prefers_agent_override_then_groq_model(monkeypatch):
    monkeypatch.delenv("AGENT_MODEL_NAME", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    assert AgentConfig.from_environment().model_name == AgentConfig().model_name
    monkeypatch.setenv("GROQ_MODEL", "groq-override")
    assert AgentConfig.from_environment().model_name == "groq-override"
    monkeypatch.setenv("AGENT_MODEL_NAME", "agent-override")
    assert AgentConfig.from_environment().model_name == "agent-override"


def _message(*, content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tool_call(arguments, *, name="search_policy_documents", call_id="call-1"):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_mcp_schema_converts_to_native_provider_tool():
    mcp_tool = Tool(
        name="search_policy_documents",
        description="Find policy evidence.",
        inputSchema={
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
            "additionalProperties": False,
        },
    )

    converted = mcp_tools_to_provider([mcp_tool])

    assert converted == [
        {
            "type": "function",
            "function": {
                "name": "search_policy_documents",
                "description": "Find policy evidence.",
                "parameters": {
                    "type": "object",
                    "properties": {"question": {"type": "string"}},
                    "required": ["question"],
                    "additionalProperties": False,
                },
            },
        }
    ]
    assert converted[0]["function"]["parameters"] is not mcp_tool.inputSchema


def test_groq_adapter_serializes_tool_result_and_requests_one_sequential_call(monkeypatch):
    calls = [
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=_message(
                        tool_calls=[
                            _tool_call('{"question":"travel approval"}'),
                        ]
                    )
                )
            ]
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(message=_message(content="Written approval is required."))]
        ),
    ]
    requests = []

    class FakeCompletions:
        async def create(self, **kwargs):
            requests.append(kwargs)
            return calls.pop(0)

    class FakeGroq:
        def __init__(self, *, api_key):
            assert api_key == "test-key"
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("hr_agent.llm.AsyncGroq", FakeGroq)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    config = AgentConfig()
    client = GroqLLMClient()
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_policy_documents",
                "description": "Find policy evidence.",
                "parameters": {"type": "object", "properties": {}},
            },
        }
    ]

    async def exercise():
        first = await client.complete(
            [{"role": "user", "content": "What is the travel policy?"}],
            tools,
            config=config,
        )
        assert first.tool_call is not None
        assert first.tool_call.arguments == {"question": "travel approval"}

        messages = [
            {"role": "user", "content": "What is the travel policy?"},
            first.assistant_message,
            {
                "role": "tool",
                "tool_call_id": first.tool_call.call_id,
                "content": json.dumps({"status": "found"}),
            },
        ]
        final = await client.complete(messages, tools, config=config)
        assert final.tool_call is None
        assert final.content == "Written approval is required."

    asyncio.run(exercise())

    assert len(requests) == 2
    for request in requests:
        assert request["n"] == 1
        assert request["parallel_tool_calls"] is False
        assert request["model"] == config.model_name
    assert requests[1]["messages"][1]["tool_calls"][0]["id"] == "call-1"
    assert requests[1]["messages"][2]["role"] == "tool"


def test_groq_adapter_rejects_multiple_tool_calls(monkeypatch):
    calls = [
        _tool_call('{"question":"one"}', call_id="call-1"),
        _tool_call('{"question":"two"}', call_id="call-2"),
    ]

    class FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=_message(tool_calls=calls))]
            )

    class FakeGroq:
        def __init__(self, *, api_key):
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setattr("hr_agent.llm.AsyncGroq", FakeGroq)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    client = GroqLLMClient()

    async def exercise():
        with pytest.raises(AgentRuntimeError, match="multiple_tool_calls"):
            await client.complete([], [], config=AgentConfig())

    asyncio.run(exercise())


def test_groq_adapter_requires_environment_credential(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    async def exercise():
        with pytest.raises(AgentRuntimeError, match="missing_llm_credentials"):
            await GroqLLMClient().complete([], [], config=AgentConfig())

    asyncio.run(exercise())
