# Contract: MCP Tools

These are proposed implementation contracts, not an assertion that the tools already exist.
All six are exposed by one FastMCP server and invoked via MCP stdio. Required strings must
be nonblank; integers must not be booleans. Reject unknown arguments, invalid types, unsupported
enums and invalid values as MCP tool errors. Optional `supporting_details`, when supplied, is
a string. Exact JSON schemas and SDK serialization are verified against actual tool discovery.

## Successful result envelope

Each successful result has `status` and the tool-specific fields below. `status` is `found`,
`not_found`, or `indeterminate`; fields not applicable to that status are absent except where
specified. Policy evidence fields are defined in [data-model.md](../data-model.md). MCP
`structuredContent` carries this object and the SDK may additionally return JSON text content.

| Tool | Required inputs | Optional inputs | `found` | Valid absence or uncertainty |
|---|---|---|---|---|
| `search_policy_documents` | `question: string` | `k: integer >= 1`, default 5 | `evidence_kind: "candidate"`, `evidence: list` of scored candidates, `generation_id` | `not_found` only when retrieval completes with no chunks; empty `evidence` and `generation_id` |
| `get_policy_section` | `document_id: string`, `section: string` | none | `evidence: list` of matching unscored excerpts, `generation_id` | `not_found` for no document or section; empty `evidence` and `generation_id` |
| `lookup_employee_profile` | `employee_id: string` | none | `employee` matching the synthetic employee model | `not_found`, `missing: "employee"` |
| `check_pto_balance` | `employee_id: string` | none | `pto` matching the synthetic PTO model | `not_found`, `missing: "employee"` or `"pto"` |
| `check_policy_compliance` | `check_id: "out_of_state_prior_approval"` | `approval_status: "approved" \| "not_approved" \| "unknown"`; omitted means unknown | `check_id`, `conclusion: "compliant" \| "noncompliant"`, `evidence`, `limitations: []` | `indeterminate`, `conclusion: "indeterminate"`, `evidence` (possibly empty), nonempty `limitations` |
| `draft_hr_email` | `recipient_name: string`, `purpose: string` | `supporting_details: string` | `draft: {subject, body}` | Invalid inputs are errors, never empty success |

Search `found` means retrieval returned candidates, not that they answer the question. Preserve
F001 ranking and all returned scores. Section selection uses exact document and section labels
from the active generation; matching snippets are sorted by source offset and retain overlap.
Both preserve source excerpts and generation identity. Section evidence lacks a score.

Compliance receives facts from the caller, not employee lookup. It checks only the specific
prior-written-People-Operations-approval rule; missing or changed policy evidence or an unknown
approval fact gives `indeterminate`. With sufficient reviewed evidence, `approved` gives
`compliant` and `not_approved` gives `noncompliant`. Never characterize the result as overall
eligibility or authorization. The reviewed-baseline and completeness checks are specified in
[research.md](../research.md). There is no email sending, storage, or other external action.

## Failures and tracing

Input validation and operational failures use MCP tool errors (`isError=true`), not a success
status. Error content is sanitized; the client maps them to stable categories:
`invalid_argument`, `index_unavailable`, `embedding_failure`, `data_unavailable`, or
`internal_error`. SDK-generated schema-validation messages may not carry a custom code;
the provided client maps those to `invalid_argument` without logging raw messages or inputs.
Unknown tool, discovery, connectivity, and transport failures are client-side errors, not
`not_found`; the client maps them to `unknown_tool`, `discovery_failure`, or `transport_failure`.
If mapping is not reliable for an SDK failure, use `internal_error`, not a guessed success.

The server writes an allowlisted trace for every received tool-call attempt from any client,
including invalid requests rejected before the tool body. The provided client traces discovery
and client-side failures, including failed connections. Trace failures are surfaced. See
[data-model.md](../data-model.md); do not log arbitrary SDK exception strings or request and
response bodies.

## Acceptance examples

- Search with a deterministic embedder and unrelated query: nonempty results are `found`,
  `evidence_kind` is `candidate`, and scores do not imply support.
- Request a known document/section and a missing section; verify ordered exact excerpts and
  `not_found`, respectively.
- Look up a known employee, an unknown employee, and a known employee with no PTO record;
  verify matched records and distinct missing categories.
- Check approved, not approved, omitted, and unknown approval against the reviewed policy;
  verify respective verdicts. A changed, absent, or fragmented policy is `indeterminate`,
  while a corrupt index produces an MCP error.
- A draft is deterministic and causes no email, network, or record mutation. Invalid types,
  blank strings, zero/boolean `k`, unsupported checks, and unknown arguments fail as errors.
- Disconnect the server and request an unknown tool through the client; verify distinguishable
  failures and redacted trace events.
