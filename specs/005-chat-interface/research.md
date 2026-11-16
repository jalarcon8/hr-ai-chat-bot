# Research: Chat Interface

## Decisions

### Decision 1: Use Streamlit chat as the QR-030 equivalent

**Decision**: The browser chat submits the current user message to
`HRAgent.process_request` and presents the returned answer, status, citations, snippets, and
sanitized operational activity in the same interaction. Do not add a separate REST API.

**Rationale**: QR-030 explicitly permits an endpoint “or equivalent”; the F005 roadmap names a
Streamlit chat and calls for request-handling equivalents. This gives a grader a direct
browser request path without another framework or listener.

**Alternative considered**: Add a FastAPI/Flask `/chat` service alongside Streamlit. Rejected
because it adds a second interface/framework without being required by the assignment.

### Decision 2: Keep visible conversation history separate from agent input

**Decision**: Store user messages and rendered response data in Streamlit session state for
display during the active browser session. Submit only the current message and its explicit
context to F003; do not send prior turns or create conversation memory.

**Rationale**: F003's `process_request` creates a request from its current input/context and
does not persist or replay prior turns. Sending displayed history would create a new agent
behavior not requested by F005.

**Integration constraint**: F004 requires a nonblank caller-provided `context.employee_id`
for employee-specific profile/PTO calls. The UI provides a clearly labeled synthetic employee
ID field and passes that value as context. It never treats a free-text ID as authoritative.

### Decision 3: Preserve F003 runtime and confirmation contracts

**Decision**: Keep one `HRAgent` per active Streamlit browser session, accessed through a
serialized asynchronous runtime that owns the existing `MCPClient` context. Use the same
agent instance when a user confirms or cancels an F003 draft proposal.

**Rationale**: F003's MCP client and agent methods are asynchronous. More importantly,
`confirm_action` verifies a proposal against a key held by the same `HRAgent` instance;
recreating the agent on each Streamlit rerun would reject a legitimate confirmation.
Session scoping avoids sharing proposal state between browser sessions.

**Alternatives considered**:

- Create and close an agent for every message: rejected because the same-instance
  confirmation invariant cannot be preserved.
- Share one process-global agent: rejected because pending proposal context and session
  lifetimes would not be isolated.
- Add persistent storage or agent memory: rejected because F003 carries proposals through
  the caller and F005 explicitly does not add memory.

### Decision 4: Use an in-app JSON-compatible health view

**Decision**: Provide a Streamlit health view backed by a function that returns a
JSON-serializable object with app status and MCP status. When probed, open an existing
`MCPClient`, run `discover()`, and close it. Do not invoke the model or any HR tool.

The JSON-compatible shape is:

```json
{
  "app": {"status": "healthy"},
  "mcp": {"status": "healthy", "tool_count": 6, "error_code": null}
}
```

MCP status is one of `healthy`, `failed`, or `unchecked`. A discovery failure returns
`failed` and a safe machine-readable error code; an unrequested probe returns `unchecked`.
The Streamlit view renders this object as JSON. This is the QR-031 equivalent, not a raw
HTTP `/health` endpoint.

**Rationale**: Streamlit is the selected framework and the requirement allows an equivalent.
The in-app view gives the grader machine-readable health fields without a second HTTP
framework or server. `discover()` tests the actual configured MCP transport and tool
catalog; it is more meaningful than merely reporting that the app page rendered.

**Alternative considered**: Add a standalone HTTP health listener or mount a REST framework.
Rejected because that would add infrastructure solely to work around Streamlit's built-in
server. If the assignment reviewer later requires a raw HTTP JSON response, that is a scope
change to revisit with F006 rather than something to silently add here.

### Decision 5: Render existing typed response data and allowlisted traces

**Decision**: Display `AgentResponse.answer`, `status`, `citations`, `evidence_limitations`,
`tool_calls`, and confirmation/clarification fields. Display trace events through a fixed
projection of observable event type, outcome, tool, category/decision, evidence references,
answer-basis, and approved disposition fields. Do not dump arbitrary event dictionaries.

**Rationale**: F003 already supplies typed citations and tool records, with allowlisted trace
summaries. Reuse avoids redesigning orchestration or exposing raw MCP/model messages.

## Technical Context Findings

- The project supports Python 3.11 and has pinned dependencies in `pyproject.toml` and
  `requirements.txt`; Streamlit is not yet a runtime dependency.
- `HRAgent.process_request` and `confirm_action` are asynchronous and return the existing
  `AgentResponse` structure.
- Employee-specific F004 requests require `context.employee_id`; an ID present only in
  natural-language text is not authoritative.
- F003's `AgentResponse` already contains answer, status, citations, evidence limitations,
  tool-call summaries, operational trace, clarification and confirmation state, and
  optional proposal context.
- F003 trace events are dictionaries but are constructed from observable, privacy-safe
  fields. The UI should still project an allowlisted subset rather than rendering arbitrary
  dictionary contents.
- `MCPClient` provides an async context manager and `discover()`; an MCP health probe can
  therefore use the existing protocol without a model call or tool operation.
- F004 already has deterministic agent tests and a real stdio MCP fixture harness. F005 can
  reuse those fixtures and add only one representative UI-to-agent integration scenario.
- No Streamlit app or Streamlit-specific tests currently exist.

## Risks and Mitigations

1. **Async runtime across Streamlit reruns**: Bind one `HRAgent`/`MCPClient` session to a
   serialized, session-scoped event loop. Test repeated requests and confirmation on the same
   instance; do not block the UI with concurrent calls on that session.
2. **Health-equivalent interpretation**: The selected health view returns a JSON-compatible
   object in the browser, not a raw HTTP JSON endpoint. This is within the assignment's
   “or equivalent” language; verify the reviewer accepts the browser health view before
   claiming an external health URL in F006 deployment documentation.
3. **Session data isolation**: Keep history and pending action state in Streamlit's
   per-browser-session state. Do not share an agent instance between sessions or persist
   employee context beyond the active session.
4. **Display privacy**: Use typed citation/tool fields and a fixed trace projection. Add tests
   with unexpected trace keys to ensure arbitrary event data is not rendered.
5. **Local policy index readiness**: Streamlit startup and health must not eagerly build or
   download the F001 index. If a policy request cannot access the index, surface the F003/F002
   failure rather than presenting an empty or successful answer.
