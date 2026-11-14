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

**Decision:** Support only `out_of_state_prior_approval`. Resolve `HR-004`, section
`2.2 Working from another state`, from one validated active snapshot. Determine a verdict only
when the complete indexed section can be reconstructed from overlapping or adjacent excerpts
and matches the reviewed baseline section after newline normalization and trimming. Return
`indeterminate` with a limitation if the section is absent, incomplete, or differs from the
reviewed baseline. A corrupt or missing snapshot remains an operational error.

**Rationale:** The rule says written People Operations approval is required before working in
another US state. Section names and embeddings alone do not prove that the current text still
states that rule. A conservative reviewed-baseline guard avoids a definitive verdict after a
policy edit, without external models or a second index. The test corpus can include the same
fictional baseline text. If non-overlapping chunks leave gaps, do not reconstruct missing
characters by guessing.

**Alternatives:** Assuming the rule still applies whenever the section label exists is unsafe;
an LLM judging arbitrary revisions expands scope and requires live-service validation.
Review and update the approved baseline when a policy changes.

## Trace and error boundary

**Decision:** Instrument the server at the MCP tool-request dispatch boundary, outside the
SDK's input validation, so successful and failed calls from any MCP client are traced. Also
instrument the provided client for discovery, unknown-tool, connection, and transport failures.
Use tool-name and outcome/error categories plus allowlisted metadata only. Use stderr or a
separately configured sink, never stdout. For tool failures, return MCP `isError=true`; the
client also distinguishes client-side failure categories. Explicitly configure SDK and
application logging so raw arguments, payloads, and secrets are not emitted. If trace writing
fails, surface that failure without claiming successful tracing.

**Rationale:** SDK input validation can reject a call before its tool body runs, so
server-body-only instrumentation would miss failures. The pinned SDK's low-level tool-request
handler performs this validation; a narrow wrapper at that handler can observe the result.
Test the wrapper against the actual pinned SDK and isolate any dependency on private FastMCP
dispatch internals. Client instrumentation also observes failed connections and discovery.

**Alternatives:** Logging raw JSON with redaction is error-prone. A server-only trace cannot
observe a failed client connection; client-only tracing misses calls from other clients.
