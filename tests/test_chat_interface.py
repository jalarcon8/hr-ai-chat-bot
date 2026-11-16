import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from hr_agent.config import AgentConfig
from hr_agent.errors import AgentError
from hr_agent.types import (
    AgentResponse,
    Citation,
    OperationalTrace,
    ToolInvocationRecord,
)
from hr_app import runtime
from hr_app.app import PTO_PROMPT, REMOTE_WORK_PROMPT
from hr_mcp.client import ClientError
from tests.unit.agent_orchestration_helpers import (
    EMPLOYEE_RESULT,
    FakeMCPClient,
    ScriptedLLM,
    final_completion,
    tool_completion,
)

APP_PATH = Path(__file__).parents[1] / "src" / "hr_app" / "app.py"


class ContextMCPClient(FakeMCPClient):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


def test_chat_submits_current_question_through_hr_agent(monkeypatch):
    mcp_client = ContextMCPClient(results={"lookup_employee_profile": EMPLOYEE_RESULT})
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "lookup_employee_profile",
                {"employee_id": "SYN-001"},
                "profile",
            ),
            final_completion("The synthetic profile belongs to Alex Example."),
        ]
    )
    monkeypatch.setattr(runtime, "MCPClient", lambda **kwargs: mcp_client)
    monkeypatch.setattr(runtime, "GroqLLMClient", lambda: llm_client)

    app = AppTest.from_file(str(APP_PATH)).run()
    try:
        app.text_input[0].set_value("SYN-001").run()
        app.chat_input[0].set_value("What does my employee profile show?").run()

        assert any(
            "The synthetic profile belongs to Alex Example." in item.value
            for item in app.markdown
        )
        assert any("Status: answered" in item.value for item in app.caption)
        assert [name for name, _ in mcp_client.calls] == ["lookup_employee_profile"]
        user_request = json.loads(llm_client.requests[0]["messages"][1]["content"])
        assert user_request == {
            "request": "What does my employee profile show?",
            "context": {"employee_id": "SYN-001"},
        }
    finally:
        app.session_state["agent_session"].close()


def _click_button(app, label):
    button = next(item for item in app.button if item.label == label)
    button.click().run()


class RecordingAgentSession:
    def __init__(self, response=None, error=None):
        self.response = response or AgentResponse("Request received.", "answered")
        self.error = error
        self.requests = []
        self.confirmations = []

    def process_request(self, user_input, context=None):
        self.requests.append((user_input, context))
        if self.error is not None:
            raise self.error
        return self.response

    def confirm_action(self, action_id, confirmation, context):
        self.confirmations.append((action_id, confirmation, context))
        return AgentResponse("The draft was confirmed. No email was sent.", "answered")


