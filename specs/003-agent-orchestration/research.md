# Research: Agent Orchestration Design Decisions

## Scope and Inputs

This design research reconciles the approved Feature 003 specification, the Feature 003
decisions, the project constitution, the requirements-integration rules, the roadmap, the
requirements traceability matrix, and the existing Feature 002 MCP client/tool contract.
Research is limited to the Feature 003 planning stage; it does not create implementation tasks.

## Decisions

### 1. LLM-driven orchestration and tool calling

**Decision:** Use an LLM with native tool calling to interpret each request, select from
discovered MCP tools, decide when additional calls are needed, and synthesize the response.
The model is called again after each tool result, allowing each next decision to use the
preceding result. Do not use heuristic intent routing, a dependency graph, or an orchestration
framework.

**Rationale:** This is the explicitly approved Feature 003 architecture and directly satisfies
FR-001, FR-003, FR-008, and QR-018. A small provider adapter over the existing Groq dependency
keeps the implementation within the current Python project.

**Alternatives rejected:** Keyword/regex routing was rejected by the user. LangChain, LangGraph,
topological sorting, and a separate workflow engine add abstractions not required by the
bounded tool-use problem.

### 2. Bounded sequential loop

**Decision:** Use one model-selected MCP tool call per LLM turn. Validate and execute that call,
append its structured result to the conversation, and request the next model turn. Stop when
the model returns a final answer or the configured `max_tool_calls` limit is reached.

**Rationale:** Sequential execution is approved, permits later calls to depend on earlier tool
results, and avoids concurrent side effects and dependency planning. The call bound prevents
runaway loops. Groq SDK 0.18.0 supports `n=1` and `parallel_tool_calls=False`; request both
for the Groq adapter and still reject any provider response containing multiple calls.

**Alternatives rejected:** Parallel tool execution and a static/topological workflow plan are
not needed for the MVP.

**Source validation:** Groq's official tool-use guide and API reference document native tool
calls and `parallel_tool_calls`; the pinned SDK source exposes the parameter:
[tool use](https://console.groq.com/docs/tool-use/overview),
[API reference](https://console.groq.com/docs/api-reference), and
[Groq Python 0.18.0 completion parameters](https://github.com/groq/groq-python/blob/v0.18.0/src/groq/types/chat/completion_create_params.py).
These sources do not guarantee that the model will always return a single call, so the
single-call check remains required.

### 3. MCP integration and policy retrieval

**Decision:** Reuse `src/hr_mcp/client.py` and the installed MCP SDK. The existing asynchronous
client establishes the stdio session, discovers tools through MCP `tools/list`, and invokes
them through `tools/call`. The agent uses `MCPClient.discover()` and `MCPClient.call()` rather
than importing server functions or calling Feature 001.

Feature 002 defines six tools: `search_policy_documents`, `get_policy_section`,
`lookup_employee_profile`, `check_pto_balance`, `check_policy_compliance`, and `draft_hr_email`.
Discover the live catalog and schemas rather than assuming a static catalog. Pass only
Feature-003-supported tools to the model; policy evidence is accessed solely through
`search_policy_documents`, as required by the approved clarification. Do not use
`get_policy_section` as an alternate policy-evidence path. Integration validation checks the
complete six-tool discovery baseline; SC-001's four-tool minimum remains a lower acceptance
threshold.

**Rationale:** This preserves dynamic discovery and actual protocol use while respecting the
approved exclusive policy-search path. F002 remains the owner of server and tool behavior.

### 4. Tool schema and safety boundary

**Decision:** Translate the schemas returned by the current MCP discovery result to the
provider's tool-call format. Validate the selected name and JSON arguments against the same
discovered catalog before invoking MCP. Enforce the approved Feature 003 action boundary:
the existing email-drafting tool may prepare an unsent mock draft; sending, approvals,
employee-record updates, and other unsupported mutations are refused.

**Rationale:** Provider schema conversion is required to let the model select tools without
hardcoded argument schemas. Runtime validation prevents malformed or invented calls. A
Feature-003 safety check remains necessary even though selection is LLM-driven.

**Alternatives rejected:** Duplicating F002 schemas in Feature 003 would become stale and would
undermine dynamic discovery. Trusting model output without schema validation would conflict with
FR-004 and the constitution.

### 5. Confirmation across requests without persistence

**Decision:** Call the existing `draft_hr_email` tool to prepare an unpersisted draft proposal,
then return that proposal and a confirmation request. Bind confirmation to that exact proposal.
The caller carries the pending proposal/action identifier in the next request context. A
materially changed proposal gets a new identifier and requires new confirmation. On confirmation
the agent reports only the simulated draft outcome and states that no email was sent. The agent
does not store drafts or confirmations in a database or session service.

**Rationale:** This implements the approved confirmation intent with the existing F002 tool and
the optional `context` already present in the interface. It introduces no persistent state or
unsupported operation.

### 6. Grounded synthesis and conflicts

**Decision:** Synthesize factual claims only from the user's in-scope request/context and
returned MCP evidence. Policy claims cite evidence returned by `search_policy_documents`;
employee/operational claims cite the relevant tool result. If evidence conflicts, report the
conflict and sources without inventing a resolution. Refuse or redirect unsupported and
out-of-scope requests.

**Rationale:** This satisfies FR-006/FR-007, QR-015/QR-016 support, and Constitution Principle
IV. Feature 001 retrieval remains behind F002.

### 7. Trace content

**Decision:** Trace concise, observable summaries: intent category, selected tool names,
selection category, allowlisted argument summaries, outcome category, duration, source IDs and
sections, answer-basis category, and clarification/escalation/failure outcome. Exclude
chain-of-thought, internal prompts, full user requests, credentials, full records, and draft
bodies.

**Rationale:** This meets QR-020 and FR-009/FR-010 without recording hidden reasoning or
sensitive data. The trace describes observable actions and evidence, not the model's private
reasoning.

### 8. Async interface and test strategy

**Decision:** Make the public agent calls asynchronous to compose directly with F002's
asynchronous `MCPClient` and its stdio session. Use deterministic fake LLM/MCP interfaces in
unit tests; use the actual F002 MCP server over stdio in integration validation.

**Rationale:** The existing client already exposes async context management, `discover()`, and
`call()`. A synchronous wrapper would add blocking and lifecycle complexity. External model
calls are unnecessary for routine tests.

**Source validation:** The pinned MCP Python SDK 1.28.1 `ClientSession` exposes asynchronous
`list_tools()` and `call_tool()` methods; the existing project client wraps these operations as
`MCPClient.discover()` and `MCPClient.call()`. See the
[MCP Python SDK 1.28.1 client session](https://github.com/modelcontextprotocol/python-sdk/blob/v1.28.1/src/mcp/client/session.py).

## Requirement and Scope Findings

- QR-018, QR-020, QR-021, QR-022, and QR-026 are assigned to F003 and have design decisions and
  planned verification in [plan.md](plan.md).
- QR-019 assigns the two named business workflows to F004. F003 establishes and verifies
  general multi-step orchestration without implementing those dedicated workflows.
- QR-015 and QR-016 are F001-owned requirements supported by F003's citation and refusal
  behavior.
- QR-027 is F002-owned; F003 documents its actual MCP client integration and protocol usage.
- The F003 scope does not add direct retrieval, new MCP/business tools, real email sending,
  approval/record mutation, or persistent confirmation storage.

## Remaining Validation

The configured Groq-compatible model and current free-tier limits must be validated during
implementation because model availability and tool-calling support can change. Keep model and
provider configurable; return an explicit error if configuration is unavailable. This is a
configuration validation item, not an unresolved architectural decision.
