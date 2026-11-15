# Python Interface Contract: Agent Orchestration

## Overview

Feature 003 exposes an asynchronous Python agent interface. It uses the existing Feature 002
asynchronous MCP client and a configurable LLM provider with native tool calling. It does not
accept a Feature 001 retrieval client or directly call Feature 001.

## `HRAgent`

```python
class HRAgent:
    def __init__(
        self,
        mcp_client: MCPClient,
        llm_client: LLMClient,
        config: AgentConfig | None = None,
    ) -> None: ...

    async def process_request(
        self,
        user_input: str,
        context: dict[str, object] | None = None,
        options: dict[str, object] | None = None,
    ) -> AgentResponse: ...

    async def confirm_action(
        self,
        action_id: str,
        confirmation: bool,
        context: dict[str, object],
    ) -> AgentResponse: ...
```

### Initialization

- The caller opens the Feature 002 MCP client using its asynchronous context manager.
- The agent validates the connected client and discovers the live MCP tool catalog through
  `MCPClient.discover()`.
- Before each request, the agent refreshes the catalog through MCP discovery so the model uses
  current tool definitions and schemas.
- Discovery returns tool names, descriptions, and declared input schemas from the MCP server.
- The agent adapts supported discovered definitions for the configured LLM provider; it does
  not maintain duplicate argument schemas.
- Initialization failure is explicit. The agent does not fall back to direct Feature 001
  retrieval.

### `process_request`

**Arguments**

- `user_input`: nonempty natural-language request.
- `context`: optional caller-carried context, including a pending confirmation proposal from a
  prior response. Feature 003 does not persist this context.
- `options`: optional validated per-request overrides such as `top_k` or `max_tool_calls`.

**Behavior**

1. Validate input and construct an LLM request from the user request, permitted context,
   discovered tool definitions, and the feature/safety instructions.
2. Let the LLM interpret the request and select tools. Do not route from keyword rules or a
   hardcoded workflow graph.
3. If the model requests a tool, require one tool call for the turn; validate its name against
   current MCP discovery and its arguments against the declared schema.
4. Invoke through `await mcp_client.call(name, arguments)`. Return the structured result to the
   LLM in the next turn. Repeat sequentially until a final response, clarification/refusal, or
   `max_tool_calls` bound.
5. Access policy evidence only through `search_policy_documents`; do not call Feature 001
   directly or use `get_policy_section` as another evidence path.
6. Ground policy citations in returned policy evidence and structured claims in the relevant
   tool result. Report evidence conflicts without inventing a resolution.
7. For an email-draft request, use the existing F002 draft tool to prepare an unsent proposal,
   then return the proposal and request confirmation before reporting the simulated outcome.
   The answer clearly states that no email was sent. Refuse actual sending, approvals,
   employee-record updates, and unsupported mutations.
8. Return a structured response and concise operational trace. Do not put hidden reasoning,
   internal prompts, full user text, credentials, full records, or draft bodies in the trace.

**Raises**

- `ValueError`: invalid or empty input/configuration.
- `AgentInitializationError`: disconnected MCP client or discovery failure.
- `AgentRuntimeError`: unrecoverable model, MCP, validation, or trace failure.

Recoverable tool failures may produce a `partial` response only when available evidence supports
it. Failures are not represented as successful calls.

### `confirm_action`

- Requires the action identifier and pending proposal carried from the prior response.
- A confirmation applies only to the same draft proposal. A new or materially changed draft
  requires a new proposal and explicit confirmation.
- A negative confirmation reports cancellation.
- A positive confirmation reports the simulated draft outcome, clearly stating that no email
  was sent. The draft tool does not send, store, or persist the draft, and confirmation does
  not authorize another action.
- Unsupported action types are refused regardless of confirmation.
- The agent stores no pending action or confirmation record. The caller passes the pending
  proposal back in `context`.

**Raises**

- `ValueError`: missing or mismatched action identifier/proposal context.
- `AgentRuntimeError`: failure to validate the confirmation or emit the required trace.

## Supporting Types

