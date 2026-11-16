# Data Model: Agent Orchestration

## Overview

Feature 003 coordinates the existing Feature 002 MCP client and a configurable LLM provider.
It introduces request/response and trace structures, but no retrieval client, tool server,
database, or persistent agent state. MCP tool definitions and results remain governed by
Feature 002 contracts.

## Agent Request

| Field | Type and meaning |
|---|---|
| `user_input` | Nonempty natural-language request. Used for the current model exchange; not copied verbatim into operational traces. |
| `context` | Optional caller-carried data needed for this request, including `employee_id` for employee-specific lookups and a pending email-draft proposal/action identifier from a prior response. The agent does not persist it. |
| `options` | Optional validated per-request overrides such as `max_tool_calls`, `top_k`, or output-token limit. |

## Discovered MCP Tool

The agent receives tool names, descriptions, and input schemas from the live Feature 002 MCP
discovery result at initialization and refreshes the catalog before each request. These are
converted to the configured LLM provider's native tool-call format; schemas are not duplicated
in Feature 003.

- The current Feature 002 baseline exposes six tools:
  `search_policy_documents`, `get_policy_section`, `lookup_employee_profile`,
  `check_pto_balance`, `check_policy_compliance`, and `draft_hr_email`.
- Discovery validates and records the available catalog; SC-001 requires at least four, and
  integration validation checks all six.
- Policy evidence is obtained exclusively via `search_policy_documents`. The agent does not
  call Feature 001 directly or use `get_policy_section` as another evidence path.
- The model selects from tools within Feature 003's supported scope. Before invocation, the
  agent validates the selected tool against the current discovery result and validates
  arguments against its declared schema.
- For `lookup_employee_profile` and `check_pto_balance`, the sole authoritative ID is a
  nonblank string supplied as `context.employee_id`. A missing or invalid ID requests
  clarification; a selected ID that differs exactly from the caller's ID is rejected before
  execution. Free-text IDs are not authoritative. This binds identity consistently; it does
  not authenticate the caller or authorize access.
- Unsupported tool capabilities or state-changing actions are refused; the model cannot
  expand the feature's business-operation scope.

## Orchestration Turn

An orchestration turn is transient state for a single `process_request` call:

| Field | Type and meaning |
|---|---|
| `messages` | Provider-compatible request history for the current call, including the user request and assistant/tool result messages. |
| `intent_category` | Concise observable category such as `policy_question`, `data_lookup`, `multi_step`, `ambiguous`, or `out_of_scope`. Not a reasoning transcript. |
| `tool_calls_made` | Number of completed MCP calls in the current request. |
| `max_tool_calls` | Positive configured bound; reaching it yields an explicit bounded/partial outcome, not a success-shaped fallback. |
| `evidence` | Transient references to structured MCP results used for synthesis and citations. Not persistent agent state. |

Each LLM turn may request one MCP call. The agent validates and invokes that call through
Feature 002, appends the structured result, and requests the next model turn. The loop ends
with a model final response, a clarification/refusal/error, or the call bound.

## Tool Invocation Record

| Field | Type and meaning |
|---|---|
| `tool_name` | Exact discovered MCP tool name. |
| `status` | `success`, `not_found`, `indeterminate`, `error`, or `timeout`, as applicable. |
| `arguments_summary` | Allowlisted argument names and concise non-sensitive summaries for response/trace use. Raw arguments are transient only. |
| `result_summary` | Outcome category and safe counts/identifiers; not a full result in the operational trace. |
| `source_refs` | Source document IDs/sections or tool-result references used by the answer. |
| `duration_ms` | Elapsed MCP invocation time. |
| `error_code` | Safe structured error code, if present. |

MCP structured results remain available transiently to the model for synthesis. Tool failures
remain distinct from valid `not_found` or `indeterminate` results.

## Agent Response

| Field | Type and meaning |
|---|---|
| `answer` | User-facing grounded response or concise clarification/refusal/failure message. |
| `status` | `answered`, `partial`, `clarification_needed`, `confirmation_required`, `out_of_scope`, or `error`. |
| `citations` | Evidence references supporting factual claims. |
| `evidence_limitations` | Missing, conflicting, incomplete, or unavailable evidence, if any. |
| `tool_calls` | Invocation records with safe summaries. |
| `operational_trace` | Structured observable events for this request. |
| `clarification_prompt` | Present when additional user information is required. |
| `confirmation_required` | True only when a specific email-draft proposal awaits confirmation. |
| `confirmation_prompt` | Describes the exact proposed draft and requests explicit confirmation. |
| `action_id` | Identifier bound to the exact pending proposal; a materially changed proposal requires a new identifier and confirmation. |
| `pending_action` | Optional proposal/context for the caller to carry to the next request. The agent does not persist it. |
| `error_code` | Safe machine-readable error category when `status` is `error`. |

### Response invariants

- `answered` and `partial` responses contain a nonempty answer.
- `clarification_needed` contains a nonempty clarification prompt.
- `confirmation_required` contains an action-specific prompt, action identifier, and proposal
  context sufficient for a later confirmation request.
- `out_of_scope` clearly states that the request is unsupported; it does not offer a simulated
  success for an unimplemented capability.
- Every factual claim and citation is grounded in the current request context or returned tool
  evidence. Conflicting sources are reported without an invented resolution.
- A confirmed email-draft response clearly states that no email was sent. No send, approval,
  employee-record update, or persistent mutation is performed.

## LLM Completion

