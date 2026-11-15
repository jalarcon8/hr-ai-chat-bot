# Contract: MCP Tools

All six tools are implemented by one FastMCP server and invoked via MCP stdio. Required strings must
be nonblank; integers must not be booleans. Reject unknown arguments, invalid types, unsupported
enums and invalid values as MCP tool errors. Optional `supporting_details`, when supplied, is
a string. The full SDK-generated JSON schemas are available through tool discovery; the input
properties, defaults and descriptions are summarized below.

## Discovery: descriptions and input schemas

Each input is an object with no additional properties. A required nonblank string has at least
one non-whitespace character. The optional compliance facts object also rejects additional
properties; its fields and validation are specified below.

| Tool | Published description | Input properties (required unless marked optional) |
|---|---|---|
| `search_policy_documents` | Find ranked candidate excerpts from the fictional policy index. | `question`: nonblank string; `k`: optional positive integer, default `5` |
| `get_policy_section` | Get indexed excerpts for an exact document and section. | `document_id`, `section`: nonblank strings |
| `lookup_employee_profile` | Look up a fictional employee profile. | `employee_id`: nonblank string |
| `check_pto_balance` | Look up a fictional employee's PTO balance. | `employee_id`: nonblank string |
| `check_policy_compliance` | Evaluate the bounded prior-approval check using caller-supplied facts. | `check_id`: string constant `out_of_state_prior_approval`; `approval_facts`: optional object or null, default null |
| `draft_hr_email` | Draft a fictional HR email without sending or storing it. | `recipient_name`, `purpose`: nonblank strings; `supporting_details`: optional string, default empty string |

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
| `check_policy_compliance` | `check_id: "out_of_state_prior_approval"` | `approval_facts: object` or null, containing the optional fields defined below | `check_id`, `conclusion: "compliant" \| "noncompliant"`, nonempty verified cited `evidence`, nonempty `limitations` | `indeterminate`, `conclusion: "indeterminate"`, `evidence` (possibly empty), nonempty `limitations` explaining why no definitive determination was possible |
| `draft_hr_email` | `recipient_name: string`, `purpose: string` | `supporting_details: string` | `draft: {subject, body}` | Invalid inputs are errors, never empty success |

Search `found` means retrieval returned candidates, not that they answer the question. Preserve
F001 ranking and all returned scores. Section selection uses exact document and section labels
from the active generation; matching snippets are sorted by source offset and retain overlap.
Both preserve source excerpts and generation identity. Section evidence lacks a score.

Compliance receives synthetic facts from the caller, not employee lookup; it does not
authenticate those facts or verify whether another approval exists. The optional
`approval_facts` object has the following optional fields; omitted or null values are unknown:

| Field | Accepted values |
|---|---|
| `status` | `approved`, `not_approved`, `unknown` |
| `authority` | `people_operations`, `other`, `unknown` |
| `format` | `written`, `verbal`, `unknown` |
| `approval_timestamp` | Timestamp of the asserted approval |
| `travel_start_timestamp` | Timestamp when the relevant travel starts |
| `no_other_approvals` | Boolean: `true` asserts no other approval has been granted for this trip; `false` asserts at least one other approval has been granted; null/omitted means unknown |

`approved` means the caller asserts an approval was granted, regardless of its timing, format,
authority, or policy validity; `not_approved` means no approval was granted for the trip;
`unknown` means the assessed approval's grant status is not established. A late approval is
`approved` with its actual grant timestamp, not `not_approved`. Authority, format, and approval
timestamp refer to one assessed candidate approval. With unknown or omitted status, those
details are conditional: if the candidate was granted, it has the supplied attributes; they
do not themselves assert that it was granted. `no_other_approvals` concerns all approvals for
the same trip other than that candidate, as of the caller's assertion. `true` excludes other
approvals even if the candidate was never granted; `false` establishes another approval exists
but supplies no facts about its qualification. With `approved`, `true` asserts the candidate is
the only granted approval for the trip. It does not identify or authenticate any approval.
Selecting the check assumes this rule applies; the tool does not determine applicability
from trip duration, location, exceptions, or other policy conditions.
Timestamps are RFC 3339 strings using `YYYY-MM-DDTHH:MM:SS`, an optional `.` followed
by one to six fractional digits, and `Z` or a numeric `+HH:MM`/`-HH:MM` known offset. Reject invalid dates,
seconds outside `00`-`59`, `-00:00`, missing offsets, leap seconds, excess fractional precision,
invalid enums/types, unknown fields, and a non-object, non-null `approval_facts` as
`INVALID_ARGUMENT`.
A `not_approved` status with a known authority, format, approval timestamp, or
`no_other_approvals: false` is contradictory and also invalid; unknown or absent candidate
details, `no_other_approvals: true` or null/omitted, and a travel timestamp remain allowed.
The `no_other_approvals` value must be a boolean or null. Unknown or omitted status may be
combined with any otherwise valid candidate details and any `no_other_approvals` value; those
candidate details remain conditional. Omitted or null `approval_facts` means all facts are
unknown.

