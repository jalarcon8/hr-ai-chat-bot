# Feature Specification: Agent Orchestration

**Feature ID**: F003

**Feature Branch**: `003-agent-orchestration`

**Created**: 2026-11-15

**Status**: Draft - ready for implementation

**Input**: Provide an LLM-based agent that interprets HR requests, decides when to use RAG 
retrieval alone versus MCP tool calls, dynamically discovers and invokes tools, handles 
multi-step operations, and synthesizes grounded responses. Reuse Feature 001 (RAG retrieval) 
and Feature 002 (MCP tools) capabilities without reimplementing them.

## Clarifications

### Session 2026-11-15

- Q: Is Feature 001 policy retrieval accessed directly by the agent, or only through Feature 002's MCP tools? → A: The agent accesses policy evidence exclusively through Feature 002's `search_policy_documents` MCP tool; it does not invoke Feature 001 retrieval directly.
- Q: What mock state-changing operations are supported, and what must be refused? → A: Only the existing Feature 002 email-drafting tool is used for confirmable actions; new mock approval, record-update, or persistent state-management capabilities are not introduced. The agent drafts emails, requests confirmation, and clearly indicates no email was sent. All other state-changing operations (sending, approvals, record updates) are refused.
- Q: What is the confirmation requirement when state-changing operations are proposed? → A: Confirmation is specific to the proposed action. A new or materially changed action requires new confirmation, not cached confirmation from prior requests.
- Q: Should operational traces include chain-of-thought reasoning or only observable decisions? → A: Traces include observable intent categories, selected tools, outcome categories, and evidence references. Hidden chain-of-thought, internal prompts, and sensitive raw data must be excluded.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interpret intent and route to appropriate tools (Priority: P1)

As a developer, I want the agent to understand what the user is asking for and autonomously 
decide whether to use policy retrieval alone, MCP tools alone, or a combination so that the 
correct evidence and data are gathered to answer the question.

**Why this priority**: Intent interpretation and correct tool selection are the foundation 
of agent autonomy.

**Independent Test**: Submit representative requests (policy question, employee lookup, 
multi-step workflow) to the agent and verify that it selects and invokes the appropriate 
tools without user intervention.

**Acceptance Scenarios**:

1. **Given** a straightforward policy question that does not require structured employee data,
   **When** the request is submitted to the agent, **Then** the agent uses policy retrieval 
   and does not make unnecessary MCP tool calls.
2. **Given** a request for employee information or PTO balance, **When** the request is 
   submitted, **Then** the agent invokes the relevant MCP tool(s) and does not rely solely 
   on policy retrieval.
3. **Given** a multi-step request combining policy evidence with structured data (e.g., 
   "Can this employee take PTO?" requiring both PTO balance and policy checks), **When** the 
   request is submitted, **Then** the agent makes both types of calls and integrates the 
   results in the answer.

---

### User Story 2 - Discover and invoke MCP tools dynamically (Priority: P1)

As an agent, I want to discover available MCP tools at runtime and invoke them according to 
the request so that the agent adapts to available capabilities without hardcoding tool 
definitions.

**Why this priority**: Dynamic discovery ensures the agent can work with evolving tool sets 
and reduces coupling between the agent and MCP server.

**Independent Test**: Start the agent with the Feature 002 MCP server, verify that it 
discovers all available tools, and successfully invoke a representative set in a single 
conversation.

**Acceptance Scenarios**:

1. **Given** the agent is initialized and the MCP server is running, **When** the agent 
   starts, **Then** it discovers all six MCP tools and their schemas.
2. **Given** an available tool and a valid request requiring it, **When** the agent processes 
   the request, **Then** it invokes the tool through MCP with appropriate arguments derived 
   from the request context.
3. **Given** multiple tools are available and a request could use more than one, **When** the 
   agent processes the request, **Then** it selects and invokes all necessary tools to 
   satisfy the request.

---

