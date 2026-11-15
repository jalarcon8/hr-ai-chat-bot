# Data Model: MCP Tool Integration

All records are fictional. Employee and PTO JSON files are the initial read-only source of
truth; malformed data files, duplicate IDs, invalid field types, and dangling PTO references
are operational errors. No employee record is synthesized for a missing ID. Compliance
baseline failures are handled separately as described below.

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
internally to order and validate section chunks, but need not be returned. F001 `start` and
`end` are zero-based, half-open Python string character offsets into the complete source
strictly decoded from UTF-8, including metadata; they are not byte or grapheme offsets. F001
does not convert newlines or normalize Unicode in this text. For compliance citation
verification, strictly decode the snapshot-bound raw bytes in the same way, require integer,
non-boolean `0 <= start < end <= len(text)`, and compare `text[start:end]` exactly with the
indexed snippet. Invalid required citation offsets, mismatched snippets, or an unreconstructable
text representation yield `indeterminate` with a limitation. Do not apply these offsets to raw
bytes or the separately LF/NFC-normalized text encoded as UTF-8 for baseline hashing.
Each response
uses a single validated active index generation. No score is attached to unranked section or
compliance evidence. Candidate search results do not assert semantic support.

## Compliance evaluation

`check_id` is `out_of_state_prior_approval`. The optional `approval_facts` object describes
the caller's synthetic assertions for one trip and one candidate approval. Selecting
the check assumes this rule applies; the tool does not determine applicability based on trip
duration, location, exceptions, or other policy conditions. Omitted or null fields are unknown.
Unknown fields do not authenticate the remaining assertions.

| Field | Type and meaning |
|---|---|
| `status` | `approved`, `not_approved`, or `unknown`: the candidate was granted, no approval was granted for the trip, or the candidate's grant status is not established |
| `authority` | `people_operations`, `other`, or `unknown`: issuer of the asserted approval |
| `format` | `written`, `verbal`, or `unknown`: format of the asserted approval |
| `approval_timestamp` | RFC 3339 timestamp with known offset, or null/omitted if unknown |
| `travel_start_timestamp` | RFC 3339 timestamp with known offset, or null/omitted if unknown |
| `no_other_approvals` | Boolean or null/omitted: `true` asserts no other approval was granted for the trip; `false` asserts at least one other was granted; null/omitted is unknown |

Status describes approval existence independently of timing, format, authority, or policy
validity. An approval granted after travel began is `approved` with its actual grant timestamp.
When status is unknown or omitted, candidate authority, format, and approval timestamp are
conditional attributes if that candidate was granted; they do not establish its grant. The
`no_other_approvals` assertion applies as of the caller's assertion and excludes or establishes
other approvals regardless of whether the candidate was granted. It does not establish their
policy validity or independently authenticate them.

Timestamp strings use `YYYY-MM-DDTHH:MM:SS`, optionally followed by `.` and one to six
fractional digits, and `Z` or a numeric `+HH:MM`/`-HH:MM` offset. Require a valid calendar date, seconds
from `00` through `59`, and a known valid offset; reject `-00:00`, missing offsets, leap
seconds, invalid strings, and excess fractional precision as `INVALID_ARGUMENT`. Compare
timestamps as instants, not lexicographically. Unknown enum values, non-object, non-null facts,
unknown fields, and invalid types are also invalid arguments. A `not_approved` status with
a known authority, format, approval timestamp, or `no_other_approvals: false` is contradictory
and invalid; omitted, null, or `unknown` authority/format, an omitted or null approval timestamp,
and `no_other_approvals: true` or null/omitted are allowed. The boolean field rejects all other
types. Omitted or null `approval_facts` means all facts are unknown. Unknown or omitted status
allows any otherwise valid candidate details and any `no_other_approvals` value.

A result contains that check ID, a `compliant`/`noncompliant`/`indeterminate` conclusion,
limitations, and policy evidence. Reject invalid or contradictory facts first. With the
baseline and citations verified, `not_approved` is `noncompliant`. A known `other` authority,
`verbal` format, or approval timestamp at or after travel start is also `noncompliant` when
`no_other_approvals` is `true`, even if the candidate's status is unknown. Otherwise, such a
candidate does not exclude a separate qualifying approval. A qualifying candidate yields
`compliant` only when status is `approved`, authority is `people_operations`, format is
`written`, and both timestamps show approval strictly before travel. All other combinations
are `indeterminate`, including unknown status with otherwise qualifying attributes and a
disqualified candidate when other approvals are possible. These conclusions assess the
supplied trip facts; they do not independently verify whether another approval exists or
authenticate any fact. For an upcoming trip, `not_approved` means the requirement is unmet
under the supplied facts; it does not assert travel has occurred or predict whether approval
will be obtained later. Every result's nonempty `limitations` must disclose that the approval
facts are unauthenticated caller assertions and the check is limited to this requirement.
Unsupported checks and malformed inputs are errors.