For example, a caller may supply:

```json
{
  "check_id": "out_of_state_prior_approval",
  "approval_facts": {
    "status": "approved",
    "authority": "people_operations",
    "format": "written",
    "approval_timestamp": "2026-01-01T10:00:00Z",
    "travel_start_timestamp": "2026-01-02T10:00:00Z"
  }
}
```

Evaluate the request in this order:

1. Reject malformed or contradictory inputs as `INVALID_ARGUMENT` before evaluating the
   baseline or approval outcome.
2. Verify the reviewed baseline, complete documents, and citations. Insufficient or
   unverifiable evidence yields `indeterminate`; a missing or corrupt index is an operational
   error.
3. If status is `not_approved`, return `noncompliant`.
4. If `no_other_approvals` is `true` and the candidate is known to be verbal, from another
   authority, or at or after travel start, return `noncompliant` even if status or another
   candidate fact is unknown. This conclusion covers both possibilities when status is
   unknown: the candidate was not granted, or it was granted with the disqualifying attribute.
5. If status is `approved`, authority is `people_operations`, format is `written`, and both
   timestamps establish approval strictly before travel, return `compliant`, regardless of
   whether other approvals exist.
6. Otherwise return `indeterminate`, identifying the missing or unknown facts in `limitations`.
   In particular, a disqualified candidate alone does not exclude a separate qualifying
   approval when `no_other_approvals` is false, null, or omitted. An unknown status with
   otherwise qualifying candidate details also remains indeterminate.

Compare timestamps as instants after applying their offsets; equality is not before travel.
`noncompliant` means the approval requirement is unmet under the supplied assertions, not
that every policy condition was evaluated or that other approvals were independently checked.
For an upcoming trip, a `not_approved` result does not assert that travel has occurred or
that approval cannot be granted later.
Neither verdict authenticates caller-supplied approval facts or predicts future approvals for
a hypothetical trip. A missing, invalid, unreviewed, or
mismatched baseline, missing or changed governing documents, or insufficient indexed citations
still yields `indeterminate` regardless of the supplied facts. Never characterize the result as
overall eligibility or authorization. Every result has nonempty `limitations` disclosing that
the approval facts are unauthenticated caller assertions and the check covers only this approval
requirement; an `indeterminate` result also identifies missing facts or evidence.
Both definitive conclusions require nonempty, verified supporting policy evidence with
section-level citations. An `indeterminate` result may have empty `evidence` when verified
supporting policy evidence is unavailable; when verified policy evidence is used to explain
the result, include its corresponding citations. Do not present unverified excerpts as
supporting evidence or fabricate citations. Verification of an individual cited excerpt
requires the applicable governing document's pinned approval metadata, complete-document
integrity and snapshot binding, and the indexed snippet's source match; verification of one
document does not establish that the entire governing set is verified. Validation and
operational errors are error responses and do not require policy citations.
The reviewed-baseline and completeness checks are specified in
[research.md](../research.md) and [data-model.md](../data-model.md): before a definitive
result, verify the approved baseline and complete governing documents HR-004 and HR-001 against
the active pin, and bind their complete source bytes to the same F001 snapshot using each
document's raw `content_hash`. Separately validate each document's approval metadata and its
binding to the pinned baseline ID, version, document ID, normalization version and digest.
Missing, inconsistent, unapproved or locally unverifiable approval metadata yields
`indeterminate`. The offline checks do not independently authenticate the approver or verify
the review reference; an authorized maintainer must verify the independent review before pin
activation. The canonical document hash strictly decodes UTF-8, converts
CRLF and CR to LF, applies Unicode NFC, and preserves all other characters before UTF-8
encoding and hashing. Missing, changed or unverifiable governing documents, or unavailable
indexed citations, yield `indeterminate` with limitations. Preserve indexed section-level
citations and exact supporting snippets; source files are not a substitute for indexed evidence.
For each required citation, strictly decode its snapshot-bound raw source as UTF-8 exactly as
F001 does, without newline conversion or Unicode normalization. Its `start` and `end` are
zero-based, half-open Python string character offsets into the complete decoded text, including
metadata. Require integer, non-boolean `0 <= start < end <= len(text)` and exact equality
between `text[start:end]` and the indexed snippet. Never apply character offsets to raw UTF-8
bytes or to the LF/NFC-normalized text used for canonical baseline hashing. Invalid required
citation offsets, mismatched snippets, or an unreconstructable text representation yield
`indeterminate` with an explanatory limitation when the active snapshot passes F001 pointer,
checksum and structural validation. A missing snapshot or one that fails those checks remains
an operational error; the section adapter must preserve this distinction for compliance.
Changed governing policy requires a new version and explicit review before activation; unrelated
document changes alone do not invalidate this check. A missing or corrupt index remains an
operational error. There is no email sending, storage, or other external action.

