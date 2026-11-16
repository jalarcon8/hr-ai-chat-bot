# Implementation Plan: Chat Interface

**Branch**: `005-chat-interface` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-chat-interface/spec.md`

## Summary

Add a thin Streamlit browser interface that passes each submitted message and explicit
employee context to the existing asynchronous `HRAgent`, then presents its answer, status,
citations, snippets, and privacy-safe operational activity. Streamlit's chat interaction is
the QR-030 equivalent; do not add a separate REST API. Keep display history in the active
browser session, but send only the current request and context to F003 because that agent
does not provide conversational memory.

Use the existing response and trace contracts without changing agent orchestration. The
agent/MCP runtime is scoped to the browser session so that a draft confirmation can use the
same `HRAgent` instance required by F003. Provide sample prompts for both F004 workflows,
clear pending/error states, and a health view that renders a JSON-compatible app/MCP status.
Implement the browser-to-agent vertical slice first; add evidence/trace presentation,
workflow prompts, and health reporting afterward.

## Technical Context

**Language/Version**: Python 3.11.

**Primary Dependencies**: Add one pinned Streamlit runtime dependency. Reuse existing
`HRAgent`, `AgentConfig`, `GroqLLMClient`, and `MCPClient`; do not add a web API framework,
orchestration library, or browser automation dependency.

**Storage**: `st.session_state` for display-only conversation history and the current
synthetic employee ID. No database or cross-session persistence.

**Testing**: Existing pytest setup. Use controlled agent responses and the existing synthetic
F004/MCP fixture harness; use Streamlit's own app test support if it covers the required
browser interactions without extra dependencies.

**Target Platform**: Local Streamlit application within the existing single-service Python
project; deployment is owned by F006.

**Project Type**: Python browser application over the existing agent library.

**Performance Goals**: No new latency target. Preserve F003's bounded sequential tool-call
behavior and show request-in-progress feedback while it runs.

**Constraints**: Do not bypass MCP, add agent conversational memory, persist history across
sessions, introduce a REST API, expose hidden reasoning or raw records, use real employee
data, or add features assigned to F006.

**Scale/Scope**: One chat surface, the two documented F004 workflow prompts, one
machine-readable health equivalent, and a small set of deterministic UI/runtime tests.

## Constitution Check

### Pre-design gate

| Principle/constraint | Status | Plan application |
|---|---|---|
| I. Simplicity First | Pass | Use Streamlit as the single browser UI; no separate API, database, or front-end stack. |
| II. Python-First Implementation | Pass | UI, session adapter, and tests remain Python. |
| III. Modular Separation | Pass | Keep display code separate from a narrow adapter to F003; reuse F003/F002 interfaces. |
| IV. Grounded AI Responses | Pass | Render only returned answers, statuses, citations, snippets, and evidence limitations. |
| V. MCP-Compliant Tool Integration | Pass | Only F003 invokes discovered tools through the existing MCP client. |
| VI. Synthetic Data and Safe Operations | Pass | Use synthetic workflow examples and existing proposal-bound confirmation; send no email. |
| VII. Automated Testing and Reproducibility | Pass | Exercise app startup, the request path, response rendering, health states, and an MCP-backed scenario with deterministic fixtures. |
| Single-service/free-tier constraints | Pass | Streamlit and the stdio MCP server remain in the existing application service. |
| Feature ownership | Pass | F005 owns the browser experience; F006 retains deployment, CI/CD, evaluation, and final demo. |

### Post-design gate

The design adds only the Streamlit dependency required by the roadmap. It introduces no
separate listener, persistent store, new agent capability, or change to the F003 response
contract. One session-scoped runtime is required to preserve F003's same-agent confirmation
invariant; it carries no conversational history into agent requests. The in-app health view
uses the assignment's “or equivalent” allowance and does not claim to be a standalone HTTP
JSON endpoint.

## Design Decisions

1. **Chat equivalent for QR-030**: The Streamlit chat is the request/response equivalent.
   Submitting a message calls `HRAgent.process_request`; the resulting answer, response
   status, citations/snippets, and sanitized tool activity are available in the same browser
   interaction. No `/chat` REST route is added.
2. **Display history, not agent memory**: Keep prior messages and rendered responses only in
   `st.session_state`. Each agent call receives the current user message and the current
   optional `context.employee_id`, not the visible conversation transcript. IDs in free text
   are not promoted to authoritative context. Provide a clearly labeled synthetic employee
   ID input for employee-specific workflows.
3. **Runtime lifetime**: Keep a per-browser-session `HRAgent` and its MCP session on one
   serialized asynchronous runtime. This is needed because F003 requires the same agent
   instance to validate a caller-carried draft proposal during confirmation. It does not
   turn F003 into a memory-bearing agent. Do not share an agent instance across browser
   sessions.
4. **Health equivalent for QR-031**: Provide a Streamlit health view whose JSON-compatible
   result has `app.status` and `mcp.status`. The view probes MCP by opening the existing
   `MCPClient` and running `discover()` only; it makes no LLM or HR tool call. Use `healthy`,
   `failed`, or `unchecked` for MCP, with a safe error code on failure and no raw exception
   content. The health function also supports an unchecked result when no probe is requested.
5. **Response presentation**: Reuse `AgentResponse.answer`, `status`, `citations`,
   `evidence_limitations`, `tool_calls`, `operational_trace`, and confirmation fields.
   Render citations and tool records from their typed fields. Project trace events through an
   explicit allowlist of observable event/outcome/tool/evidence/answer-basis fields rather
   than dumping arbitrary event dictionaries.
6. **Errors and safety**: Handle known agent initialization/runtime and MCP client failures
   explicitly. Preserve non-success statuses, show safe actionable messages, and never
   fabricate a response or report a failed dependency as healthy.

## Implementation Sequence

These are plan milestones, not implementation tasks:

1. **Browser-to-agent vertical slice**: Add the minimal Streamlit entry point and pinned
   dependency; accept nonblank input, pass explicit context through the existing agent
   interface, and display the returned answer/status. Establish a deterministic smoke test.
2. **Session and action continuity**: Add display-only session history and the session-scoped
   async runtime; preserve the same agent for the existing email-draft proposal confirmation
   flow. Do not pass prior chat turns into F003.
3. **Evidence and trace presentation**: Render returned citations/snippets, evidence
   limitations, and ordered allowlisted tool/trace summaries. Cover every response status and
   missing optional fields.
4. **Workflow reproduction**: Add sample prompts for PTO and remote-work scenarios, with
   explicit synthetic employee context where needed. Verify both use the same request path as
   typed questions.
5. **Health and failure checks**: Add the JSON-compatible health view with healthy, failed,
   and unchecked MCP states, plus explicit initialization, request, timeout, and dependency
   failure handling.
6. **Documentation and final focused verification**: Document local startup and the health
   view in the F005 quickstart and the relevant README section; run the targeted UI/runtime
   tests and the F004 MCP-backed acceptance path.

## Requirements-to-Design Traceability

| Requirement | Design decision | Planned verification |
|---|---|---|
| QR-028 / FR-001 | Add the roadmap's Streamlit browser app and one pinned runtime dependency. | Start the app using the documented command and verify the chat surface loads. |
| QR-029 / FR-001-FR-003 | Submit user text to the existing agent and display its returned answer and status. | Deterministic UI test for a policy request and a workflow response. |
| QR-030 / FR-002-FR-005 | Use the Streamlit interaction as the chat equivalent; present returned answer, citations, snippets, and sanitized tool activity without a REST API. | Test the UI-to-agent call and rendered response fields; verify no alternate orchestration path is used. |
| QR-031 / FR-007, FR-009 | Provide a health view returning a JSON-compatible app/MCP object; probe with `MCPClient.discover()` and distinguish healthy, failed, and unchecked. | Test the JSON shape and each MCP status with a controlled client; verify no LLM/tool call occurs. |
| QR-032 / FR-006 | Supply F004 PTO and remote-work sample prompts and explicit synthetic employee context. | Submit both samples through the same UI request handler and verify agent context. |
| QR-020 / FR-005, FR-011 | Present typed tool summaries and explicitly allowlisted sanitized trace fields only. | Assert displayed traces preserve order/outcomes/evidence while excluding reasoning, prompts, credentials, full records, and unrestricted input. |
| QR-049 / FR-006 | Make both F004 scenarios reproducible for F006's later demo. | Verify each prompt completes or reports its actual clarification/escalation outcome without claiming unsupported actions. |

QR-033-QR-060 remain F006-owned. No F005 design decision claims deployment, CI/CD,
project-wide evaluation, a recorded presentation, or final submission completion.

## Testing Strategy

- **Unit/runtime**: Verify blank input does not invoke the agent; current user text and
  employee context are passed correctly; previous display history is not included in the
  request; and expected F003 errors become explicit UI-safe states.
- **Streamlit interaction**: Use deterministic responses to cover answer/status rendering,
  citations/snippets, ordered tool activity, absent optional fields, workflow prompts,
  clarification/confirmation/partial/error outcomes, and display-only session history.
- **Health**: Verify JSON serialization and `healthy`, `failed`, and `unchecked` MCP states.
  The probe uses MCP discovery only and never invokes the LLM or an HR operation.
- **MCP-backed integration**: Exercise one browser-to-agent workflow using the existing
  stdio MCP fixture harness and a controlled LLM; reuse F004's actual protocol integration
  coverage rather than duplicating its workflow suite.
- **Startup**: Run a Streamlit app smoke test with stubbed dependencies and no provider
  credentials or network calls.
- **Regression**: Run relevant F003/F004 acceptance and MCP tests after implementation; do
  not run the full project suite unless targeted tests indicate a regression.

## Project Structure

```text
src/hr_app/
├── __init__.py
├── app.py          # Streamlit chat, session display state, prompts, and rendering
└── runtime.py      # Narrow session-scoped async adapter to HRAgent/MCPClient and health probe

tests/
├── test_chat_interface.py           # Deterministic Streamlit/UI acceptance
├── unit/test_chat_runtime.py         # Request/context and health contract
└── integration/test_chat_mcp.py      # One controlled browser-to-agent stdio scenario

specs/005-chat-interface/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
└── quickstart.md
```

**Structure Decision**: Add one small `hr_app` package to the existing `src/` layout. Keep
presentation in `app.py` and agent lifecycle/health adaptation in `runtime.py`; do not add a
generic API layer, service, workflow engine, or persistence module.

## Complexity Tracking

No constitution exception is proposed. The session-scoped async runtime is retained only to
respect the existing async MCP lifecycle and same-agent confirmation contract; it does not
add agent memory or cross-session state.
