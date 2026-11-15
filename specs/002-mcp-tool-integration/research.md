# Research: MCP Tool Integration

## SDK and Python compatibility

**Decision:** Plan to pin the official `mcp==1.28.1` Python SDK and use its
`mcp.server.fastmcp.FastMCP` server and `ClientSession`/`stdio_client`. Add the dependency to
the project manifest and keep the existing requirements installation path consistent.

**Rationale:** The feature and roadmap explicitly require FastMCP. The official v1 SDK
provides that class; package metadata declares Python >=3.10, compatible with the project's
Python 3.11 constraint. Its v1 documentation describes stdio, discovery, structured output,
and `isError` tool responses. The v2 migration guide says FastMCP was renamed and its import
removed; an exact pin prevents an accidental incompatible major upgrade. Validate dependency
resolution and stdio behavior on both Windows and Linux during implementation; metadata alone
is not an installation or security verification.

**Alternatives:** Official SDK v2 requires a change to the specified FastMCP interface; the
separate third-party FastMCP package adds an unnecessary alternative SDK. Reconsider the pin
if a security advisory or dependency conflict requires it.

**Sources:** [SDK v1 documentation](https://py.sdk.modelcontextprotocol.io/v1/),
[v1 client](https://py.sdk.modelcontextprotocol.io/v1/client/),
[v1 server and errors](https://py.sdk.modelcontextprotocol.io/v1/server/),
[v2 migration](https://py.sdk.modelcontextprotocol.io/migration/),
[mcp 1.28.1 metadata](https://pypi.org/pypi/mcp/1.28.1/json).

## Existing retrieval and exact section access

**Decision:** Call F001's public `retrieve` for ranked search. For exact section lookup, use
a small F002 adapter around the existing F001 `_active_metadata` snapshot validator and its
validated `documents`/`chunks` metadata. Read one active generation per operation, validate
the required record fields, match document ID and the complete section label, and return
unscored chunks sorted by source offset. Do not query top-k as a substitute for exact lookup
or read the live corpus in place of the indexed snapshot.

**Rationale:** F001 stores chunk IDs, section labels, offsets, snippets and a generation ID in
the active snapshot; its public API currently has no exact section operation. `_active_metadata`
is private, so isolate and test this dependency rather than duplicating snapshot integrity
logic or changing F001. A future public F001 interface can replace the adapter if approved.
The validator verifies pointer and file checksums and basic metadata, but the adapter must
validate consumed chunk fields itself. Exact case-sensitive matching avoids ambiguous partial
section matches; headingless documents have no section to select.

**Alternatives:** Calling `retrieve` with a section name may omit matching chunks due to
ranking. Re-parsing source files could return content from a different generation. Reimplementing
snapshot validation risks drift; creating a second index violates scope.

## Candidate search versus support

**Decision:** Return all successful F001 top-k results as candidate evidence, with original
scores and metadata. Nonempty results mean `found` only in the sense of retrieved candidates;
only an empty successful retrieval means `not_found`. Do not infer semantic support.

**Rationale:** F001 similarity ranking is not a relevance or grounding guarantee. The user
explicitly confirmed this interpretation during planning. F003 owns answer-level assessment.

**Alternatives:** A score threshold or arbitrary lexical filter would silently discard results
without demonstrating semantic relevance. Adding a separate model-based relevance service
would change scope and introduce a new dependency.

## Bounded compliance and policy changes

**Decision:** Support only `out_of_state_prior_approval`. The minimum integrity unit is each
complete governing policy document, not its indexed chunks. The reviewed set for this check
must include `HR-004` Remote Work Policy and `HR-001` Employee Handbook: HR-001 sections 1.3,
5.1, 5.4 and 14.1 address policy precedence or this approval. SEC-001, IT-001, IT-002 and
FIN-001 concern security, equipment, support or expenses; their current texts do not establish
this specific prior-approval rule, so they are not in the initial governing set. This is not
an assessment of overall remote-work eligibility, legal exceptions, or agreements outside the
corpus. When a newly identified policy governs this rule, explicitly review it, add its complete
document to a new baseline version, and update the pin before making definitive decisions.
Do not infer that unrelated files are governing solely from cross-references.

The proposed version-controlled artifact is
`data/compliance-baselines/out-of-state-prior-approval-v2.json`, with the complete governing
document IDs and their individual canonical SHA-256 digests, version, check ID, normalization
version and per-document approval metadata, as defined in [data-model.md](data-model.md).
The separately version-controlled pin contains each complete record, including approval fields.
Current candidate digests are:

| Document | Canonical SHA-256 |
|---|---|
| HR-004 | `cefc968e27181bada8117c7fc8007f1beae495d6ac1744214f399780e54679b2` |
| HR-001 | `06e5b754e0b2d7ff733c824c8e51f72a38569bb056d3aa3cec66189853109c7c` |

These are candidate hashes, not evidence that the full documents were reviewed or approved.
The prior approval covered only the HR-004 section text; the existing section-only v1 artifact
must not be treated as an approved document-level baseline. Until explicit review of both
complete documents and activation of v2, the production check returns `indeterminate`.

Canonicalize each complete source file, including its metadata, headings, all whitespace and
final newline: strictly decode UTF-8, convert CRLF and lone CR to LF, normalize Unicode to NFC,
encode as UTF-8, then compute SHA-256. Preserve all other characters; never trim or collapse
content. A canonical digest identifies the reviewed document version, while F001's existing
`content_hash` is a separate SHA-256 over the original raw file bytes. The named normalization
version is `utf8-lf-nfc-v1`; reject an unknown version rather than choosing a default.

For each check, read one checksum-validated F001 active metadata snapshot. Require exactly one
valid document record for each governing ID. Resolve each record's relative `source_path`
under the configured corpus root, rejecting absolute paths, traversal and resolved paths outside
that root. Read each complete source once, compare its raw SHA-256 with that same record's
`content_hash`, then compare its canonical SHA-256 with the corresponding separately
version-controlled active pin. The raw comparison binds those bytes to the indexed generation;
reading the source is an integrity check, never a fallback for missing indexed evidence. If the
file changed after indexing, even only in line endings, the raw comparison fails until
reindexing. A new snapshot containing canonically equivalent line endings or Unicode can match
the same pinned canonical digest.

Separately validate approval: require exactly one complete, correctly typed record per governing
document; check the shared baseline ID, version, check ID and normalization version; validate
each document ID, SHA-256, `approved` status, nonblank approver, UTC timestamp and GitHub review
permalink; and compare every required field with that document's pinned record. The approval
fields thereby refer to the same record's exact document digest and baseline version. Missing,
malformed, inconsistent, unapproved or locally unverifiable approval metadata fails closed.
Matching content hashes alone never establish approval.

The runtime's offline verification policy checks only record completeness, format, internal
binding and equality to the version-controlled pin. It does **not** query GitHub, verify that a
review permalink exists, authenticate the reviewer or independently verify authorization. Before
activating a pin, an authorized maintainer must independently inspect the referenced repository
review, verify the reviewer and timestamp and confirm that it explicitly approves the exact
baseline version and complete-document digests. If that independent review cannot be verified,
do not activate the pin. No such full-document review record has yet been identified. The runtime
trusts the activated reviewed configuration; a plausible but false reference cannot be detected
by offline checks alone.

For citations, obtain the existing HR-004 section 2.2 snippets from that same indexed generation.
F001 strictly decodes the original UTF-8 bytes into a Python string without newline conversion or
Unicode normalization; offsets refer to that entire decoded string, including metadata. Reconstruct
the identical string by strictly decoding the same raw bytes after their snapshot hash is verified.
Each `start` and `end` is a zero-based, half-open Python string character range, not a byte or
grapheme range. Require integer, non-boolean offsets satisfying `0 <= start < end <= len(text)`,
and require `text[start:end]` to equal the indexed snippet exactly. Retain the document, section,
chunk and generation metadata. Never apply character offsets to UTF-8 bytes or to the separate
LF/NFC-normalized representation encoded for the canonical baseline hash.
Invalid required citation offsets, a snippet mismatch, or inability to reconstruct this text
reliably yields `indeterminate` with a limitation when the active snapshot passes F001's
pointer, checksum and structural validation. An active snapshot that fails those checks remains
an operational error. The shared section adapter must preserve this distinction for compliance
instead of turning an individual invalid citation offset into a snapshot error. Do not
reconstruct a full document from chunks. A missing,
unreadable, invalid, unreviewed or mismatched baseline; a missing, modified,
unreadable, undecodable or otherwise unverifiable governing document; a stale source/index
binding; or missing, incomplete or conflicting required citation evidence yields `indeterminate`
with a limitation. An absent governing document record in an otherwise valid snapshot also yields
`indeterminate`. A missing or corrupt index snapshot remains an operational error.

For a governing policy change, create a new baseline version without overwriting the old one,
explicitly review every changed governing document and the governing set, and update every
per-document record and full-record pin in the same reviewed source-control change before
activation. Unchanged governing documents may retain their prior digests, but each new-version
record still requires approval explicitly bound to that new version and digest. A digest or an
`approved` string alone is not proof of human review; this design relies on the documented
maintainer review and trusted source-control process, not a cryptographic signature. Until
activation, changed documents are `indeterminate`; changes to documents outside the reviewed
governing set do not alone invalidate this check.

**Rationale:** The rule says written People Operations approval is required before travel for
work in another US state. The caller supplies the approval's status, authority, format and
timestamp, plus the travel start timestamp; the result evaluates those synthetic assertions
without independently authenticating them or establishing that no other approval exists.
Section names and embeddings alone do not prove that the current text still
states that rule. A conservative reviewed-baseline guard avoids a definitive verdict after a
policy edit anywhere in either governing document, without external models or a second index.
The fixed, explicitly reviewed set avoids a policy-dependency service.

**Alternatives:** Assuming the rule still applies whenever the section label exists is unsafe;
an LLM judging arbitrary revisions expands scope and requires live-service validation.
Review and activate a new baseline version when a governing policy changes.

## Trace and error boundary

**Observation:** On Windows with Python 3.11, `mcp==1.28.1` was installed in an isolated
session environment for a focused probe; it was not installed in the project environment.
FastMCP registers its low-level tool handler with `validate_input=False`, then performs
Pydantic argument validation before invoking the registered tool callable. A malformed
argument did not invoke the callable, but both that validation failure and an unexpected
handler exception returned `isError=true` with text only and no `structuredContent` error
category. The low-level server's optional JSON Schema validation also runs before its handler
and returns text-only errors. A custom low-level handler returning `CallToolResult` with
`isError=true` and structured error data was observed unchanged by `ClientSession` and in a
raw JSON-RPC response.

An in-memory raw JSON-RPC probe of the same SDK showed that a `tools/call` request with
non-object `arguments` or a missing tool name returns JSON-RPC `-32602` before the registered
request handler is invoked. A request with an arguments object containing an invalid field
reaches the handler but does not invoke the tool callable; omitting `arguments` also reaches the
handler. A malformed JSON input was rejected without a tool-call response being captured. The
SDK validates request envelopes in its session receive loop, before the planned adapter; its
stdio transport parses JSON before that loop. These probes are SDK evidence, not evidence that
F002's adapter or tracing has been implemented.

**Decision:** Use one adapter at the MCP tool-request dispatch boundary, after SDK envelope
acceptance, for pre-handler argument validation, machine-readable error classification, and
tracing. Persist traces for invocations that reach the adapter when the sink is operational;
the server cannot promise execution traces for malformed protocol requests the SDK rejects
before dispatch. The provided client separately traces protocol failures it observes.
Preserve FastMCP
discovery and the six advertised schemas, bypass SDK tool-input validation that would consume
the error type, and validate against the advertised schema and strict input model before
calling the handler. Return structured tool errors for supported calls as defined in the
contract; do not infer categories or origins from SDK text or missing execution traces. The
provided client assigns `UNCLASSIFIED_ERROR` with no asserted origin when reliable error
classification metadata is unavailable; this is client interpretation, not an SDK-emitted
category. Protocol errors that do not reach the adapter remain native SDK/MCP errors and cannot
be guaranteed to carry the structured envelope. Also
instrument the provided client for discovery, unknown-tool, connection, and transport failures.
Use tool-name and outcome/error categories plus allowlisted metadata only. Use a configured
persistent sink, never stdout; stderr is suitable only when captured by a persistent destination.
For tool failures, return MCP `isError=true`; the
client also distinguishes client-side failure categories. Explicitly configure SDK and
application logging so raw arguments, payloads, and secrets are not emitted. If trace writing
fails, surface an explicit operational error without claiming successful tracing or returning
tool success. No secondary sink or retry infrastructure is required.

**Rationale:** SDK input validation can reject a call before its tool body runs, and its
text-only tool errors do not reliably distinguish validation from execution. A narrow adapter
can validate and classify before that information is lost. Test the adapter against the pinned
SDK over stdio with both standard and raw clients, and isolate any dependency on private FastMCP
dispatch internals. Client instrumentation also observes failed connections and discovery.

**Alternatives:** Logging raw JSON with redaction is error-prone. A server-only trace cannot
observe a failed client connection; client-only tracing misses calls from other clients.
