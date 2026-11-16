# Research: HR Agentic Workflows

## Decisions

### Decision 1: Reuse the existing HRAgent and its native tool-calling loop

**Decision**: Implement workflow-specific interpretation guidance in the existing agent
prompt and preserve dynamic tool selection, one tool per model turn, sequential MCP
execution, and the configured call bound.

**Rationale**: `HRAgent.process_request` already discovers the F002 catalog, validates calls
against live schemas, sends structured results back to the LLM, and handles clarification,
failures, citations, and safe actions. A second workflow engine or hardcoded call graph would
duplicate these responsibilities and conflict with F003's contract.

**Alternatives considered**:

- Add a separate workflow class or state machine: rejected as unnecessary duplication.
- Add workflow-specific MCP tools: rejected because F002 already exposes the required
  operations and new compliance behavior is out of scope.
- Change tool signatures: rejected because no F004 requirement requires an interface change.

### Decision 2: Preserve existing evidence and safety boundaries

**Decision**: Retrieve policy evidence only through `search_policy_documents`; use the
existing profile, PTO, compliance, and email-draft tools. Treat compliance input as caller
context, not authenticated proof. Keep draft generation unsent and proposal-bound.

**Rationale**: This reuses F001-F003 and F002 contracts without bypassing MCP. The tool
`check_policy_compliance` supports only the existing out-of-state prior-approval check; it
does not determine overall remote-work eligibility or employee-specific security posture.

**Alternatives considered**:

- Add security posture or approval data to synthetic records: rejected because those facts
  are not available in the approved scope and would make unsupported decisions appear
  established.
- Add new approval/compliance rules: rejected as explicitly out of scope.
- Use `get_policy_section` as another evidence path: rejected; the F003 contract uses policy
  search as the sole evidence path.

### Decision 3: Keep tests deterministic and exercise the real MCP boundary

**Decision**: Use fixed synthetic tool results and `ScriptedLLM` for routine acceptance
tests; use the existing stdio integration harness to verify the MCP discovery/call boundary
with controlled model responses. Add only test fixture policy evidence needed to cover
missing F004 policy topics.

**Rationale**: This isolates agent behavior from provider variability while verifying
actual MCP schemas, transport, and server behavior. It follows the existing test architecture
and constitution without adding a full evaluation framework.

**Alternatives considered**:

- Require a live Groq call in routine tests: rejected because it is nondeterministic,
  credential-dependent, and may consume quota.
- Test only fake MCP clients: rejected because it would not verify protocol integration.
- Add a new integration service or test framework: rejected as unnecessary.

### Decision 4: Document representative sequences, not a workflow graph

**Decision**: Describe the required evidence and representative call sequences in
`contracts/workflows.md`; permit different valid sequential orders.

**Rationale**: The order can vary with the request and LLM tool selection. The acceptance
contract concerns the information used, grounding, safe outcomes, and traceability rather
than a fixed implementation sequence.

**Alternatives considered**:

- Require one exact tool order for every request: rejected because it would constrain the
  existing LLM-native orchestration without adding user value.
- Omit expected sequences: rejected because QR-047 explicitly requires them.

### Decision 5: Carry human-review disposition through the existing completion boundary

**Decision**: Add
`final_disposition: Literal["human_review_recommended"] | None = None` to `LLMCompletion`.
The model emits the optional disposition as structured metadata with its final answer in one
completion; the provider adapter validates and maps it into `LLMCompletion`. The agent
records it as an optional `disposition` on the existing completion trace event and uses the
existing `partial` response status. No public `AgentResponse` field or status is added.
Reject any non-`None` value outside the allowed literal as an explicit invalid completion.

**Rationale**: The current trace already records tool-derived clarification, `not_found`,
`indeterminate`, errors, answer basis, and generic completion outcome. It cannot tell that
the model recommends human review when every tool succeeds but the returned evidence does
not establish eligibility. The typed field supplies that missing signal without parsing
answer text, adding a model call, or creating another trace or orchestration system.

The final answer and disposition are emitted together. The final-output contract requires
that a `human_review_recommended` disposition accompany an answer that explicitly recommends
review based on the evidence limitation. The agent does not try to determine this by
matching words in the answer. Deterministic acceptance tests verify the answer/disposition
pair and the trace event.

**Compatibility**: `final_disposition` defaults to `None`. Tool-call completions and existing
callers/provider adapters that omit the field preserve current behavior. The configured
adapter maps the structured model metadata when present; it must support the F004
human-review scenario. Existing completion `outcome` values and the public `AgentResponse`
shape/status vocabulary remain unchanged. The new trace member is optional and allowlisted.
Update the provider adapter, scripted test helper, and F003 interface/data-model
documentation together.

**Alternatives considered**:

- Treat every `answered` or `partial` status as an escalation: rejected because those
  statuses do not establish that a human review was recommended.
- Parse natural-language phrases: rejected as unreliable and expressly prohibited by the
  design decision.
- Add a new trace subsystem, orchestration step, or model call: rejected as unnecessary.
- Add broader outcome categories: rejected; only `human_review_recommended` is required.

## Technical Context Findings

- Runtime baseline is Python 3.11; dependencies are pinned in `pyproject.toml`.
- `HRAgent` already uses only discovered supported MCP tools and enforces a positive
  `max_tool_calls` bound.
- Employee profile records contain current work arrangement and work state, but no
  employee-specific security posture or proposed-location approval.
- PTO results contain `available_hours` and `as_of`; `not_found` for PTO is distinct from a
  zero-hour record.
- Existing traces store tool names, outcomes, allowlisted argument-name summaries, evidence
  counts, policy document references, completion outcome, answer basis, and sanitized
  errors. They do not store full tool results or generated hidden reasoning. F004 adds only
  the optional disposition on the existing completion event.
- The integration test harness launches the MCP fixture server over stdio and can record
  protocol calls. Routine agent tests use a deterministic scripted LLM.
- F005 owns the grader-facing interface; F006 owns the evaluation set/metrics and final demo.
  F004 supplies scenarios and contracts only.

## Disposition Invariant and Verification

For a remote-work request where all MCP calls succeed but candidate policy evidence does not
establish eligibility, the controlled final completion returns both an answer recommending
the responsible human review and `final_disposition="human_review_recommended"`. The
response retains its existing public shape and uses status `partial`; the existing completion
event records the optional disposition alongside the current outcome and answer basis.

Routine tests also verify that `None` leaves existing behavior unchanged and that review
metadata is taken only from the typed completion field, not parsed from answer text. No
hidden reasoning, unrestricted provider output, or raw employee data is copied into traces.
