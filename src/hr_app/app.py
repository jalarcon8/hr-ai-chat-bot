"""Minimal Streamlit chat over the existing HR agent."""

from __future__ import annotations

import re
from typing import Any, TypedDict

import streamlit as st

from hr_agent.errors import AgentError
from hr_agent.types import AgentResponse, Citation, ToolInvocationRecord
from hr_app.runtime import AgentSession, health_status
from hr_mcp.client import ClientError

PTO_PROMPT = (
    "Can I request 8 hours of PTO on 2026-02-01? "
    "Check my available balance and explain the policy steps."
)
REMOTE_WORK_PROMPT = (
    "Can I work remotely from another state for six weeks? "
    "Check my location, security, and approval requirements."
)


class DisplayMessage(TypedDict, total=False):
    role: str
    content: str
    status: str
    error_code: str
    citations: list[dict[str, object]]
    evidence_limitations: str
    tool_calls: list[dict[str, object]]
    trace_events: list[dict[str, object]]
    clarification_prompt: str


class PendingConfirmation(TypedDict):
    action_id: str
    pending_action: dict[str, Any]


_SUMMARY_KEYS = {"argument_names", "outcome", "evidence_count", "evidence_kind"}
_TRACE_SCALAR_KEYS = {
    "event",
    "outcome",
    "tool",
    "category",
    "disposition",
    "answer_basis",
    "error_code",
    "timestamp",
}


def _safe_text(value: object, *, limit: int = 120) -> str | None:
    if isinstance(value, str) and value and len(value) <= limit:
        return value
    return None


def _safe_summary(value: dict[str, Any]) -> dict[str, object]:
    summary: dict[str, object] = {}
    names = value.get("argument_names")
    safe_names = (
        [
            name[:64]
            for name in names[:12]
            if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]{1,64}", name)
        ]
        if isinstance(names, list)
        else []
    )
    if safe_names:
        summary["argument_names"] = safe_names

    outcome = _safe_text(value.get("outcome"), limit=40)
    if outcome is not None:
        summary["outcome"] = outcome
    evidence_count = value.get("evidence_count")
    if (
        isinstance(evidence_count, int)
        and not isinstance(evidence_count, bool)
        and evidence_count >= 0
    ):
        summary["evidence_count"] = evidence_count
    evidence_kind = value.get("evidence_kind")
    if evidence_kind == "candidate":
        summary["evidence_kind"] = evidence_kind
    return {key: item for key, item in summary.items() if key in _SUMMARY_KEYS}


def _display_citation(citation: Citation) -> dict[str, object]:
    fields = ("source_type", "source_id", "document_id", "title", "section", "snippet")
    return {
        field: value
        for field in fields
        if isinstance((value := getattr(citation, field)), str) and value
    }


def _display_tool_call(tool_call: ToolInvocationRecord) -> dict[str, object]:
    result: dict[str, object] = {
        "tool_name": _safe_text(tool_call.tool_name, limit=80) or "unknown_tool",
        "status": tool_call.status,
        "arguments_summary": _safe_summary(tool_call.arguments_summary),
        "result_summary": _safe_summary(tool_call.result_summary),
    }
    if isinstance(tool_call.duration_ms, (int, float)) and tool_call.duration_ms >= 0:
        result["duration_ms"] = tool_call.duration_ms
    error_code = _safe_text(tool_call.error_code, limit=80)
    if error_code is not None:
        result["error_code"] = error_code
    return result


def _display_trace_event(event: dict[str, Any]) -> dict[str, object]:
    safe_event: dict[str, object] = {}
    for key in _TRACE_SCALAR_KEYS:
        value = _safe_text(event.get(key), limit=120)
        if value is not None:
            safe_event[key] = value

    for key in ("citation_count", "tool_count"):
        value = event.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            safe_event[key] = value

    duration = event.get("duration_ms")
    if (
        isinstance(duration, (int, float))
        and not isinstance(duration, bool)
        and duration >= 0
    ):
        safe_event["duration_ms"] = duration

    for key in ("arguments_summary", "result_summary"):
        value = event.get(key)
        if isinstance(value, dict):
            summary = _safe_summary(value)
            if summary:
                safe_event[key] = summary

    source_refs = event.get("source_refs")
    safe_refs = (
        [
            {"document_id": reference["document_id"]}
            for reference in source_refs[:12]
            if isinstance(reference, dict)
            and isinstance(reference.get("document_id"), str)
            and re.fullmatch(r"[A-Z]{2,8}-[0-9]{3}", reference["document_id"])
        ]
        if isinstance(source_refs, list)
        else []
    )
    if safe_refs:
        safe_event["source_refs"] = safe_refs
    return safe_event