### User Story 3 - Handle tool failures and missing information gracefully (Priority: P1)

As a user, I want the agent to clearly communicate when tools fail, information is missing, 
or the request is ambiguous so that I understand why the agent cannot provide a complete 
answer.

**Why this priority**: Transparent failure handling and clarification requests maintain user 
trust and prevent silent errors.

**Independent Test**: Simulate tool failures (unavailable MCP server, missing employee, no 
policy evidence) and ambiguous requests (missing required context); verify that the agent 
returns clear, actionable error messages or clarification requests without hallucinating 
data.

**Acceptance Scenarios**:

1. **Given** an MCP tool is unavailable or returns an error, **When** the agent attempts to 
   invoke it, **Then** the agent communicates the failure clearly and either provides 
   alternative information or escalates gracefully.
2. **Given** a request refers to a missing employee ID or an employee without a PTO record, 
   **When** the agent retrieves structured data, **Then** it reports the missing information 
   explicitly and does not invent employee data or assume default values.
3. **Given** a request is ambiguous or missing required context (e.g., "I need time off" 
   without specifying the dates or employee), **When** the agent processes the request, 
   **Then** it requests the necessary clarification from the user.
4. **Given** policy evidence does not support a claim or conflicts, **When** the agent 
   synthesizes the answer, **Then** it identifies the limitation and does not present 
   unsupported claims as fact.

---

### User Story 4 - Generate grounded, cited responses with operational traces (Priority: P2)

As a developer or auditor, I want to inspect the agent's decision-making, tool invocations, 
and evidence so that I can verify correctness and diagnose problems without exposing hidden 
reasoning or sensitive data.

**Why this priority**: Transparency and traceability are essential for trust, debugging, and 
compliance.

**Independent Test**: Execute representative workflows and inspect the returned operational 
traces; verify that they show tool names, arguments (allowlisted summaries), results, 
retrieved citations, and the basis for the final response, without exposing chain-of-thought, 
credentials, or unnecessary user input.

**Acceptance Scenarios**:

1. **Given** a completed agent request, **When** the result is inspected, **Then** the 
   operational trace includes: tool names selected, allowlisted argument summaries, tool 
   outcomes, retrieved evidence (citations), and the explicit basis for the final answer.
2. **Given** sensitive data (credentials, full employee records, raw question text), **When** 
   the trace is persisted, **Then** the trace excludes or redacts them, capturing only 
   allowlisted summaries.
3. **Given** a multi-step workflow with several tool calls, **When** the trace is inspected, 
   **Then** it shows the sequence, results of each call, and how they contributed to the 
   final answer.
4. **Given** the agent encounters an escalation, ambiguity, or failure, **When** the trace 
   is inspected, **Then** it clearly indicates the decision and the reason.

---

### User Story 5 - Prevent unauthorized or irreversible actions (Priority: P1)

As an HR manager or employee, I want assurance that the agent cannot perform irreversible 
operations (send emails, approve requests, update records) without explicit user confirmation 
so that I retain control over sensitive actions.

**Why this priority**: Safety is non-negotiable; synthetic data and mock operations reduce 
risk, but confirmations provide an additional safeguard.

**Independent Test**: Attempt to execute a state-changing operation (e.g., draft and confirm 
an email, simulate an approval request) and verify that it requires explicit user 
confirmation before proceeding and that the operation affects only synthetic data.

**Acceptance Scenarios**:

1. **Given** an action that would change state (draft and send an HR email), **When** the 
   agent identifies the action as needed, **Then** it requests explicit user confirmation 
   before executing the mock operation.
2. **Given** a confirmed state-changing operation on synthetic data, **When** it completes, 
   **Then** the change affects only fictional employee records or drafts and is reversible 
   or resettable.
3. **Given** a request to perform an operation not yet supported or outside scope, **When** 
   the agent processes it, **Then** it clearly identifies the limitation and does not 
   silently mock the action or invent a result.