### `AgentConfig`

```python
@dataclass
class AgentConfig:
    model_provider: str
    model_name: str
    temperature: float
    max_tokens: int
    top_k: int
    max_tool_calls: int
    mcp_server_command: str
    mcp_server_args: list[str]
    trace_sink: TraceSink
```

Values are validated and environment-configurable. Provider credentials are read from
environment variables and are never included in config traces or logs. Defaults and supported
environment variable names are documented in the quickstart. No retrieval-client, heuristic
confidence, or confirmation-persistence configuration is exposed.

### `AgentResponse`

```python
@dataclass
class AgentResponse:
    answer: str
    status: Literal[
        "answered",
        "partial",
        "clarification_needed",
        "confirmation_required",
        "out_of_scope",
        "error",
    ]
    citations: list[Citation] = field(default_factory=list)
    evidence_limitations: str = ""
    tool_calls: list[ToolInvocationRecord] = field(default_factory=list)
    operational_trace: OperationalTrace | None = None
    clarification_prompt: str | None = None
    confirmation_required: bool = False
    confirmation_prompt: str | None = None
    action_id: str | None = None
    pending_action: dict[str, object] | None = None
    error_code: str | None = None
```

**Invariants**

- `answered` and `partial` responses have a nonempty answer.
- `clarification_needed` has a nonempty `clarification_prompt`.
- `confirmation_required` has a nonempty prompt, `action_id`, and caller-returnable proposal
  context.
- `error` includes an error code and does not claim successful completion.
- Citations reference available policy evidence or MCP results and support the associated
  factual claim.
- Confirmed draft outcomes clearly state that no email was sent.

### `Citation`

```python
@dataclass
class Citation:
    source_type: Literal["policy_evidence", "tool_result"]
    source_id: str
    section: str | None = None
    snippet: str = ""
    claim: str = ""
```

Policy citations identify the document/title, optional section, and exact snippet returned by
`search_policy_documents`. Tool citations identify the relevant F002 tool result.

### `ToolInvocationRecord`

```python
@dataclass
class ToolInvocationRecord:
    tool_name: str
    status: Literal["success", "not_found", "indeterminate", "error", "timeout"]
    arguments_summary: dict[str, object]
    result_summary: dict[str, object]
    duration_ms: float
    error_code: str | None = None
```

Argument/result summaries are allowlisted. Raw arguments and full records may be used transiently
for MCP invocation and response generation but MUST NOT be written into operational traces.

### `OperationalTrace` and `TraceEvent`

Each trace contains a request identifier, UTC timestamps, duration, and events. Events record
observable intent category, selected tool, concise argument/result summaries, outcome category,
source IDs/sections, and clarification/escalation/failure category.

Trace data MUST exclude chain-of-thought, internal prompts, full raw user requests, credentials,
full employee records, email bodies, and unrestricted tool outputs. Tool-selection summaries
describe an observable category (for example, `policy evidence needed`), not private model
reasoning.

## LLM Client Boundary

`LLMClient` provides provider-native completion/tool-calling requests and returns either a
single structured tool call or a final response. The adapter handles provider-specific schema
format and result-message serialization, disabling parallel calls when supported. If a
provider returns more than one tool call in a turn, the agent rejects that model response
explicitly and does not invoke any of the requested tools.

Routine tests replace `LLMClient` with a deterministic fake. Model/provider failures are
surfaced explicitly; the agent must not fabricate a final answer when synthesis fails.

## MCP Client Boundary

Feature 003 uses the existing Feature 002 methods:

- `await mcp_client.discover()` obtains the live tool list and schemas through MCP.
- `await mcp_client.call(name, arguments)` invokes a discovered tool through MCP.

The client owns stdio transport, MCP session setup, protocol errors, and its own trace boundary.
Feature 003 does not import server implementation functions or call Feature 001's RAG API.

## Trace Failure Semantics

If agent trace persistence fails, the operation returns/raises an explicit runtime error rather
than silently claiming that a trace-complete request succeeded. The trace never contains hidden
reasoning or sensitive raw data.