def _response_message(response: AgentResponse) -> DisplayMessage:
    message: DisplayMessage = {
        "role": "assistant",
        "content": response.answer,
        "status": response.status,
        "citations": [_display_citation(citation) for citation in response.citations],
        "tool_calls": [_display_tool_call(call) for call in response.tool_calls],
        "trace_events": [
            safe_event
            for event in response.operational_trace.events
            if (safe_event := _display_trace_event(event))
        ],
    }
    if response.evidence_limitations:
        message["evidence_limitations"] = response.evidence_limitations
    if response.clarification_prompt:
        message["clarification_prompt"] = response.clarification_prompt
    if response.error_code:
        message["error_code"] = response.error_code
    return message


def _error_message(content: str, error_code: str) -> DisplayMessage:
    return {
        "role": "assistant",
        "content": content,
        "status": "error",
        "error_code": error_code,
    }


def _show_message(message: DisplayMessage) -> None:
    with st.chat_message(message["role"]):
        status = message.get("status")
        if status == "error":
            st.error(message["content"])
        elif status in {"partial", "clarification_needed", "confirmation_required"}:
            st.warning(message["content"])
        elif status == "out_of_scope":
            st.info(message["content"])
        else:
            st.markdown(message["content"])

        status = message.get("status")
        if status:
            st.caption(f"Status: {status}")
        error_code = message.get("error_code")
        if error_code:
            st.caption(f"Error code: {error_code}")

        clarification = message.get("clarification_prompt")
        if clarification and clarification != message.get("content"):
            st.info(clarification)

        limitations = message.get("evidence_limitations")
        if limitations:
            st.warning(f"Evidence limitation: {limitations}")

        citations = message.get("citations", [])
        if citations:
            with st.expander("Sources and supporting snippets"):
                for citation in citations:
                    document_id = citation.get("document_id")
                    title = citation.get("title")
                    identity = " — ".join(
                        value for value in (document_id, title) if isinstance(value, str)
                    )
                    source = citation.get("source_type")
                    if isinstance(source, str):
                        source_id = citation.get("source_id")
                        source_reference = (
                            f"{source} ({source_id})"
                            if isinstance(source_id, str)
                            else source
                        )
                        st.caption(f"{source_reference}: {identity or 'source'}")
                    elif identity:
                        st.markdown(f"**{identity}**")
                    section = citation.get("section")
                    if isinstance(section, str):
                        st.caption(f"Section: {section}")
                    snippet = citation.get("snippet")
                    if isinstance(snippet, str):
                        st.text(snippet)

        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            with st.expander("Tool activity"):
                for index, tool_call in enumerate(tool_calls, start=1):
                    name = tool_call.get("tool_name", "unknown_tool")
                    outcome = tool_call.get("status", "unknown")
                    st.caption(f"{index}. {name} — {outcome}")
                    st.json(tool_call)

        trace_events = message.get("trace_events", [])
        if trace_events:
            with st.expander("Operational trace"):
                st.json(trace_events)


def _agent_session() -> tuple[AgentSession | None, str | None]:
    session = st.session_state.get("agent_session")
    if session is not None:
        return session, None
    try:
        session = AgentSession()
    except ValueError:
        return None, "invalid_configuration"
    st.session_state.agent_session = session
    return session, None


def _run_request(user_input: str) -> None:
    if not user_input.strip():
        st.warning("Enter a question before submitting.")
        return

    user_message: DisplayMessage = {"role": "user", "content": user_input}
    st.session_state.chat_history.append(user_message)

    employee_id = st.session_state.employee_id.strip()
    context = {"employee_id": employee_id} if employee_id else None
    with st.spinner("Working on your request..."):
        session, configuration_error = _agent_session()
        if session is None:
            assistant_message = _error_message(
                "The HR assistant is not configured correctly.",
                configuration_error or "invalid_configuration",
            )
        else:
            try:
                response = session.process_request(user_input, context=context)
            except AgentError as exc:
                assistant_message = _error_message(
                    f"The request could not be completed ({exc.code}).",
                    exc.code,
                )
            except ClientError as exc:
                assistant_message = _error_message(
                    f"The HR tools could not be reached ({exc.code}).",
                    exc.code,
                )
            except TimeoutError:
                assistant_message = _error_message(
                    "The request timed out. Please try again.",
                    "timeout",
                )
            except ValueError:
                assistant_message = _error_message(
                    "The request could not be processed because its inputs are invalid.",
                    "invalid_request",
                )
            else:
                assistant_message = _response_message(response)
                if response.confirmation_required:
                    if response.action_id and response.pending_action:
                        st.session_state.pending_confirmation = {
                            "action_id": response.action_id,
                            "pending_action": response.pending_action,
                        }
                    else:
                        st.warning("The draft proposal is missing confirmation details.")

    st.session_state.chat_history.append(assistant_message)
    st.rerun()


