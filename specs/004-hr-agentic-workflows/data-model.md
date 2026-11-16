# Data Model: HR Agentic Workflows

## Overview

F004 introduces no persistent entities, database, or new public response type. It composes
the existing F001 policy evidence, F002 synthetic results, and F003 request/response/trace
structures for two workflows. Results remain transient to one `HRAgent.process_request`
call except for the existing caller-carried email-draft proposal.

## Reused Entities

### Employee profile

Source: F002 `lookup_employee_profile`.

| Field | Meaning and workflow rule |
|---|---|
| `employee_id` | Synthetic identifier used to select the record. Only nonblank caller-provided `context.employee_id` is authoritative; missing or invalid context is clarified, and mismatched model-selected IDs are rejected before lookup. Free-text IDs are not authoritative. |
| `name`, `role`, `department` | Synthetic profile facts; include only when relevant to the response. |
| `work_arrangement` | Current recorded arrangement, not approval for a proposed change. |
| `work_state` | Current recorded state, not authorization for work in another state. |

The current record has no employee-specific device, network, account-security, or proposed
location approval field. The model must not infer those facts from policy excerpts.
The ID binding ensures consistency only; it is not caller authentication or authorization.

### PTO balance

Source: F002 `check_pto_balance`.

| Field | Meaning and workflow rule |
|---|---|
| `employee_id` | Synthetic employee to whom the balance belongs. |
| `available_hours` | Point-in-time available hours, not projected hours or an approval decision. |
| `as_of` | Date through which the returned balance is reported; retain this qualifier in guidance. |
| result `status` | `found` with a PTO record, or `not_found` when no record exists. Missing is not equivalent to zero. |

### Policy evidence

Source: F001 through F002 `search_policy_documents`.

Existing citation metadata includes document ID, title, optional section, snippet, and chunk
ID. Policy excerpts are candidate evidence. Policy claims must be grounded in returned
evidence; the agent must not represent a search result as an overall eligibility or compliance
decision.

### Approval facts and compliance result

Source: caller input passed to F002 `check_policy_compliance`, which supports only
`out_of_state_prior_approval`.

- `approval_facts` are caller-provided and not independently authenticated.
- The check's `conclusion` and result status apply only to the supported prior-approval
  question.
- Missing, contradictory, or inconclusive facts remain indeterminate; they do not prove
  overall remote-work eligibility.
- No extra approval or security fields are created by F004.

### Workflow response and citations

Source: F003 `AgentResponse` and `Citation`.

The response carries an answer, status, citations, evidence limitations, tool-call summaries,
operational trace, and optional clarification/confirmation data. F004 adds no response fields.
Employee claims must be grounded in the relevant structured result; policy claims must cite
returned policy evidence. Distinguish facts, recommendations, and unresolved questions.

### LLM final disposition

Source: the existing F003 `LLMCompletion` boundary, extended additively.

| Field | Type and meaning |
|---|---|
| `final_disposition` | `Literal["human_review_recommended"] | None`, default `None`. The model emits it as structured metadata with its final answer; the provider adapter validates and maps it. Tool-call completions and legacy callers/adapters may omit it. Any other non-`None` value is invalid. |
| `clarification_needed` | `Literal["employee_id"] | None`, default `None`. On a final completion, request a valid employee ID without copying the model's answer; reject other values and combinations with a tool call or final disposition. |

The final completion carries both the answer and disposition; if the disposition is present,
the accompanying answer must explicitly recommend human review based on the evidence
limitation. The agent must not infer the disposition from the answer text. A set disposition
maps to the existing public `AgentResponse.status` value `partial`; no public response field
or status is added.

An employee-ID clarification maps to the existing `clarification_needed` status and a fixed
clarification prompt. A missing signal does not bypass the missing-evidence fallback; an
existing tool failure without supporting evidence still takes precedence.

### Operational trace

Source: F003 `OperationalTrace` and `ToolInvocationRecord`.

Reuse discovery, intent, tool-call, completion, confirmation, refusal, and error events.
Records retain allowlisted argument names, outcome, duration, evidence count, and policy
source references; full employee results and raw user content remain outside traces.

When `final_disposition` is `human_review_recommended`, the existing completion event
includes the optional allowlisted `disposition` member with that value. Its existing
`outcome` remains the response status (`partial`), and the existing answer-basis field
remains unchanged. When the disposition is `None`, omit the member so existing trace
consumers see their current event shape. Do not copy model messages, answer text, internal
prompts, or reasoning into the trace.

Groq HTTP 400 errors may additionally record allowlisted error and request-structure metadata,
message roles, tool-call/result counts, and ID-match status in the existing error event. No raw
provider body, prompts, tool arguments/results, employee data, or call IDs are recorded.

### Email draft

Source: existing F002 `draft_hr_email` and F003 proposal-bound confirmation.

Draft data is synthetic, unsent, unpersisted, and returned only following an explicit user
request. Confirmation remains limited to the exact caller-carried proposal; it never sends
email or authorizes another action.

## Relationships and State

```text
Employee ID ──lookup──> Employee profile
Employee ID ──balance──> PTO balance (may be absent; absent != zero)
User question ──search──> Candidate policy evidence ──cite──> Workflow response
Caller approval facts ──supported check──> Prior-approval conclusion (may be indeterminate)
Explicit draft request ──draft──> Unsent proposal ──existing confirmation──> Simulated outcome
Tool selections/results ──summarize──> Operational trace
Final completion ──optional typed disposition──> Existing completion event
```

All workflow results are request-scoped. No F004 persistence or state transition is added.