The previously planned top-level `approval_status` argument is no longer accepted; it is an
unknown argument. A nested `status: "approved"` alone is insufficient and returns
`indeterminate` when the required baseline and citations are valid. This is a contract change
for any callers built against the earlier draft.

## Failures and tracing

For a valid MCP `tools/call` request with an arguments object targeting one of the six tools,
every error returned by the server's validation or execution boundary is an MCP tool result
with `isError=true`, sanitized text content, and this machine-readable `structuredContent`:

```json
{
  "error": {
    "classification": "INVALID_ARGUMENT",
    "origin": "input_validation",
    "code": "invalid_argument"
  }
}
```

`classification`, `origin`, and `code` are required strings. The allowed combinations are:

| Classification | Origin | Code | Meaning |
|---|---|---|---|
| `INVALID_ARGUMENT` | `input_validation` | `invalid_argument` | Advertised schema or strict tool-input validation rejects the arguments before the handler runs. |
| `OPERATIONAL_ERROR` | `tool_execution` | `index_unavailable`, `embedding_failure`, or `data_unavailable` | A recognized dependency failure occurs during execution. |
| `OPERATIONAL_ERROR` | `trace_persistence` | `trace_persistence_failure` | A required trace cannot be persisted, whether or not the handler ran. |
| `UNKNOWN_ERROR` | `tool_execution` or `request_adapter` | `internal_error` | An unexpected handler or adapter failure was caught at that known origin but has no recognized operational cause. |

The adapter assigns these fields only from validation it performs or typed failures it catches
at a known boundary. The SDK transports the server's `structuredContent`; it does not assign
these application classifications. Use the fields and known typed error origins, never
error-message text or missing execution traces, for classification.
The provided client and raw MCP clients read `structuredContent.error`; sanitized text is
for humans and is not a classification source. Preserve the existing successful envelopes:
valid `not_found` or `indeterminate` outcomes are not errors.

The planned server tracing boundary is the tool-request dispatch adapter, after the SDK accepts
the MCP request envelope and before application argument validation or handler execution.
It validates each known tool's arguments against its advertised schema and strict input model
before invoking the handler; it converts known dependency exceptions, unexpected exceptions,
and trace persistence failures to the structured errors above. It must not infer application
error types from SDK error strings. The adapter replaces or bypasses SDK tool-input validation
that would otherwise consume errors before classification, while retaining FastMCP discovery
and the same six schemas. It dispatches the underlying server-side handlers without using
FastMCP's error-wrapping tool execution path. Its internal call to a handler occurs only after
the request has arrived through MCP; it is not a client-side protocol bypass. The handler may
already have run if trace persistence fails.

When the provided client receives an error without a valid, recognized classification/origin/code
combination and has no independently established local failure, it assigns this **client-side**
representation:

```json
{
  "classification": "UNCLASSIFIED_ERROR",
  "origin": null,
  "code": "unclassified_error"
}
```

`UNCLASSIFIED_ERROR` is an error, never a success or `not_found`. It does not assert that the
failure occurred before dispatch, during SDK validation, or during tool execution. An observed
machine-readable JSON-RPC error code may be retained separately as protocol metadata; it is not
by itself an application error category or proof of origin. Neither the message text nor the
presence or absence of an execution trace may be used to infer category or origin. In
particular, a missing trace does not by itself establish a trace-persistence failure.

