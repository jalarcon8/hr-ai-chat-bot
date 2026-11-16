# Feature Specification: Chat Interface

**Feature Branch**: `005-chat-interface`

**Created**: 2026-11-15

**Status**: Draft - ready for user review

**Input**: Provide a simple browser interface to the HR agent so users can ask policy and
workflow questions and inspect grounded answers, evidence, and operational traces.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask HR questions in a browser (Priority: P1)

As an employee, I want to ask a natural-language HR policy or workflow question in a browser
so that I can receive guidance from the existing HR agent.

**Why this priority**: The browser chat is the primary user-facing capability of F005 and the
grader-facing entry point for the application.

**Independent Test**: Start the app with controlled agent responses, submit a policy question
and each F004 workflow scenario, and verify that each request reaches the existing agent and
its result is displayed.

**Acceptance Scenarios**:

1. **Given** the application is ready, **When** a user submits a non-empty policy question,
   **Then** the app submits it to the existing agent and displays its returned answer and
   status.
2. **Given** a user submits either documented F004 workflow scenario, **When** the agent
   completes or needs clarification, **Then** the app displays the returned guidance or
   clarification without claiming an unsupported action occurred.
3. **Given** the agent is processing a request, **When** the response is pending, **Then** the
   interface indicates that processing is underway and prevents the user from mistaking the
   pending request for a completed answer.
4. **Given** a workflow requires employee-specific information, **When** the user provides a
   synthetic employee ID in the dedicated context field, **Then** the app passes that value
   as `context.employee_id` and does not infer authoritative identity from message text.
5. **Given** the submitted message is blank or whitespace, **When** the user submits it,
   **Then** the app does not invoke the agent and provides clear input guidance.

### User Story 2 - Inspect evidence and tool activity (Priority: P1)

As an employee or reviewer, I want to inspect citations, supporting snippets, and concise tool
activity alongside an answer so that I can understand what evidence and operations support it.

**Why this priority**: Traceable, grounded responses are core project requirements; merely
showing generated answer text would hide whether a workflow used the required evidence.

**Independent Test**: Supply a deterministic agent response containing citations, snippets,
tool-call summaries, and an error or partial status; verify the corresponding information is
available in the browser without exposing hidden reasoning or raw records.

**Acceptance Scenarios**:

1. **Given** an answer includes policy citations, **When** it is displayed, **Then** each
   citation includes the returned document identity/title, section when available, and
   supporting snippet.
2. **Given** an answer includes tool activity, **When** a user inspects the response, **Then**
   the interface shows the ordered tool names, concise allowlisted summaries, and outcomes
   available in the agent response.
3. **Given** an answer is partial, needs clarification or confirmation, is out of scope, or
   reports an error, **When** it is displayed, **Then** its status and next step or limitation
   are clear and are not presented as a successful completed workflow.
4. **Given** tool activity or evidence is absent, **When** the response is displayed, **Then**
   the interface does not fabricate citations, snippets, tool calls, or outcomes.
5. **Given** operational details are shown, **When** the user inspects them, **Then** hidden
   chain-of-thought, internal prompts, credentials, full employee records, and unnecessary
   raw user data are not displayed.

### User Story 3 - Reproduce workflows and check service health (Priority: P2)

As a grader or developer, I want sample prompts for the two required workflows and a
machine-readable health check so that I can reproduce the core tasks and determine whether
the app and its MCP dependency are available.

**Why this priority**: Graders need a predictable way to exercise the two agentic tasks, while
developers need a simple way to distinguish app availability from dependency availability.

**Independent Test**: Run each supplied workflow prompt through the browser and request the
health response; verify both workflows can be exercised and that health is returned as JSON
with app status and MCP status when that check is feasible.

**Acceptance Scenarios**:

1. **Given** a user opens the application, **When** sample prompts are presented, **Then**
   they provide clear starting points for both the PTO and remote-work workflows without
   promising a particular eligibility or approval result.
2. **Given** a grader selects either sample prompt, **When** it is submitted, **Then** the
   request follows the same chat and agent path as a user-entered question.
3. **Given** a health check is requested, **When** the application returns its health result,
   **Then** the result is machine-readable JSON identifying application status and MCP
   connectivity where feasible; an unchecked or indeterminate dependency is not reported as
   healthy.
4. **Given** the agent or MCP dependency is unavailable, **When** a chat request or health
   check encounters that condition, **Then** the app reports a clear failure or dependency
   status rather than returning a success-shaped response.

### Edge Cases

- An empty or whitespace-only request is rejected before agent invocation.
- A request is slow, times out, or the agent raises an error; the user sees an explicit
  pending, timeout, or error state rather than a fabricated answer.
- MCP is unavailable while the web app is running; app availability and MCP availability
  remain distinguishable.
- A response has no citations or tool calls, or has only some optional evidence fields; the
  interface displays only returned data and handles absent fields clearly.
- A citation has no section; the citation remains usable with its available source identity,
  title, and snippet.