The internal `LLMCompletion` carries the final answer and tool-call selection for one provider
turn. Its optional
`final_disposition: Literal["human_review_recommended"] | None = None` is set only on a final
completion, never on a tool-call turn. The provider adapter validates the structured final
payload and supplies the disposition without deriving it from the answer text. Legacy callers
that omit the field retain the default `None`.

The optional `clarification_needed: Literal["employee_id"] | None = None` signals an
employee-ID clarification on a final completion. It cannot coexist with a tool call or final
disposition. The agent returns the existing clarification status with a fixed prompt rather
than displaying unsupported model text.

A set `human_review_recommended` disposition requires the accompanying user-facing answer to
explicitly recommend human review. The agent maps it to the existing `partial` status; no
public response field or status is added.

## Citation

| Field | Type and meaning |
|---|---|
| `source_type` | `policy_evidence` or `tool_result`. |
| `source_id` | Source document ID/title or exact tool-result reference. |
| `section` | Policy section when returned by the source; otherwise null. |
| `snippet` | Exact policy excerpt or concise structured-data summary appropriate for the user. |
| `claim` | The user-facing fact supported by this source. |

Policy citations come from `search_policy_documents` results and preserve the returned document
ID/title, section when present, and exact snippet. Employee or operational claims cite the
relevant F002 tool result.

## Email-Draft Confirmation

| State | Behavior |
|---|---|
| `proposal_prepared` | Existing `draft_hr_email` returns an unsent, unpersisted mock draft. The agent presents the proposal and asks for explicit confirmation. |
| `confirmed` | A later request carries the same proposal/action identifier and explicit confirmation. The agent returns the simulated draft outcome, stating no email was sent. |
| `cancelled` | The caller carries the same proposal/action identifier with a negative confirmation; the agent reports cancellation. |
| `new_or_changed_proposal` | A new or materially changed draft has a new identifier and requires new confirmation. |

The pending proposal is carried by the caller in request context between calls. It is not
stored by Feature 003. Confirmation applies only to the exact proposal; it does not authorize
actual email delivery or another operation.

## Operational Trace

### Trace event

Each event contains a UTC timestamp, `event_type`, observable outcome `status`, and concise
allowlisted `details`.

| Event type | Observable details |
|---|---|
| `discovery` | Discovered tool names/count and discovery outcome. |
| `intent_analysis` | Intent category, decision category, and whether clarification is required. |
| `tool_call` | Selected tool name, argument-name/summary allowlist, result category, duration, and evidence references. |
| `confirmation` | Draft action identifier, `requested`/`confirmed`/`cancelled` outcome, and whether reconfirmation was required. |
| `error` | Error category/code, affected tool if known, and recoverability category. |
| `completion` | Final response status, tool-call count, citation count, and escalation/clarification outcome; optionally the allowlisted `disposition="human_review_recommended"`. |

### Trace requirements

Traces include concise, observable intent categories, selected tools, outcome categories, and
evidence/source references. An optional short decision summary may explain the tool selection
at a user-observable level (for example, `policy evidence needed`); it must not expose internal
reasoning. The completion disposition is included only when present and is not inferred by
parsing answer text.

Traces MUST NOT contain hidden chain-of-thought, internal prompts, full user questions,
credentials, full employee records, email bodies, or unrestricted raw tool arguments/results.
Use an allowlist rather than storing model messages and attempting to redact them afterward.
For Groq HTTP 400 errors, the error event may include only allowlisted provider error category,
request structure, message roles, tool-call counts, and call/result-ID match status.

## Configuration

| Setting | Meaning |
|---|---|
| `model_provider` / `model_name` | Configured provider and tool-calling model. |
| `temperature` | Sampling setting, validated within provider-supported bounds. |
| `max_tokens` | Maximum generated response tokens. |
| `top_k` | Search-result limit passed to the MCP policy-search tool when applicable. |
| `max_tool_calls` | Positive upper bound on sequential MCP calls per request. |
| `mcp_server_command` / `mcp_server_args` | Existing F002 stdio client configuration. |
| `trace_sink` | Configured project trace destination. |
| API credentials | Environment-only values; never included in configuration output or traces. |

Defaults and environment variable names are documented in the quickstart. No
`intent_confidence_threshold`, direct retrieval-client setting, retrieval-only fallback, or
persistent confirmation-store setting is introduced.

## Error Handling

| Condition | Required behavior |
|---|---|
| MCP connection/discovery unavailable | Explicit initialization/runtime error; no direct Feature 001 fallback. |
| Model/provider unavailable | Explicit model error; do not report a successful answer without synthesis. |
| Tool name not in discovery catalog or unsupported by F003 | Reject the call and report a safe error/refusal. |
| Invalid/missing tool arguments | Reject against the discovered schema; ask the user for missing facts rather than guessing. |
| MCP error/timeout | Surface the failure; provide a partial answer only when remaining evidence supports it. |
| No policy result or conflicting evidence | Identify the evidence limitation; do not fabricate or resolve conflicts. |
| Tool-call limit reached | Return a clear bounded/partial result; do not claim workflow completion. |
| Confirmation does not match pending proposal | Reject confirmation for that proposal and require confirmation for the current action. |
| Trace persistence fails | Surface an explicit operational error; do not silently claim trace-complete success. |

## Design Notes

- Feature 001 retrieval is accessible only through F002's `search_policy_documents` MCP tool.
- Feature 003 uses the existing F002 client and protocol rather than importing server logic.
- LLM tool selection is dynamic; only the sequential execution loop and safety/schema checks
  are deterministic.
- Traces describe observable decisions and results, never hidden reasoning.
- The only confirmation workflow is the existing unsent email-drafting capability.
