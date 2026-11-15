import json
from types import SimpleNamespace

from mcp.types import Tool

from hr_agent.types import LLMCompletion, LLMToolCall

POLICY_EVIDENCE = {
    "document_id": "HR-004",
    "title": "Synthetic Remote Work Policy",
    "section": "2.2 Out-of-State Work",
    "snippet": "Written approval is required before work travel to another state.",
    "chunk_id": "hr-004-out-of-state-1",
    "generation_id": "fixture-generation",
}

EMPLOYEE_RESULT = {
    "status": "found",
    "employee": {
        "employee_id": "SYN-001",
        "name": "Alex Example",
        "role": "Analyst",
        "department": "People Operations",
        "work_arrangement": "hybrid",
        "work_state": "California",
    },
}


def discovered_tools():
    schemas = {
        "search_policy_documents": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "k": {"type": "integer", "minimum": 1},
            },
            "required": ["question"],
            "additionalProperties": False,
        },
        "lookup_employee_profile": {
            "type": "object",
            "properties": {"employee_id": {"type": "string"}},
            "required": ["employee_id"],
            "additionalProperties": False,
        },
        "check_pto_balance": {
            "type": "object",
            "properties": {"employee_id": {"type": "string"}},
            "required": ["employee_id"],
            "additionalProperties": False,
        },
        "draft_hr_email": {
            "type": "object",
            "properties": {
                "recipient_name": {"type": "string", "minLength": 1},
                "purpose": {"type": "string", "minLength": 1},
                "supporting_details": {"type": "string"},
            },
            "required": ["recipient_name", "purpose"],
            "additionalProperties": False,
        },
    }
    return [
        Tool(
            name=name,
            description=f"Discovered tool {name}.",
            inputSchema=schemas.get(
                name,
                {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        )
        for name in (
            "search_policy_documents",
            "get_policy_section",
            "lookup_employee_profile",
            "check_pto_balance",
            "check_policy_compliance",
            "draft_hr_email",
        )
    ]


class FakeMCPClient:
    def __init__(self, *, results=None, failures=None):
        self.tools = discovered_tools()
        self.results = results or {}
        self.failures = failures or {}
        self.calls = []
        self.discover_calls = 0

    async def discover(self):
        self.discover_calls += 1
        return self.tools

    async def call(self, name, arguments):
        self.calls.append((name, arguments))
        failure = self.failures.get(name)
        if failure:
            if isinstance(failure, list):
                current = failure.pop(0)
            else:
                current = failure
            if current is not None:
                raise current
        result = self.results.get(name)
        if isinstance(result, list):
            result = result.pop(0)
        if isinstance(result, BaseException):
            raise result
        return SimpleNamespace(
            isError=bool(isinstance(result, dict) and result.get("_is_error")),
            structuredContent=(
                result.get("structuredContent", result)
                if isinstance(result, dict)
                else result
            ),
        )


class ScriptedLLM:
    def __init__(self, completions):
        self.completions = list(completions)
        self.requests = []

    async def complete(self, messages, tools, *, config):
        self.requests.append({"messages": list(messages), "tools": tools})
        return self.completions.pop(0)


def tool_completion(name, arguments, call_id):
    call = LLMToolCall(call_id=call_id, name=name, arguments=arguments)
    assistant_message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments),
                },
            }
        ],
    }
    return LLMCompletion(None, call, assistant_message)


def final_completion(answer):
    return LLMCompletion(
        answer,
        None,
        {"role": "assistant", "content": answer},
    )


def policy_result(evidence=None):
    return {
        "status": "found" if evidence is None or evidence else "not_found",
        "evidence_kind": "candidate" if evidence is None or evidence else None,
        "evidence": [POLICY_EVIDENCE] if evidence is None else evidence,
        "generation_id": "fixture-generation",
    }