def test_evidence_and_trace_render_only_allowlisted_fields(monkeypatch):
    response = AgentResponse(
        answer="Remote work requires review.",
        status="partial",
        citations=[
            Citation(
                source_type="policy_evidence",
                source_id="HR-004:section-2",
                document_id="HR-004",
                title="Synthetic Remote Work Policy",
                section="2.2 Out-of-State Work",
                snippet="Written approval is required before out-of-state work.",
                claim="Prior approval is required.",
            )
        ],
        evidence_limitations="Eligibility has not been determined.",
        tool_calls=[
            ToolInvocationRecord(
                tool_name="search_policy_documents",
                status="success",
                arguments_summary={
                    "argument_names": ["question"],
                    "question": "PRIVATE-RAW-ARGUMENT",
                },
                result_summary={
                    "outcome": "found",
                    "evidence_count": 1,
                    "private_record": "PRIVATE-RAW-RESULT",
                },
                duration_ms=12.5,
            ),
            ToolInvocationRecord(
                tool_name="lookup_employee_profile",
                status="success",
                arguments_summary={"argument_names": ["employee_id"]},
                result_summary={"outcome": "found", "evidence_count": 1},
                duration_ms=8.0,
            ),
        ],
        operational_trace=OperationalTrace(
            events=[
                {"event": "intent_analysis", "category": "policy_question"},
                {
                    "event": "tool_call",
                    "tool": "search_policy_documents",
                    "outcome": "found",
                    "duration_ms": 12.5,
                    "arguments_summary": {
                        "argument_names": ["question"],
                        "question": "PRIVATE-RAW-ARGUMENT",
                    },
                    "result_summary": {
                        "outcome": "found",
                        "evidence_count": 1,
                        "private_record": "PRIVATE-RAW-RESULT",
                    },
                    "source_refs": [{"document_id": "HR-004", "employee": "PRIVATE-EMPLOYEE"}],
                    "provider_diagnostic": {"api_key": "PRIVATE-KEY"},
                    "internal_prompt": "PRIVATE-PROMPT",
                }
            ]
        ),
    )
    sessions = []

    def create_session():
        session = RecordingAgentSession(response=response)
        sessions.append(session)
        return session

    monkeypatch.setattr(runtime, "AgentSession", create_session)
    app = AppTest.from_file(str(APP_PATH)).run()
    app.chat_input[0].set_value("Can I work remotely from another state?").run()

    history = app.session_state["chat_history"]
    displayed = history[-1]
    assert displayed["status"] == "partial"
    assert displayed["citations"][0]["snippet"] == (
        "Written approval is required before out-of-state work."
    )
    assert displayed["tool_calls"][0]["arguments_summary"] == {
        "argument_names": ["question"]
    }
    assert [call["tool_name"] for call in displayed["tool_calls"]] == [
        "search_policy_documents",
        "lookup_employee_profile",
    ]
    assert [event["event"] for event in displayed["trace_events"]] == [
        "intent_analysis",
        "tool_call",
    ]
    assert displayed["trace_events"][1]["source_refs"] == [
        {"document_id": "HR-004"}
    ]
    assert "PRIVATE" not in json.dumps(displayed)
    assert any("Synthetic Remote Work Policy" in item.value for item in app.caption)
    assert any("HR-004:section-2" in item.value for item in app.caption)
    assert any(
        item.value == "Written approval is required before out-of-state work."
        for item in app.text
    )
    assert len(app.json) == 4
    rendered_json = json.dumps(
        [json.loads(item.value) for item in app.json],
        separators=(",", ":"),
    )
    assert rendered_json.index("search_policy_documents") < rendered_json.index(
        "lookup_employee_profile"
    )
    assert '"event":"tool_call"' in rendered_json
    assert "PRIVATE" not in rendered_json


def test_sample_prompts_use_the_agent_request_path_and_explicit_context(monkeypatch):
    sessions = []

    def create_session():
        session = RecordingAgentSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(runtime, "AgentSession", create_session)
    app = AppTest.from_file(str(APP_PATH)).run()
    app.text_input[0].set_value("SYN-001").run()

    _click_button(app, "PTO request guidance")
    _click_button(app, "Remote-work guidance")

    assert [request for request, _ in sessions[0].requests] == [
        PTO_PROMPT,
        REMOTE_WORK_PROMPT,
    ]
    assert [context for _, context in sessions[0].requests] == [
        {"employee_id": "SYN-001"},
        {"employee_id": "SYN-001"},
    ]
    assert len(app.session_state["chat_history"]) == 4