### Edge Cases

- A request lacks sufficient context (e.g., no employee ID when one is required): the agent 
  requests clarification rather than making assumptions.
- An MCP tool is temporarily unavailable (network failure, server restart): the agent 
  communicates the temporary failure and suggests a retry or alternative.
- Policy evidence is retrieved but does not directly answer the question: the agent provides 
  the most relevant evidence available and identifies what remains unknown.
- Tool input schemas change (between agent startup and tool invocation): the agent detects 
  schema mismatch and reports the incompatibility rather than failing silently.
- A request triggers multiple tools that have conflicting or redundant results: the agent 
  synthesizes them transparently, citing all relevant evidence.
- The agent's internal reasoning (chain-of-thought, prompt instructions) appears in the 
  trace or output: this is an operational error to be surfaced, not silently filtered.
- A tool call fails after partial execution (e.g., record lookup starts but times out): the 
  agent reports the partial failure and does not invent the missing data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST interpret natural-language user requests and decide whether to 
  use Feature 002's MCP policy search tool alone, other Feature 002 MCP tools alone, or a 
  combination based on the request content and the agent's understanding of tool capabilities. 
  The agent MUST NOT invoke Feature 001 retrieval directly; policy evidence MUST be accessed 
  exclusively through Feature 002's `search_policy_documents` MCP tool.
- **FR-002**: The agent MUST dynamically discover available MCP tools via the Feature 002 
  MCP server's discovery mechanism at initialization or on-demand, without hardcoding tool 
  names or schemas. It MUST validate that the declared schemas and available tools match 
  before invocation.
- **FR-003**: When a user request requires multiple tools or a sequence of operations (e.g., 
  lookup employee, check balance, retrieve policy), the agent MUST autonomously determine 
  the call sequence and execute all necessary calls. It MUST preserve results and pass them 
  to subsequent calls as context when needed.
- **FR-004**: The agent MUST validate tool input arguments against declared schemas and 
  reject invalid arguments with a clear error. If a required argument cannot be derived from 
  the request or prior results, the agent MUST request the missing information from the user 
  rather than inventing or guessing values.
- **FR-005**: When a tool call fails, times out, or returns an error, the agent MUST surface 
  the failure explicitly to the user, identify what information is unavailable, and either 
  provide a partial answer with clear limitations or request user confirmation to proceed 
  with alternative approaches.
- **FR-006**: The agent MUST use retrieved policy evidence (from Feature 001) and tool 
  results (from Feature 002) as the exclusive source of factual claims in the response. It 
  MUST ground all policy claims in policy evidence with citations (document ID, title, 
  optional section, and exact snippet). It MUST ground all employee or operational claims in 
  tool results.
- **FR-007**: When policy evidence does not support a claim, conflicts with other evidence, 
  or is absent, the agent MUST identify the limitation and MUST NOT fabricate evidence or 
  claims. It MUST distinguish supported facts from recommendations.
- **FR-008**: The agent MUST support at least two representative multi-step workflows 
  combining policy retrieval and MCP tool calls. These workflows need not be hardcoded; the 
  agent MUST be capable of planning and executing similar workflows autonomously.
- **FR-009**: The agent MUST generate a concise operational trace for each request showing: 
  (a) the identified intent, (b) tools selected and why, (c) tool invocation details 
  (allowlisted argument summaries, not raw values), (d) tool results, (e) retrieved evidence 
  and citations, (f) reasoning for the final response, and (g) any escalation, clarification, 
  or failure decision.
- **FR-010**: Operational traces MUST exclude or redact: credentials, API keys, full employee 
  records, complete raw user questions, email drafts (beyond subject/recipient summary), 
  chain-of-thought reasoning, and internal prompts. Traces MUST capture allowlisted metadata 
  such as tool names, argument names (not values), source document IDs, sections, and outcome 
  categories.