def _run_confirmation(confirmation: bool) -> None:
    pending = st.session_state.get("pending_confirmation")
    if not isinstance(pending, dict):
        st.warning("There is no draft awaiting confirmation.")
        return
    action_id = pending.get("action_id")
    pending_action = pending.get("pending_action")
    if not isinstance(action_id, str) or not isinstance(pending_action, dict):
        st.error("The pending draft confirmation is invalid.")
        st.session_state.pending_confirmation = None
        return

    choice = "Confirmed" if confirmation else "Cancelled"
    st.session_state.chat_history.append(
        {"role": "user", "content": f"{choice} the simulated draft."}
    )

    with st.spinner("Recording your choice..."):
        session, configuration_error = _agent_session()
        if session is None:
            assistant_message = _error_message(
                "The HR assistant is not configured correctly.",
                configuration_error or "invalid_configuration",
            )
        else:
            try:
                response = session.confirm_action(
                    action_id,
                    confirmation,
                    {"pending_action": pending_action},
                )
            except AgentError as exc:
                assistant_message = _error_message(
                    f"The confirmation could not be completed ({exc.code}).",
                    exc.code,
                )
            except ClientError as exc:
                assistant_message = _error_message(
                    f"The HR tools could not be reached ({exc.code}).",
                    exc.code,
                )
            except TimeoutError:
                assistant_message = _error_message(
                    "The confirmation timed out. Please try again.",
                    "timeout",
                )
            except ValueError:
                assistant_message = _error_message(
                    "The pending draft is no longer valid. Request a new draft if needed.",
                    "invalid_confirmation",
                )
                st.session_state.pending_confirmation = None
            else:
                assistant_message = _response_message(response)
                st.session_state.pending_confirmation = None

    st.session_state.chat_history.append(assistant_message)
    st.rerun()


def main() -> None:
    st.set_page_config(page_title="HR Assistant")
    st.title("HR Assistant")
    st.caption("Ask a question about fictional HR policies or workflows.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "employee_id" not in st.session_state:
        st.session_state.employee_id = ""
    if "pending_confirmation" not in st.session_state:
        st.session_state.pending_confirmation = None
    if "health_result" not in st.session_state:
        st.session_state.health_result = health_status(probe=False)

    with st.sidebar:
        st.text_input(
            "Synthetic employee ID (optional)",
            key="employee_id",
            help="Used as explicit context for employee-specific requests.",
        )
        st.caption("Use a synthetic employee ID for profile or balance-specific answers.")
        st.divider()
        st.subheader("Application health")
        if st.button("Check MCP health", key="health_probe"):
            st.session_state.health_result = health_status()
        st.json(st.session_state.health_result)

    for message in st.session_state.chat_history:
        _show_message(message)

    pending = st.session_state.pending_confirmation
    if isinstance(pending, dict):
        st.info("A simulated email draft is awaiting your explicit choice.")
        confirm_column, cancel_column = st.columns(2)
        if confirm_column.button("Confirm draft", key="confirm_draft"):
            _run_confirmation(True)
        elif cancel_column.button("Cancel draft", key="cancel_draft"):
            _run_confirmation(False)

    st.caption("Sample prompts")
    prompt_column, remote_column = st.columns(2)
    pto_clicked = prompt_column.button("PTO request guidance", key="sample_pto")
    remote_clicked = remote_column.button(
        "Remote-work guidance",
        key="sample_remote_work",
    )

    user_input = st.chat_input("Ask an HR question")
    if pto_clicked:
        _run_request(PTO_PROMPT)
    elif remote_clicked:
        _run_request(REMOTE_WORK_PROMPT)
    elif user_input is not None:
        _run_request(user_input)


if __name__ == "__main__":
    main()
