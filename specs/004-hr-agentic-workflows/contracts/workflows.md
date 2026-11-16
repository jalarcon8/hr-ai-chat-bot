# F004 Workflow Contract

## Contract Principles

- Both workflows use the existing `HRAgent.process_request` entry point and discovered
  Feature 002 MCP tools.
- The model selects one tool at a time; the agent executes calls sequentially within the
  existing call bound.
- The sequences below are representative, not a required global order. Tests must verify
  required evidence and result propagation without asserting identical order for every
  request.
- Policy evidence is retrieved through `search_policy_documents`; do not add a second
  retrieval path or call `get_policy_section` as a parallel evidence source.
- All employee examples and policy fixtures are synthetic.
- Callers supply a nonblank `context.employee_id` for employee-specific lookups. The agent
  rejects a model-selected ID that does not exactly match this value before MCP execution.
  IDs appearing only in request text are not authoritative. This is an identity-consistency
  safeguard, not authentication or authorization; policy-only requests need no employee ID.

## PTO Request Guidance

### Inputs

- Employee ID in `context.employee_id` when the question requires person-specific guidance.
- Requested dates or hours when comparing a request to available balance.
- Recipient and purpose/details only when the user explicitly asks for a manager email draft.

### Representative sequence

```text
lookup_employee_profile(employee_id)
check_pto_balance(employee_id)
search_policy_documents(question, k)
[draft_hr_email(recipient_name, purpose, supporting_details) only on explicit request]
```

The three read-only lookups may occur in another sequential order. A draft is a separate,
explicitly requested action after any required details have been supplied.

### Required result handling

- Combine profile facts, PTO result, and relevant policy citations when the request needs
  them.
- Identify `available_hours` as reported `as_of` the returned date; do not calculate or
  describe a projected balance unless a supported calculation is added in a separately
  approved scope.
- `not_found` PTO is unavailable, not zero. A returned `available_hours: 0` is a found
  zero-hour balance.
- Explain the relevant request and approval process without claiming submission, approval,
  denial, or an exception.
- If ID, dates, hours, or draft details are missing, ask for only what is needed and do not
  attribute data to an unidentified employee.
- If evidence is insufficient, direct the employee to the relevant human function without
  promising an exception or legal/payroll outcome.
- Drafting must remain unsent and use F003's existing proposal-bound confirmation behavior.

### Fixed test examples

- `TEST-001`: found profile; 40 available hours as of `2026-01-01`.
- `TEST-002`: found profile; no PTO record. Expected guidance distinguishes unavailable from
  zero.
- `TEST-003`: found profile; zero available hours as of `2026-01-01`.

Routine tests use controlled policy search results containing a synthetic PTO excerpt and
assert that the returned citation reaches the final response. The actual MCP integration
test copies `tests/fixtures/mcp/f004-policies/hr-pto.md` into a temporary corpus, separate
from the pinned F002 baseline, and requests 8 hours on `2026-02-01` for `TEST-001`. Its
expected result includes the profile, 40 hours as of `2026-01-01`, and an `HR-005` citation.

## Remote-Work Guidance or Escalation

### Inputs

- Employee ID in `context.employee_id` for profile-specific guidance.
- Proposed state/location and arrangement, if relevant to the question.
- Caller-provided prior-approval facts only when the existing supported check is applicable.

### Representative sequence

```text
lookup_employee_profile(employee_id)
search_policy_documents(question, k)  # remote-work, location, and security evidence
[check_policy_compliance(
    check_id="out_of_state_prior_approval",
    approval_facts=<caller-provided facts>
) only for the supported out-of-state prior-approval question]
```

Policy/profile calls may be reversed. The compliance check is conditional and is not a
general remote-work eligibility check. Do not call it for international work or unrelated
approval rules.

### Required result handling

- Clearly distinguish recorded current `work_state`/`work_arrangement` from approval for a
  proposed location or arrangement.
- Treat approval facts as caller-provided and unverified, even when the supported check
  returns a conclusion.
- Report the compliance result only within the existing out-of-state prior-approval scope.
- Policy evidence may describe security requirements; it cannot establish that the
  synthetic employee's device, network, or account satisfies them.
- When missing approval/security facts or unsupported policy rules prevent a determination,
  state the gap and direct the user to the responsible reviewer rather than asserting
  eligibility or ineligibility.
- International work, conflicting sources, tool failures, and insufficient evidence must
  remain unresolved and be directed to human review.

### Fixed test examples

- Use `TEST-002` (current recorded state `OR`, arrangement `remote`) to ensure current profile
  data is not treated as approval for a proposed location.
- For the supported check, include fixed caller facts in the scripted tool call and verify
  those exact facts are passed to MCP. Include an incomplete/indeterminate case.
- Use policy results that identify applicable remote-work and security controls while
  providing no employee-specific security posture. Expected answer must not claim that the
  employee satisfies those controls.
- Include a case where all MCP calls succeed and return candidate evidence, but the evidence
  does not establish eligibility. The same final completion must contain an answer
  recommending review and `final_disposition="human_review_recommended"`.
- The stdio test asks about `TEST-002` working in `CA` and supplies written
  People Operations approval dated `2026-01-01T10:00:00Z`, before travel on
  `2026-01-02T10:00:00Z`. It checks that these unverified facts reach the existing
  prior-approval tool unchanged. The temporary corpus includes
  `tests/fixtures/mcp/f004-policies/hr-security.md`; the response cites `HR-004`
  and `HR-006`, remains `partial`, and records the human-review disposition.

## Trace and Failure Contract

### Typed final disposition

The existing F003 `LLMCompletion` boundary has
`final_disposition: Literal["human_review_recommended"] | None = None`. F004 uses only the
`human_review_recommended` value; `None` preserves existing behavior. The model emits this
optional value as structured metadata with its final answer in one completion; the provider
adapter validates and maps it into `LLMCompletion`. It is not inferred by parsing answer
text, and it does not require another model call. Any other non-`None` value is an explicit
invalid completion.

When set, the existing completion event records
`disposition="human_review_recommended"` alongside its existing `outcome` and `answer_basis`.
The existing outcome remains the public response status (`partial`); no new `AgentResponse`
field or status is added. The answer and disposition are emitted together, and the final
answer must explicitly recommend human review when the disposition is set.

For each workflow, inspect the existing trace and response for:

- Sequential tool names and outcomes, with allowlisted argument/output summaries.
- Returned policy source references and citations where policy claims are made.
- Explicit missing-ID clarification, `not_found`, `indeterminate`, tool/model failure, and
  bounded-call outcomes.
- The typed human-review disposition when all calls succeed but the final evidence does not
  establish remote-work eligibility.
- No raw employee record, raw user input, credentials, internal prompt, or hidden reasoning.

The disposition is allowlisted metadata only. Traces must not copy the final answer or other
provider output to derive or represent it.

## Out of Scope

- New MCP tools, compliance rules, security data, HR integrations, or persistence.
- Email delivery, request submission/approval, or record mutation.
- Fixed mandatory tool ordering, a hardcoded workflow graph, F005 UI/API, or F006 evaluation
  and demo deliverables.
