# F004 Validation Quickstart

## Prerequisites

- Python 3.11 and the repository's existing development dependencies installed.
- Run commands from the repository root.
- No Groq key, live model, live HR system, or real employee data is needed for routine tests.
- Agent acceptance tests use `ScriptedLLM` and fixed synthetic results. MCP integration tests
  use the existing stdio fixture harness and controlled model responses.
- Integration tests copy isolated F004 policy fixtures into a temporary corpus; the pinned
  F002 baseline and production corpus are not changed.
- Scripted completions test orchestration for selected model outputs; they do not prove a
  live provider will always select the appropriate tools or produce the required answer.
- For employee-specific requests, provide a nonblank ID in `context.employee_id`, for example
  `context={"employee_id": "TEST-001"}`. An ID in user text alone is not authoritative.
  A model-selected mismatch fails before MCP execution. This is not authentication or
  authorization; policy-only requests do not need employee context.

If dependencies are not installed yet, follow the repository README's local setup instructions.

## Deterministic Acceptance

Run the F004 agent acceptance tests:

```powershell
.\.venv\Scripts\python -m pytest tests\test_f004_workflows.py -q
```

Expected outcomes:

- PTO response combines the synthetic employee profile, balance with its `as_of` date, and a
  returned policy citation.
- Missing PTO for `TEST-002` is reported as unavailable; the found zero-hour record for
  `TEST-003` remains a distinct result.
- Missing employee identifiers are clarified before employee-specific lookup. An ambiguous
  employee name or identifier selects no record; the agent requests a valid employee ID
  before employee-specific lookups or claims, without searching by name or resolving identity.
- Remote-work response does not treat the current `TEST-002` profile as authorization for a
  proposed location and does not infer a security posture from policy text.
- The prior-approval tool is called only for its supported out-of-state check and receives
  only the caller-provided facts.
- An unsupported international-work request does not invoke the out-of-state prior-approval
  tool. Where policy evidence is available, the response cites it and recommends human review
  without claiming eligibility.
- In the remote-work insufficiency case, all MCP calls succeed and return candidate evidence,
  but eligibility remains unestablished. The controlled final completion carries both an
  explicit human-review recommendation and
  `final_disposition="human_review_recommended"`; the response uses the existing `partial`
  status and the completion trace records the disposition.
- A completion with `final_disposition=None` retains existing behavior. No test or runtime
  path infers the disposition by parsing answer text.
- A value outside the single allowed disposition is rejected explicitly rather than
  producing a success-shaped response.
- An explicitly requested email draft remains unsent and follows the existing confirmation
  flow.
- Traces contain allowlisted tool/evidence outcomes and no hidden reasoning or private fixture
  values. The disposition is a single allowlisted enum value, not model reasoning or answer
  content.
- A mocked provider-adapter test verifies same-response structured disposition mapping and
  unchanged native tool-call handling; it does not call the live model.

## Manual Provider Compatibility Checkpoint

Before Milestone 1 is considered complete, manually verify that the configured live provider
can return `human_review_recommended` with its final answer in the same completion while
preserving native tool-call behavior. This checkpoint is separate from the mocked
provider-adapter tests and is not part of routine CI; use only synthetic inputs.

Final acceptance also requires manual synthetic live checks for the PTO balance and its
as-of date, remote-work escalation, missing or ambiguous identity, and a request without
an explicit email draft. Check actual tool calls, answer, and privacy-safe trace; do not
rely on scripted selections as proof. Record provider errors separately from behavior
failures, without recording credentials or unnecessary raw data.
Supply `context.employee_id` for positive employee-specific live scenarios and omit it for
missing/ambiguous identity scenarios, even if an ID appears in the request text.

### Controlled Synthetic Acceptance Diagnostic

The F004 MCP integration scenarios use an in-memory observer around the existing MCP client.
It inspects actual dispatched arguments and structured results, matching returned policy
evidence to response citations and checking the user-facing answer. It does not inspect
provider requests, headers, environment variables, internal prompts, or hidden reasoning.
The existing operational traces and their privacy contract are unchanged. The observer
records attempted calls even when the MCP client fails.