- The agent returns `clarification_needed`, `confirmation_required`, `partial`,
  `out_of_scope`, or `error`; the UI preserves the distinction and does not imply completion.
- A rerun, reload, or new browser session occurs; F005 does not claim that cross-session
  conversation history was saved.
- Trace details include values that are not suitable for display; only the agent's
  privacy-safe, allowlisted summaries are eligible for presentation.

## Scope Boundaries

**In scope**: A simple Streamlit browser chat; natural-language input; display of agent
answers, statuses, citations, snippets, and concise tool-call traces; sample prompts for both
F004 workflows; request-in-progress feedback; user-friendly input and dependency errors; and
a JSON health endpoint or equivalent.

**Out of scope**: Authentication, administrative dashboards, persistent cross-session chat
history, complex front-end frameworks, new HR workflows, new agent or retrieval logic,
real HR integrations, deployment and CI/CD, project-wide evaluation, and the final recorded
demonstration. F006 owns deployment, CI/CD, evaluation, and final delivery.

## Dependencies

- **F001 - HR Policy RAG**: supplies policy evidence, citations, and snippets through the
  existing agent workflow.
- **F002 - MCP Tool Integration**: supplies the existing MCP client and tools used by the
  agent; F005 does not call tools directly or bypass MCP.
- **F003 - Agent Orchestration**: supplies the request-processing interface, response status,
  citations, tool-call summaries, and sanitized operational trace. The UI presents these
  results and does not implement a second orchestrator.
- **F004 - HR Agentic Workflows**: supplies the PTO and remote-work user scenarios that F005
  makes reproducible through the browser.
- **F006 - Deployment, CI/CD, and Evaluation**: consumes the interface for integrated
  deployment and verification; it is not a prerequisite for implementing F005.

## MVP Classification

**Required for F005**

- Provide a browser chat for natural-language HR policy and workflow questions.
- Pass requests through the existing agent interface and render its answer and outcome
  without bypassing the agent or MCP.
- Make returned citations, supporting snippets, and concise privacy-safe tool-call traces
  inspectable.
- Provide example prompts for both documented F004 workflows.
- Show request-in-progress feedback and clear validation, agent, and dependency errors.
- Provide a machine-readable health endpoint or equivalent reporting application status and
  MCP connectivity where feasible.
- Keep chat history within the active session only; do not promise cross-session persistence.

**Supporting**

- Reuse existing F001-F004 contracts and deterministic scenarios. Keep the interface
  independently testable with controlled agent responses and without live provider calls.

**Deferred from F005, not dropped from the project**

- Single-service hosting, shareable deployment URL, cold-start documentation, CI/CD,
  project-wide evaluation, metrics, design/submission materials, and recorded demo are owned
  by F006.
- Authentication, admin functions, persistent history, and unrelated workflows remain
  outside the project scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST provide a browser-based chat interface for natural-language
  HR policy and workflow questions, using the project-approved lightweight web framework.
- **FR-002**: The application MUST submit valid user requests to the existing agent processing
  interface and pass an explicitly supplied synthetic employee ID as `context.employee_id`
  when needed. It MUST NOT infer authoritative employee context from free text, duplicate
  agent orchestration, invoke MCP tools directly, or provide a separate answer-generation
  path.
- **FR-003**: The application MUST display the agent's answer and response status, preserving
  distinctions among answered, partial, clarification-needed, confirmation-required,
  out-of-scope, and error outcomes.
- **FR-004**: The application MUST make returned citations and their supporting snippets
  inspectable, including source identity and title and section when available. It MUST display
  only citations and snippets returned by the agent.
- **FR-005**: The application MUST make returned tool-call activity inspectable in order, using
  tool names, concise allowlisted argument/output summaries, outcomes, and evidence references
  available in the sanitized agent response or trace. It MUST NOT expose hidden
  chain-of-thought, internal prompts, credentials, full employee records, or unnecessary raw
  user data.
- **FR-006**: The application MUST provide sample prompts that enable a grader to reproduce
  the F004 PTO and remote-work workflows through the same request path as ordinary chat.
- **FR-007**: The interface MUST provide clear processing feedback while an agent request is
  pending and MUST communicate request validation, timeout, agent, and dependency failures
  without returning a success-shaped fallback.
- **FR-008**: The application MUST reject an empty or whitespace-only message without calling
  the agent and MUST give the user actionable input guidance.
- **FR-009**: The application MUST provide a health endpoint or equivalent that returns a
  JSON-serializable status object identifying application status and MCP connectivity where
  feasible. The health view MUST render that result as JSON and distinguish a confirmed
  healthy dependency from an unavailable, failed, or unchecked dependency.
- **FR-010**: The application MUST NOT add authentication, administrative dashboards,
  persistent cross-session conversation storage, real employee data, or real HR integrations.
