# Tasks: Chat Interface

**Input**: Design documents in `specs/005-chat-interface/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, and `quickstart.md`

**Organization**: Tasks follow the four requested MVP milestones. User-story labels link
implementation and verification to the F005 scenarios; milestone order is intentional.

**Scope**: F005 browser chat and local verification only. No REST API, agent memory,
deployment, CI/CD implementation, or project-wide evaluation.

## Milestone 1: Foundation

**Purpose**: Add the minimal Streamlit application structure, reuse the existing F003/F004
contracts, and establish isolated session state.

- [x] T001 [US1] Add a pinned Streamlit runtime dependency to `pyproject.toml` and
  `requirements.txt`, and create the minimal `src/hr_app/` package with `app.py` and
  `runtime.py`; do not add another web framework or API service (FR-001; QR-028).
- [x] T002 [US1] Implement the narrow session runtime in `src/hr_app/runtime.py` using
  `AgentConfig`, `GroqLLMClient`, `MCPClient`, and `HRAgent`; keep its asynchronous MCP
  lifecycle valid across Streamlit reruns and preserve the same `HRAgent` instance for
  proposal confirmation (FR-002, FR-011).
- [x] T003 [US1] Initialize per-browser-session display history and optional synthetic
  employee ID state in `src/hr_app/app.py`; keep prior turns display-only and pass an
  explicit ID only as `context.employee_id` (FR-002, FR-010, FR-013).

**Checkpoint**: The app shell can initialize the existing agent runtime without adding
conversational memory or sharing agent state across browser sessions.

## Milestone 2: Core vertical slice

**Purpose**: Get one request from the browser through the existing agent and show its actual
answer and status before adding the remaining interface features.

- [x] T004 [US1] Implement the minimal chat submission in `src/hr_app/app.py`: reject blank
  input, show request-in-progress feedback, call the existing runtime with only the current
  message and explicit context, and display the returned answer and status (FR-002, FR-003,
  FR-007, FR-008; QR-028-QR-030).
- [x] T005 [US1] Run the vertical slice locally with a deterministic agent response and verify
  a submitted browser message reaches `HRAgent.process_request` and renders its returned
  answer/status without provider credentials; record the command and outcome in
  `specs/005-chat-interface/quickstart.md` (FR-001-FR-003, FR-012; QR-028-QR-030).

**Checkpoint**: One browser request completes through the F003 interface and displays the
agent's real response status; no answer or success state is fabricated by the UI.

## Milestone 3: Remaining MVP functionality

**Purpose**: Complete evidence and trace inspection, both workflow entry points, safe input
and failure states, and JSON-compatible health reporting.

- [x] T006 [US2] Extend response rendering in `src/hr_app/app.py` to show returned citations,
  source/title/section when available, supporting snippets, and evidence limitations; render
  ordered typed tool-call summaries and only the allowlisted observable fields from
  `AgentResponse.operational_trace` (FR-004, FR-005, FR-011; QR-030 and supporting QR-020).
- [x] T007 [US3] Add sample prompts for the documented PTO and remote-work scenarios in
  `src/hr_app/app.py`; connect each prompt to the same submission path as typed input and
  supply employee-specific context only through the explicit synthetic employee ID field
  (FR-002, FR-006; QR-029, QR-032).
- [x] T008 [US1] Complete user-facing validation and failure states in `src/hr_app/app.py`:
  preserve clarification, confirmation-required, partial, out-of-scope, and error outcomes;
  present explicit safe messages for known agent/MCP failures; and use the same session
  runtime for explicit draft confirmation/cancellation (FR-003, FR-007, FR-008, FR-011).
- [x] T009 [US3] Add a JSON-serializable health check in `src/hr_app/runtime.py` and render it
  in the Streamlit health view in `src/hr_app/app.py`; report app status and MCP
  `healthy`/`failed`/`unchecked` status, using `MCPClient.discover()` only for a probe and
  returning safe error codes rather than raw exception details (FR-009; QR-031).

**Checkpoint**: The UI exposes both F004 scenarios, returned evidence and safe traces, all
agent outcome classes, and a health result without a separate REST endpoint or MCP tool call.

## Milestone 4: Verification and closure

**Purpose**: Add focused deterministic coverage, verify the local checks, record requirement
evidence, and check CI availability without absorbing F006 ownership.

- [x] T010 [US2] Add focused Streamlit interaction tests in
  `tests/test_chat_interface.py` for answer/status rendering, citations/snippets, ordered
  allowlisted traces, absent optional fields, display-only history, current-message/context
  forwarding, blank-input rejection, and explicit error/confirmation states (FR-002-FR-005,
  FR-007-FR-008, FR-010-FR-013; QR-028-QR-030).
- [x] T011 [US3] Extend the existing deterministic Streamlit tests to verify both sample
  prompts reach `AgentSession.process_request`, explicit employee context is preserved, draft
  confirmation/cancellation uses the same runtime, and health distinguishes healthy, failed,
  and unchecked MCP results through discovery only. Reuse F004's existing scripted and
  stdio workflow tests for backend regression coverage; do not add a separate test harness
  (FR-006, FR-009, FR-012; QR-031-QR-032).
- [x] T012 [US3] Run the focused F005 tests, the related F003/F004 agent and MCP
  regressions, and repository-wide Ruff; record exact commands and results in
  `specs/005-chat-interface/quickstart.md` (FR-001-FR-013; QR-028-QR-032).
- [x] T013 [US1] Update the local-run instructions in `README.md` and verify
  `specs/005-chat-interface/quickstart.md` matches the implemented app command, synthetic
  context input, and health view (FR-001, FR-006, FR-009, FR-012; QR-028-QR-032).
- [x] T014 [US3] Update the F005 QR-028-QR-032 rows in
  `docs/requirements/traceability.md` with verified outcomes and any remaining limitations;
  do not mark a requirement Verified without supporting evidence (QR-028-QR-032).
- [x] T015 [US3] Check for a CI run covering the F005 branch and record its result. The
  active workflow exists, but no hosted run is available for this branch; record CI as
  unverified and hand it off to F006 without creating CI/deployment work (QR-028-QR-032;
  F006 ownership).

**Closure criteria**: F005 implementation and local verification evidence are recorded; each
QR row distinguishes verified outcomes from remaining limitations; hosted CI is explicitly
reported as unverified and remains with F006.

## Requirement Coverage

| Requirement | Implementation tasks | Verification tasks |
|---|---|---|
| QR-028 | T001, T004 | T005, T010, T012 |
| QR-029 | T004, T007 | T010, T011 |
| QR-030 | T004, T006 | T005, T010, T011 |
| QR-031 | T009 | T011, T012 |
| QR-032 | T007 | T011, T012 |

## Noncritical limitations

- An active `.github/workflows/ci.yml` workflow exists, but no hosted run was found for branch
  `005-chat-interface`; hosted CI is unverified and remains with F006.
- QR-031 is implemented as a Streamlit health-view equivalent rendering a JSON-serializable
  status object, not a raw HTTP `/health` endpoint.
- F005 does not establish a deployed URL, deployment readiness, project-wide metrics, or
  completion of the final demo; these remain with F006.