Routine tests use fixed synthetic inputs and scripted completions; their success does not
establish live model behavior. The PTO scenario verifies the profile and balance results,
balance/date/units in the answer, and a matching PTO citation. The remote-work scenario
verifies profile facts, exact caller-provided compliance arguments and results, both
citations, partial status, and the human-review disposition. Separate scenarios check that
guidance does not call the draft tool without an explicit request and that an explicit
request produces an unsent draft requiring confirmation.

Live cases are opt-in and must be run only after approval, one selected case per invocation.
For example, to select only PTO:

```powershell
$env:AGENT_RUN_F004_LIVE = "1"
.\.venv\Scripts\python -m pytest 'tests\integration\test_f004_workflows_mcp.py::test_pto_workflow_uses_real_mcp_results_and_cited_policy[live]' -q -rs --tb=no --show-capture=no
```

Select the `[live]` case for `test_remote_work_uses_real_mcp_results_and_records_human_review`
or `test_guidance_without_explicit_draft_never_calls_draft_tool` separately; the optional
explicit-draft case is `test_explicit_draft_uses_real_mcp_and_requires_confirmation`.
Use the existing provider configuration; do not put credentials in the command. Restore or
remove the opt-in environment variable after the controlled session.

For manual semantic review, set a debugger breakpoint immediately after the observed
`process_request` call in the selected test. Inspect `observations` and `response.answer`
in the debugger's variable view, using only the controlled synthetic fixture. Do not copy
them to a console, transcript, file, debugger log, or test report; do not enable pytest
`--showlocals`, captured output, or raw provider logging. The opt-in PTO, remote-work, and
no-draft tests intentionally report **inconclusive** after their automated checks: a
reviewer must also verify the actual answer's meaning and required policy guidance. A PTO
balance evaluator mismatch is inconclusive, not proof of an omission. Record only safe
pass/fail/inconclusive classifications, tool names and outcomes, and existing sanitized
provider diagnostics. A failed automated check or provider error stops that scenario.

The observer is for controlled test fixtures, not arbitrary deployed user input. Synthetic
fixtures alone do not guarantee that generated free text contains no credentials. F005
owns any later interface for deployed diagnostic access; these tests do not create one.

## MCP Protocol Integration

Run the F004 stdio MCP integration tests:

```powershell
.\.venv\Scripts\python -m pytest tests\integration\test_f004_workflows_mcp.py -q
```

Expected outcomes:

- Tool discovery and calls use the actual F002 MCP server over the existing stdio harness.
- Synthetic profile, PTO, policy search, and supported compliance calls use their existing
  schemas and result forms.
- A controlled LLM response consumes actual MCP results and produces cited workflow output
  or an explicit limitation. For insufficient remote-work evidence, its same final completion
  supplies `human_review_recommended`, which appears in the existing completion trace event.
- Integration uses deterministic embeddings and fixture data; it does not call a live LLM.

## Regression and Static Checks

Run directly related existing tests:

```powershell
.\.venv\Scripts\python -m pytest tests\test_agent_acceptance.py tests\unit\test_agent_llm.py tests\unit\test_agent_confirmation.py tests\unit\test_agent_trace.py tests\integration\test_agent_mcp.py -q
```

Run repository-wide lint, as required by T021:

```powershell
.\.venv\Scripts\python -m ruff check .
```

## Traceability References

- Scenario inputs, representative calls, expected outputs, and failure behavior:
  [contracts/workflows.md](contracts/workflows.md).
- Reused entity/result semantics and the typed final disposition:
  [data-model.md](data-model.md).
- F004's assigned Quantic requirement mapping and QR-020 design:
  [plan.md](plan.md).

The exact MCP order may vary with model tool selection. Validate the required calls, their
sequential result propagation, and the resulting evidence; do not require a single identical
sequence for every request.