- **FR-011**: The interface MUST preserve the agent's safety and evidence limitations; it MUST
  NOT imply that an email was sent, a request submitted or approved, a record changed, or an
  eligibility decision made when the agent did not return that outcome.
- **FR-012**: Routine interface tests MUST use controlled responses or fixtures and MUST NOT
  require live model-provider credentials or calls.
- **FR-013**: The application MUST maintain the visible chat history only for the active
  browser session. It MUST NOT send prior displayed turns as agent context or persist them
  across sessions.

### Key Entities

- **Chat request**: A user's submitted natural-language message, carried through the existing
  agent request boundary.
- **Agent response**: The answer, status, citations, evidence limitations, tool-call records,
  and operational trace returned by the existing agent.
- **Citation**: A returned policy or tool-result reference with source identity, title, optional
  section, and supporting snippet.
- **Tool activity**: An ordered, sanitized record of a tool name, allowlisted summaries,
  outcome, and available evidence references.
- **Health result**: A machine-readable status of the web application and, where checked, its
  MCP dependency; unchecked dependency status is distinct from healthy.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A browser user can submit a valid policy question and view the agent's answer
  and status without a live HR integration.
- **SC-002**: Each F004 demo scenario can be started from a supplied sample prompt and produces
  the corresponding agent response through the same path as typed input.
- **SC-003**: For responses containing citations, snippets, or tool calls, all returned
  inspectable items are available in the UI with their source/ordering and outcome metadata;
  no unreturned item is fabricated.
- **SC-004**: Agent responses in every supported status are visibly distinguishable, and
  errors or pending requests are never presented as successful completed answers.
- **SC-005**: Empty and whitespace-only input results in zero agent invocations and clear
  validation feedback.
- **SC-006**: The health check produces a JSON-serializable result identifying app status and
  MCP connectivity when checked, and the health view renders it as JSON without labeling an
  unchecked or failed MCP dependency as healthy.
- **SC-007**: Routine interface tests cover request submission, evidence/trace rendering,
  both sample workflows, input validation, health results, and dependency or agent failures
  without live provider credentials.
- **SC-008**: User-visible operational details exclude hidden reasoning, internal prompts,
  credentials, full employee records, and unnecessary raw user data.
- **SC-009**: Within one browser session, previous messages remain available for display; a
  request made after earlier messages contains only the current message and its explicit
  context, and a new session does not restore prior history.

## Assumptions

- The roadmap's Streamlit interface is the project-approved lightweight browser framework;
  any change of framework requires a planning justification and must not introduce a complex
  front-end stack.
- The chat interaction itself may satisfy the assignment's `/chat` endpoint-or-equivalent
  requirement when it exposes the same request, answer, citation, snippet, and trace
  information. F005 does not require a separate REST API unless planning finds the browser
  interaction insufficient for grading.
- The health result is independently testable as a JSON-serializable object and is rendered
  as JSON in the browser. MCP status is reported when it can be checked safely without
  causing a user chat request or presenting an unchecked dependency as healthy; a raw HTTP
  health route is not required by the “or equivalent” allowance.
- F003's existing response and privacy-safe trace are the data source for UI display; missing
  optional values are represented as absent or unavailable, not inferred.
- Conversation state may be maintained during the active browser session, but F005 does not
  persist it across sessions.
- All policy documents, employees, and workflow examples are synthetic.

## Assignment Requirements Traceability

| Assignment requirement | Functional requirements | Success criteria | Acceptance scenarios |
|---|---|---|---|
| QR-028 - Provide a web application using an appropriate framework. | FR-001 | SC-001 | US1-AS1 |
| QR-029 - Provide a chat interface for HR policy and workflow questions. | FR-001, FR-002 | SC-001, SC-002 | US1-AS1-AS2 |
| QR-030 - Provide a chat endpoint or equivalent returning answer, citations, snippets, and concise tool-call trace. | FR-002-FR-005 | SC-001, SC-003 | US1-AS1-AS2, US2-AS1-AS2 |
| QR-031 - Provide a health endpoint or equivalent with JSON app status and MCP connectivity where feasible. | FR-007, FR-009 | SC-006 | US3-AS3-AS4 |
| QR-032 - Enable a grader to reproduce at least two agentic tasks through UI or API client. | FR-002, FR-006 | SC-002 | US1-AS4, US3-AS1-AS2 |
| QR-020 - Provide concise privacy-safe operational traces. (F003 owns; F005 presents them.) | FR-005, FR-011 | SC-003, SC-008 | US2-AS2-AS5 |
| QR-049 - Demonstrate both workflows in the final deployed recording. (F006 owns; F005 supplies the browser interface.) | FR-006 | SC-002 | US3-AS1-AS2 |

QR-033-QR-039 (deployment and CI/CD), QR-040-QR-044 (evaluation), QR-045-QR-048 and
QR-050-QR-060 (design and submission) remain F006-owned. F005 provides a browser experience
and health response that F006 can integrate and verify; this specification does not claim
that a deployed URL, final evaluation, or recorded presentation already exists.