def test_display_history_is_not_sent_as_agent_context_and_absent_evidence_stays_absent(
    monkeypatch,
):
    sessions = []

    def create_session():
        session = RecordingAgentSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(runtime, "AgentSession", create_session)
    app = AppTest.from_file(str(APP_PATH)).run()
    app.chat_input[0].set_value("First question").run()
    app.chat_input[0].set_value("Second question").run()

    assert sessions[0].requests == [("First question", None), ("Second question", None)]
    assert [message["role"] for message in app.session_state["chat_history"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert [message["content"] for message in app.session_state["chat_history"]][::2] == [
        "First question",
        "Second question",
    ]
    assert app.session_state["chat_history"][-1]["citations"] == []
    assert app.session_state["chat_history"][-1]["tool_calls"] == []
    assert app.session_state["chat_history"][-1]["trace_events"] == []
    assert len(app.json) == 1


def test_blank_input_does_not_create_or_call_agent(monkeypatch):
    sessions = []

    def create_session():
        session = RecordingAgentSession()
        sessions.append(session)
        return session

    monkeypatch.setattr(runtime, "AgentSession", create_session)
    app = AppTest.from_file(str(APP_PATH)).run()
    app.chat_input[0].set_value("   ").run()

    assert not sessions
    assert not app.session_state["chat_history"]
    assert any("Enter a question before submitting." in item.value for item in app.warning)


@pytest.mark.parametrize(
    ("failure", "message", "code"),
    [
        (AgentError("llm_request_failed"), "The request could not be completed", "llm_request_failed"),
        (ClientError("transport_failure"), "The HR tools could not be reached", "transport_failure"),
        (TimeoutError(), "The request timed out", "timeout"),
        (ValueError("do not display this detail"), "inputs are invalid", "invalid_request"),
    ],
)
def test_agent_and_dependency_failures_are_explicit(monkeypatch, failure, message, code):
    sessions = []

    def create_session():
        session = RecordingAgentSession(error=failure)
        sessions.append(session)
        return session

    monkeypatch.setattr(runtime, "AgentSession", create_session)
    app = AppTest.from_file(str(APP_PATH)).run()
    app.chat_input[0].set_value("A deterministic test question").run()

    assert app.session_state["chat_history"][-1]["status"] == "error"
    assert app.session_state["chat_history"][-1]["error_code"] == code
    assert any(message in item.value for item in app.error)
    assert not any("do not display this detail" in item.value for item in app.error)


def test_health_view_renders_json_and_uses_discovery_only(monkeypatch):
    mcp_client = ContextMCPClient()
    monkeypatch.setattr(runtime, "MCPClient", lambda **kwargs: mcp_client)
    monkeypatch.setattr(
        AgentConfig,
        "from_environment",
        classmethod(lambda cls: AgentConfig()),
    )
    app = AppTest.from_file(str(APP_PATH)).run()

    assert json.loads(app.json[0].value) == {
        "app": {"status": "healthy"},
        "mcp": {"status": "unchecked", "tool_count": None, "error_code": None},
    }
    _click_button(app, "Check MCP health")
    assert json.loads(app.json[0].value) == {
        "app": {"status": "healthy"},
        "mcp": {"status": "healthy", "tool_count": 6, "error_code": None},
    }
    assert mcp_client.discover_calls == 1
    assert mcp_client.calls == []
    assert "agent_session" not in app.session_state

    class FailedDiscoveryClient(ContextMCPClient):
        async def discover(self):
            raise ClientError("discovery_failure")

    failed_client = FailedDiscoveryClient()
    monkeypatch.setattr(runtime, "MCPClient", lambda **kwargs: failed_client)
    _click_button(app, "Check MCP health")
    assert json.loads(app.json[0].value) == {
        "app": {"status": "healthy"},
        "mcp": {
            "status": "failed",
            "tool_count": None,
            "error_code": "discovery_failure",
        },
    }


@pytest.mark.parametrize(
    ("button_label", "confirmation", "expected_answer"),
    [
        ("Confirm draft", True, "The draft was confirmed"),
        ("Cancel draft", False, "confirmation was cancelled"),
    ],
)
def test_draft_confirmation_uses_the_same_agent_session(
    monkeypatch,
    button_label,
    confirmation,
    expected_answer,
):
    mcp_client = ContextMCPClient(
        results={
            "draft_hr_email": {
                "status": "found",
                "draft": {
                    "subject": "Synthetic PTO request",
                    "body": "Please review this synthetic PTO request.",
                },
            }
        }
    )
    llm_client = ScriptedLLM(
        [
            tool_completion(
                "draft_hr_email",
                {"recipient_name": "Synthetic Manager", "purpose": "PTO request"},
                "draft",
            )
        ]
    )
    monkeypatch.setattr(runtime, "MCPClient", lambda **kwargs: mcp_client)
    monkeypatch.setattr(runtime, "GroqLLMClient", lambda: llm_client)

    app = AppTest.from_file(str(APP_PATH)).run()
    try:
        app.chat_input[0].set_value("Please draft an email to my manager about PTO.").run()
        session = app.session_state["agent_session"]
        agent = session._agent

        assert app.session_state["pending_confirmation"]["action_id"]
        assert app.session_state["chat_history"][-1]["status"] == "confirmation_required"
        _click_button(app, button_label)

        assert app.session_state["agent_session"] is session
        assert session._agent is agent
        assert app.session_state["pending_confirmation"] is None
        assert app.session_state["chat_history"][-1]["status"] == "answered"
        assert expected_answer in app.session_state["chat_history"][-1]["content"]
        assert "No email was sent" in app.session_state["chat_history"][-1]["content"]
        assert [name for name, _ in mcp_client.calls] == ["draft_hr_email"]
    finally:
        app.session_state["agent_session"].close()