- **FR-011**: The agent MUST support user confirmation workflows using the existing Feature 002 
  email-drafting tool only. The agent MUST request explicit user confirmation before 
  finalizing any draft email, MUST clearly indicate that no email was sent, and MUST NOT 
  introduce new mock approval, record-update, or persistent state-management capabilities. 
  Confirmation requirements are specific to each proposed action; a new or materially changed 
  action requires new confirmation. All unsupported state-changing operations (actual email 
  sending, approvals, persistent record updates) MUST be refused.
- **FR-012**: The agent MUST refuse or redirect requests outside its scope (e.g., "Delete 
  all employee records", "Override the PTO policy") and MUST NOT silently invent capabilities 
  or bypass safety constraints.
- **FR-013**: The agent's question interface MUST be a Python function or class accepting a 
  user request string and optional context, and returning a structured result containing the 
  answer, citations, evidence limitations, operational trace, and any required user 
  confirmation for state-changing actions.
- **FR-014**: The agent initialization MUST establish a connection to the Feature 002 MCP 
  server, discover available tools, and validate readiness before accepting user requests. If 
  the MCP server is unavailable, the agent MUST report this explicitly rather than falling 
  back silently to retrieval-only mode.
- **FR-015**: Tool invocation and response handling MUST use the MCP protocol exclusively; 
  direct in-memory calls to MCP server functions bypass the protocol and are not acceptable.
- **FR-016**: The agent MUST support configuration of the LLM model, temperature, token 
  limits, and top-k retrieval parameters. These MUST be environment-configurable and 
  documented. Credentials (API keys) MUST be read from environment variables and MUST NOT be 
  committed.
- **FR-017**: The agent MUST have separable responsibilities from retrieval, MCP integration, 
  response synthesis, and trace generation, enabling independent testing and debugging without 
  requiring end-to-end execution.

### Quantic Requirement Traceability

| Requirement | F003 specification coverage |
|---|---|
| QR-018 | FR-001, FR-003, FR-008; agent interprets intent, decides orchestration, selects and calls tools, synthesizes responses. |
| QR-019 | Deferred to F004; F003 provides the orchestration foundation. |
| QR-020 | FR-009, FR-010; concise operational traces without hidden reasoning. |
| QR-021 | FR-005, FR-004; graceful handling of missing tools, employee IDs, incomplete evidence, and ambiguity. |
| QR-022 | FR-011, FR-012; mock state-changing operations with confirmation; scope enforcement. |
| QR-026 | FR-015; actual MCP protocol invocation, not direct calls. |

### Key Entities

- **User Request**: A natural-language question or instruction submitted by a user or 
  application to the agent.
- **Intent**: The agent's interpretation of what the user is trying to accomplish (e.g., 
  "lookup employee", "request PTO approval", "check policy compliance").
- **Tool Selection Decision**: The agent's determination of which tools (retrieval, MCP tools, 
  or both) are needed to satisfy the request.
- **Tool Call**: An MCP-protocol invocation of a specific tool with validated arguments, 
  executed by the agent.
- **Operational Trace**: A structured log of the agent's decisions, tool calls, results, and 
  reasoning, suitable for auditing and debugging.
- **Grounded Response**: An answer supported by retrieved evidence (with citations) and tool 
  results, with identified limitations and clear handling of missing or conflicting evidence.
