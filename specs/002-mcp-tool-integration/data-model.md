# Data Model: MCP Tool Integration

All records are fictional. JSON files are the initial read-only source of truth; malformed
files, duplicate IDs, invalid field types, and dangling PTO references are operational errors.
No employee record is synthesized for a missing ID.

## Synthetic employee

| Field | Type | Rule |
|---|---|---|
| `employee_id` | string | Nonblank, unique, exact lookup key |
| `name` | string | Nonblank fictional display name |
| `role` | string | Nonblank |
| `department` | string | Nonblank |
| `work_arrangement` | string | `office`, `hybrid`, or `remote` |
| `work_state` | string | Nonblank fictional work-location state code |

These are mock facts, not an authorization or eligibility decision. Additional fields are
outside the initial output contract.

## Synthetic PTO record

| Field | Type | Rule |
|---|---|---|
| `employee_id` | string | Unique; references an existing synthetic employee |
| `available_hours` | number | Finite and nonnegative; not a projected approval |
| `as_of` | string | ISO 8601 calendar date |

A known employee without a PTO record returns `not_found`, not a zero balance. An unknown
employee also returns `not_found`; the response indicates which record is missing.

## Snapshot and evidence

An evidence item contains `document_id`, `title`, nullable `section`, exact `snippet`,
`chunk_id`, and `generation_id`; ranked search adds numeric `score`. Offsets remain available
internally to order and reconstruct section chunks, but need not be returned. Each response
uses a single validated active index generation. No score is attached to unranked section or
compliance evidence. Candidate search results do not assert semantic support.

## Compliance evaluation

`check_id` is `out_of_state_prior_approval`. `approval_status` is optional and is one of
`approved`, `not_approved`, `unknown`. A result contains that check ID, a
`compliant`/`noncompliant`/`indeterminate` conclusion, limitations, and policy evidence.
An explicit status alone is not enough: the section's reviewed baseline must be present
and fully reconstructable in the active snapshot. Missing/unknown approval or missing,
incomplete, or changed policy evidence yields `indeterminate`; an unavailable or corrupt
index is an operational failure. Verdicts address this rule only.

## Draft and trace

The draft contains a subject and body generated deterministically from synthetic
`recipient_name`, `purpose`, and optional string `supporting_details`. It is returned only;
no external action or persistence occurs.

An operational trace event contains event type (`discovery` or `tool_call`), nullable tool
name, outcome or error category, and allowlisted metadata such as argument names and source
IDs. It excludes argument values, employee records, questions, snippets, drafts, and secrets.
For a failed connection before a tool name is known, the tool name is null. Trace-sink failures
are surfaced to the caller; a failed write cannot itself be assumed to have been recorded.
