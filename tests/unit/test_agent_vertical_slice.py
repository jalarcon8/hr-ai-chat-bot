import asyncio
import json

from mcp.types import Tool

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.types import LLMCompletion, LLMToolCall

EVIDENCE = {
    "document_id": "HR-004",
    "title": "Synthetic Remote Work Policy",
    "section": "2.2 Out-of-State Work",
    "snippet": "Written People Operations approval is required before travel for work in another US state.",
    "chunk_id": "hr-004-out-of-state-1",
    "generation_id": "fixture-generation",
}


def _tool(name):
    properties = {"question": {"type": "string"}}
    required = ["question"]
    if name == "search_policy_documents":
        properties["k"] = {"type": "integer", "minimum": 1, "default": 5}
    else:
        properties = {}
        required = []
    return Tool(
        name=name,
        description=f"Tool {name}.",
        inputSchema={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


def _catalog():
    return [
        _tool("search_policy_documents"),
        _tool("get_policy_section"),
        _tool("lookup_employee_profile"),
        _tool("check_pto_balance"),
        _tool("check_policy_compliance"),
        _tool("draft_hr_email"),
    ]


def _tool_completion(arguments, *, question="What approval is required for out-of-state work?"):
    call = LLMToolCall(
        call_id=f"call-{question}",
        name="search_policy_documents",
        arguments=arguments,
    )
    return LLMCompletion(
        content=None,
        tool_call=call,
        assistant_message={
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": call.call_id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(arguments),
                    },
                }
            ],
        },
    )


class FakeMCPClient:
    def __init__(self, result):
        self.tools = _catalog()
        self.result = result
        self.calls = []
        self.discover_calls = 0

    async def discover(self):
        self.discover_calls += 1
        return self.tools

    async def call(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


class ScriptedLLM:
    def __init__(self, completions):
        self.completions = list(completions)
        self.requests = []

    async def complete(self, messages, tools, *, config):
        self.requests.append((messages.copy(), tools))
        return self.completions.pop(0)


def _search_result(evidence=None, *, status="found"):
    return type(
        "MCPResult",
        (),
        {
            "isError": False,
            "structuredContent": {
                "status": status,
                "evidence": [EVIDENCE] if evidence is None and status == "found" else evidence or [],
                "evidence_kind": "candidate" if status == "found" else None,
            },
        },
    )()


def test_policy_request_uses_llm_selected_mcp_search_and_returns_citations():
    question = "What approval is required for out-of-state work?"
    mcp_client = FakeMCPClient(_search_result())
    llm_client = ScriptedLLM(
        [
            _tool_completion({"question": question}),
            LLMCompletion(
                content="Written People Operations approval is required before the travel.",
                tool_call=None,
                assistant_message={
                    "role": "assistant",
                    "content": "Written People Operations approval is required before the travel.",
                },
            ),
        ]
    )

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig(top_k=2))
        response = await agent.process_request(question)
        assert response.status == "answered"
        assert "HR-004" in response.answer
        assert "2.2 Out-of-State Work" in response.answer
        assert response.citations[0].snippet == EVIDENCE["snippet"]
        assert mcp_client.calls == [
            ("search_policy_documents", {"question": question, "k": 2})
        ]
        assert mcp_client.discover_calls == 2
        assert llm_client.requests[0][1][0]["function"]["name"] == "search_policy_documents"
        tool_message = llm_client.requests[1][0][-1]
        assert tool_message["role"] == "tool"
        assert json.loads(tool_message["content"])["evidence"][0]["document_id"] == "HR-004"
        assert all(
            "question" not in str(event) for event in response.operational_trace.events
        )

    asyncio.run(exercise())


def test_policy_search_without_evidence_returns_limitation_not_a_claim():
    mcp_client = FakeMCPClient(_search_result([], status="not_found"))
    llm_client = ScriptedLLM([_tool_completion({"question": "unknown policy"})])

    async def exercise():
        agent = await HRAgent.create(mcp_client, llm_client, AgentConfig())
        response = await agent.process_request("What is the unknown policy?")
        assert response.status == "partial"
        assert not response.citations
        assert "No supporting policy evidence" in response.answer
        assert response.evidence_limitations
        assert len(llm_client.requests) == 1

    asyncio.run(exercise())


def test_tool_loop_stops_at_configured_call_bound():
    question = "Search policy evidence again."
    repeated = [
        _tool_completion({"question": question}, question=f"{question} {index}")
        for index in range(3)
    ]
    mcp_client = FakeMCPClient(_search_result())
    llm_client = ScriptedLLM(repeated)

    async def exercise():
        agent = await HRAgent.create(
            mcp_client,
            llm_client,
            AgentConfig(max_tool_calls=2),
        )
        response = await agent.process_request(question)
        assert response.status == "partial"
        assert len(mcp_client.calls) == 2
        assert len(llm_client.requests) == 3

    asyncio.run(exercise())