- **State-Changing Operation**: A user-confirmation workflow using the Feature 002 email-drafting 
  tool. The agent drafts an email, requests explicit confirmation, and clearly indicates no 
  email was sent. Unsupported operations (actual sending, approvals, record updates) are 
  refused.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer following setup and quickstart instructions can initialize the agent 
  with Feature 002 (which wraps Feature 001's retrieval), discover at least four MCP tools 
  (Feature 002 provides six), and submit a straightforward request (e.g., "What is the remote 
  work policy?").
- **SC-002**: In an acceptance set of at least three policy-only requests, the agent uses the MCP 
  policy search tool exclusively and does not make unnecessary calls to other MCP tools.
- **SC-003**: In an acceptance set of at least three data-lookup requests (employee, PTO 
  balance), the agent invokes the correct MCP tools and returns the retrieved data without 
  relying solely on retrieval.
- **SC-004**: In an acceptance set of at least three multi-step workflow requests combining 
  policy search and structured data operations, the agent invokes both the policy search MCP 
  tool and other data-lookup MCP tools in the correct sequence and synthesizes a complete 
  answer with citations for policy claims and structured results for data claims.
- **SC-005**: In an acceptance set of at least two requests with missing information or 
  ambiguity, the agent requests user clarification and does not invent missing details.
- **SC-006**: In an acceptance set of at least two requests where policy evidence is absent, 
  incomplete, or conflicting, the agent identifies the limitation and does not fabricate 
  evidence or unsupported claims.
- **SC-007**: In an acceptance set of at least two tool-failure scenarios (unavailable tool, 
  invalid employee ID, network error), the agent surfaces the failure clearly and provides an 
  alternative or partial response without hallucinating data.
- **SC-008**: An operational trace for each completed request includes tool names, outcome 
  categories, allowlisted argument summaries, source document IDs, and the basis for the 
  final answer; it excludes credentials, full records, chain-of-thought, and raw user 
  questions.
- **SC-009**: A representative email-drafting workflow shows explicit user confirmation 
  requirement before finalizing the draft and clearly indicates that no email was sent; 
  unsupported operations (approvals, record updates, actual sending) are refused with a clear 
  explanation.
- **SC-010**: Automated tests cover intent interpretation, single-tool and multi-tool 
  invocation, tool failure and retry handling, citation grounding, clarification requests, 
  operational tracing, and safety constraints without requiring real MCP servers or LLM 
  calls; external calls are replaced with deterministic test doubles.

## Assumptions

- F003 depends on F002 (MCP tools), which wraps F001 (policy retrieval). F002 must be complete 
  and stable before F003 is tested end-to-end. The agent does not integrate F001 directly; 
  policy evidence is accessed only through F002's `search_policy_documents` MCP tool.
- The agent is a Python application; it uses LLM tool calling (via Groq or OpenRouter) to 
  orchestrate and reason about tool selection. The specific LLM model is configurable and 
  must be documented; a free or free-tier model is required.
- The Feature 002 MCP server uses FastMCP and stdio transport. The agent is the MCP client; 
  it connects to the server at initialization.
- Tool discovery uses the MCP protocol's tools/list_tools operation. Tool invocation uses 
  tools/call_tool. Both must be performed through the protocol; direct in-memory calls are 
  not acceptable.
- The agent does not reimplement Feature 001 retrieval; it accesses policy evidence 
  exclusively through Feature 002's MCP interface. Feature 002's `search_policy_documents` 
  tool wraps Feature 001's retrieval capabilities.
- State-changing operations are not introduced beyond the existing Feature 002 email-drafting 
  tool. Email drafting is a mock operation; it does not send emails, create approvals, or 
  update databases. Confirmation is a user-facing check; once confirmed, the agent indicates 
  the draft was prepared but no email was sent.
- Operational traces are persisted to a configured sink (file, database, or log) for auditing 
  and debugging. Trace-sink failures are surfaced as explicit operational errors.
- The agent supports natural-language requests without requiring formal query languages or 
  structured APIs. The primary interface is a Python function accepting a user request string 
  and returning a structured result.
- Configuration (LLM model, API keys, retrieval k, trace sink, MCP server endpoint) is 
  environment-based and documented. No configuration is hardcoded or committed.
- Tool input schemas may evolve between agent runs (e.g., a tool is added or a schema 
  changes). The agent must validate schemas at use time and report schema mismatches rather 
  than crashing or falling back silently.
- The assignment PDF and project roadmap remain the authoritative source for scope. If 
  ambiguity arises, clarification is sought rather than assumed.