Baseline approval metadata and complete governing
documents must pass their separate checks against the active pin and the same F001 snapshot.
Section-level snippets are citations, not document-integrity evidence. Missing, inconsistent,
unapproved or locally unverifiable baseline approval metadata,
an invalid baseline, a missing, changed or unverifiable governing document, or missing,
incomplete or conflicting citation evidence yields `indeterminate` with a limitation; an
unavailable or corrupt index is an operational failure. Verdicts address this rule only.

### Versioned compliance baseline

The proposed artifact is `data/compliance-baselines/out-of-state-prior-approval-v2.json`.
It is a UTF-8 JSON object containing `records`, exactly one object per governing document:
initially `HR-004` and `HR-001`. Every record contains these required fields, all of which are
also pinned in separately version-controlled active implementation configuration:

| Field | Validation |
|---|---|
| `baseline_id` | Exact `out-of-state-prior-approval` |
| `baseline_version` | Exact string `2` initially |
| `check_id` | Exact `out_of_state_prior_approval` |
| `document_id` | Exact governing ID, unique within the set |
| `canonical_sha256` | Lowercase 64-character hexadecimal SHA-256 of the complete canonical document |
| `normalization_version` | Exact `utf8-lf-nfc-v1` |
| `approval_status` | Exact `approved` for activation |
| `approver_id` | Nonblank repository reviewer identifier |
| `approved_at` | Valid UTC RFC 3339 timestamp in `YYYY-MM-DDTHH:MM:SSZ` form |
| `approval_reference` | HTTPS GitHub pull-request review permalink with a `pullrequestreview-<id>` fragment |

Each approval is attached to its record's exact baseline ID, version, check ID, document ID,
normalization version and digest. The artifact and pin must have the same complete governing
set and exactly matching required fields, with no duplicate document IDs; all records must use
the same baseline ID, version, check ID and normalization version. The pin contains the entire
record for each document, not only its digest. Validate field types, formats, and the `approved`
status separately from document-content verification.

[research.md](research.md) defines candidate digests, source-to-snapshot binding and the
approval verification policy. The old section-only v1 artifact is not a document-level
approval. Version 2 remains pending explicit review of both complete documents; do not invent
approval values. No runtime check verifies the referenced GitHub review or authenticates the
reviewer. An authorized maintainer must verify the independent review record before activating
the pin; matching local records alone do not prove authorization.

## Tool errors

For supported tool-call envelopes, an MCP error has `isError=true` and a `structuredContent`
object containing `error.classification`, `error.origin`, and `error.code`. The contract
defines the permitted combinations. For an error without reliable classification metadata,
the provided client assigns `UNCLASSIFIED_ERROR`, `origin: null`, and code
`unclassified_error`; this local representation is not an SDK-emitted field and does not
assert where the failure occurred. Native MCP/JSON-RPC errors and unclassified SDK tool errors
are preserved by raw clients. Neither message text nor missing execution traces establish
category or origin. Independently established client failures retain their known categories.

## Draft and trace

The draft contains a subject and body generated deterministically from synthetic
`recipient_name`, `purpose`, and optional string `supporting_details`. It is returned only;
no external action or persistence occurs.

An operational trace event contains event type (`discovery` or `tool_call`), nullable tool
name, outcome or error category, and allowlisted metadata such as argument names and source
IDs. It excludes argument values, employee records, questions, snippets, drafts, and secrets.
For a failed connection before a tool name is known, the tool name is null. Trace-sink failures
are surfaced as explicit `trace_persistence_failure` operational errors. Required tool traces
must be persisted before returning success; a failed write cannot itself be assumed to have
been recorded, and its failure must not be reported as tool success. Server execution traces
cover tool invocations reaching the dispatch adapter after SDK envelope acceptance; malformed
protocol requests the SDK rejects before dispatch cannot reach this boundary and do not require
a server execution trace. The provided client separately traces protocol failures it observes.