The client preserves a recognized server envelope or independently established local failure
instead of replacing it with `UNCLASSIFIED_ERROR`. For example, unknown-tool, discovery,
connectivity, and transport failures remain distinct client-side errors (`unknown_tool`,
`discovery_failure`, or `transport_failure`) when independently established. A raw client
receives the native MCP/JSON-RPC error or unclassified SDK tool error; the SDK does not emit
the client-side `UNCLASSIFIED_ERROR` representation, and the structured tool-error envelope
cannot be guaranteed when a request never reaches the adapter. Raw clients applying their own
interpretation must follow the same evidence rule. Do not log arbitrary SDK exception strings,
request bodies, or response bodies.

When the configured sink is operational, the server persists an allowlisted trace for every
tool invocation reaching that boundary from any client, including invalid tool arguments
rejected before the handler, execution failures, and successful calls. A malformed protocol
request is exempt from this server tool execution trace guarantee only if the SDK rejects it
before tool dispatch, preventing it from reaching the boundary. Such a failure is a protocol
failure, not a tool execution failure; a raw client may receive a native protocol error or a
transport failure rather than a tool result. The provided client persists separate traces for
discovery and client-side failures, including failed connections and protocol failures it
observes, when its sink is operational. If a required server trace cannot be persisted, return
a sanitized MCP tool error (`isError=true`) with `OPERATIONAL_ERROR`, `trace_persistence`, and
`trace_persistence_failure`, never the successful tool result. If persistence of a required
client-side trace fails, surface a machine-readable client-side `OPERATIONAL_ERROR` in the
same origin and code. A persistence failure is exempt from the persisted-trace
guarantee; do not assume the failed write was recorded. A tool handler may already have run
before its trace write fails. See [data-model.md](../data-model.md); do not log arbitrary SDK
exception strings or request and response bodies.

## Acceptance examples

- Search with a deterministic embedder and unrelated query: nonempty results are `found`,
  `evidence_kind` is `candidate`, and scores do not imply support.
- Request a known document/section and a missing section; verify ordered exact excerpts and
  `not_found`, respectively.
- Look up a known employee, an unknown employee, and a known employee with no PTO record;
  verify matched records and distinct missing categories.
- Check timely written People Operations approval; known absence, late/equal timestamps,
  verbal approval and another authority; omitted and unknown necessary facts; and timestamp
  offset equivalence against reviewed governing documents. Verify caller facts are not
  represented as authenticated and conclusions address only this approval requirement.
  Changes anywhere in HR-004 or HR-001, including an
  added `2.2.1 Exception`, and missing or unverifiable documents or baselines are
  `indeterminate`, while a corrupt index produces an MCP error. A change to an unrelated
  document alone does not invalidate the check. Verify newline and Unicode normalization,
  preservation of other whitespace, source-to-snapshot binding, and indexed citations. With
  accented characters, emoji and other multibyte characters preceding a citation, verify
  F001 character-offset slicing of the exact decoded source and fail closed for invalid required
  offsets or an unreconstructable representation.
- A draft is deterministic and causes no email, network, or record mutation. Invalid types,
  blank strings, zero/boolean `k`, unsupported checks, and unknown arguments fail as errors.
- Disconnect the server and request an unknown tool through the client; verify distinguishable
  failures and redacted trace events.
- With an operational sink, inspect persisted traces for successful and failed calls. Simulate
  server trace persistence failure after a successful handler and after a failed call; both
  return `isError=true` with `OPERATIONAL_ERROR` and `trace_persistence_failure`, not a
  successful result. Simulate client-side trace persistence failure and verify the explicit
  client-side operational error.
- Using both the standard MCP client and a raw MCP client, verify structured classifications
  for invalid arguments, known dependency failures, and unexpected handler exceptions. Verify
  an ambiguous SDK error becomes client-side `UNCLASSIFIED_ERROR` with a null origin, regardless
  of message wording or whether an execution trace is available.
- Send a malformed `tools/call` envelope that the SDK rejects before dispatch; verify it is a
  protocol failure, the adapter and tool handler are not called, and no server execution trace
  is required. Invalid tool arguments inside an SDK-accepted envelope reach the adapter and
  must be traced when the sink is operational.
