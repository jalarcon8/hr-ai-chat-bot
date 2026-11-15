# Implementation Plan: MCP Tool Integration

**Feature**: `002-mcp-tool-integration` | **Date**: 2026-11-14 |
**Spec**: [spec.md](spec.md)

**Branch**: `002-mcp-tool-integration`; initial planning occurred on `main`.

## Summary

Expose the six agreed read-only or mock tools through an MCP FastMCP server and a real stdio
client. Wrap Feature 001's search and validated active snapshot; provide fictional JSON
employee and PTO data, one narrowly scoped evidence-guarded compliance check, deterministic
email drafting, explicit outcomes/errors, and allowlisted traces. Full orchestration, real HR
integration, email delivery, UI, and deployment remain out of scope.

## Technical Context

**Language/Version**: Python 3.11 (`>=3.11,<3.12`).

**Primary Dependencies**: Existing F001 dependencies and official `mcp==1.28.1` with
`FastMCP`, `ClientSession`, and stdio transport. Pin is proposed; dependency resolution,
platform compatibility, and security must be verified during implementation. SDK v2 has a
breaking FastMCP rename; see [research.md](research.md).

**Storage**: Existing F001 active FAISS snapshot; small version-controlled synthetic employee,
PTO, and reviewed compliance-baseline JSON files. No database or second index. Trace events
use a configurable local sink.

**Testing**: pytest and Ruff; deterministic embedder and synthetic fixtures; real MCP stdio
subprocess tests including discovery, all six calls, bad schemas, failures, and traces.
The documented SC-009 local/test configuration requires no paid service, subscription,
infrastructure, API credential, live model, or hosted runtime service. It uses locally installed
packages, a deterministic F001 embedder and isolated index, synthetic data and a test-approved
baseline; unauthenticated free public package sources may be used for installation.

**Target Platform**: Windows Python 3.11 and Linux Python 3.11; compatible with a future
single-service deployment. F001 Linux clean-install/live-model validation remains open.

**Project Type**: Python package with MCP server and developer-facing client.

**Performance Goals**: No F002-specific latency or concurrency SLA has been approved. Keep
corpus/data small; F006 owns measured p50/p95 latency and host-resource validation. Do not
claim free-tier viability without measurement.

**Constraints**: Exactly six tools; stdio MCP; no real HR data, external email, or state
mutation; no separate deployed service; secrets and unnecessary input excluded from logs.
F001's current code is not modified in this planning increment.

**Scale/Scope**: Small fictional fixture set and current F001 policy corpus. One supported
remote-work approval check, not an entire remote-work or PTO workflow.

## Constitution Check

| Principle | Before research | After design |
|---|---|---|
| I. Simplicity | Pass: one SDK, existing index, JSON fixtures. | Pass; no second index or service. |
| II. Python-first | Pass: Python 3.11 and pinned SDK proposed. | Pass, subject to actual installation tests. |
| III. Separation | Pass: client, server, evidence, data, and mock actions separated. | Pass; snapshot adapter isolates F001's private API. |
| IV. Grounded responses | Pass: citations and explicit missing evidence required. | Pass conditionally: baseline guard fails closed on changed/incomplete policy; test this explicitly. |
| V. MCP | Pass: six tools and real stdio protocol planned. | Pass conditionally: integration tests must prove discovery and calls; F003 agent invocation remains future work. |
| VI. Synthetic/safe | Pass: no real data or external actions. | Pass: only fictional read-only records and returned drafts. |
| VII. Tests/reproducibility | Pass: deterministic tests and docs planned. | Pass conditionally: execute Windows/Linux tests and CI; deployment gating is F006. |

No constitution exception is proposed. Conditional gates are design commitments, not evidence
that implementation or platform validation has passed.

## Project Structure

### Feature artifacts

```text
specs/002-mcp-tool-integration/
  spec.md
  plan.md
  research.md
  data-model.md
  contracts/mcp-tools.md
  quickstart.md
  tasks.md                 # Generated implementation and verification tasks
```

### Proposed implementation layout

```text
src/hr_rag/                # Existing F001; no retrieval replacement
src/hr_mcp/
  __init__.py
  server.py                # FastMCP registrations and stdio entry point
  client.py                # stdio lifecycle, discovery, calls, examples and client traces
  policy.py                # F001 search and active-snapshot section adapter
  data.py                  # validated read-only synthetic JSON records
  tools.py                 # bounded compliance and deterministic drafting
  models.py                # tool inputs, outputs, errors, safe trace events
  trace.py                 # allowlisted trace events and persistent sink
data/
  employees.json
  pto.json
  compliance-baselines/     # Versioned baseline records and document digests
tests/
  test_mcp_discovery.py
  test_mcp_policy.py
  test_mcp_data.py
  test_mcp_compliance.py
  test_mcp_draft.py
  test_mcp_stdio.py
  test_mcp_errors.py
  test_mcp_trace.py
  fixtures/mcp/            # isolated fictional records and deterministic doubles
```

These are planned paths, not existing implementations. Keep modules cohesive and reconcile
any necessary layout changes with the task inventory. Add the SDK to `pyproject.toml` and keep
`requirements.txt` and setup documentation coherent; preserve existing Python 3.11 support.

## Phase 0: Research Decisions

See [research.md](research.md). Decisions cover the official v1 SDK, Python compatibility,
candidate evidence, exact snapshot access without F001 edits, conservative compliance under
policy changes, and client-side tracing of protocol and transport failures.

## Phase 1: Design

### Interfaces and data

- Implement the six input/output contracts in [contracts/mcp-tools.md](contracts/mcp-tools.md)
  and records in [data-model.md](data-model.md).
- Search calls F001 `retrieve` and labels nonempty ranked results as **candidate** evidence;
  no score is treated as semantic support. Section lookup uses the existing checksum-verified
  active metadata via one isolated adapter; it matches full document and section IDs, validates
  fields, and retains exact snippets and a single generation ID.
- For the initial compliance check, use caller-supplied structured approval status, authority,
  format, approval timestamp, travel start timestamp and `no_other_approvals`; never authenticate
  those assertions.
  Evaluate written People Operations approval strictly before travel as defined in the
  contract, allowing a disqualified candidate to determine an unmet requirement only when the
  caller also asserts no other approval was granted.
  Require the approved
  document-level baseline for complete HR-004 and HR-001 in [data-model.md](data-model.md).
  Bind each complete source to the same F001 snapshot via its raw content hash, then compare
  its UTF-8/LF/NFC canonical digest to the versioned pin. Separately validate each pinned
  document approval record and use the maintainer-reviewed activation policy in
  [research.md](research.md); offline metadata checks do not authenticate the reviewer.
  Preserve indexed HR-004 section
  2.2 snippets for citations rather than using source files as evidence fallback. Missing,
  invalid, unreviewed or mismatched baseline; missing, changed or unverifiable governing
  documents; and absent or insufficient citations produce `indeterminate`; a corrupt/missing
  index is an operational error. Full-document review and activation are pending. New governing
  policy text requires a new baseline version and explicit review before activation. This check
  is not overall remote-work eligibility.
- Keep synthetic JSON deterministic and validated. Distinguish missing employee from missing
  PTO; malformed data is an error. Drafts are returned but never stored or sent.
- Use one server tool-request dispatch adapter for validation, error classification, and
  tracing, after SDK request-envelope acceptance and before application argument validation.
  Validate advertised schemas and strict input models before invoking handlers and
  return machine-readable error envelopes; bypass SDK tool-input validation that would consume
  error types while preserving FastMCP discovery. Instrument the provided client for discovery
  and client-side failures. Sanitize SDK logging and errors; record argument names, never
  arbitrary values. The client preserves reliable structured classifications and otherwise
  reports `UNCLASSIFIED_ERROR` with no asserted origin, without interpreting messages or missing
  traces. Persist required traces before returning tool success; if persistence fails, surface
  an operational error without requiring a trace of the failed write. Use no secondary sink or
  retry infrastructure.
- Offer planned `--discover` and `--example TOOL_NAME` client commands documented in
  [quickstart.md](quickstart.md). They launch the server using stdio; no long-running server
  is assumed. The example environment explicitly passes only required nonsecret settings.
- Document the implemented MCP client/server architecture, F001 and synthetic-data connections,
  transport, discovery and invocation in the README and linked quickstart and tool contract.
  Keep the tool schemas in the contract and link to it rather than duplicating them. Describe
  the provided client as implemented and the agent integration as future work.

### Verification and acceptance

1. Contract tests exercise required/default/invalid inputs and all success statuses through
   MCP, including unsupported checks, timely, late, equal-time, verbal, wrong-authority,
   missing and unknown approval facts, equivalent timezone offsets, empty retrieval, missing
   records, complete governing-document changes, added subsections, unrelated documents,
   baseline integrity and review status, and normalization equivalence without discarding other
   characters.
2. Verify provenance and exact excerpts for search and section lookup, including active
   generation changes and corrupt snapshots. Do not silently fall back to current source files.
3. Use standard and raw MCP clients with deterministic F001 doubles and isolated synthetic
   data; discover exactly six tools, call each, interrupt transport, and verify `isError`,
   structured classifications, and client errors. Verify invalid input is rejected before the
   handler, and ambiguous errors become client-side `UNCLASSIFIED_ERROR` without an asserted
   origin or inference from error text or missing traces. The protocol-only discovery slice may
   run with isolated handlers first; adapter-dependent integration tests run only after the
   persistent sink and server adapter are implemented, and client-side error and trace tests
   run after the corresponding client instrumentation.
   Server tracing covers invocations reaching the adapter, including pre-handler argument
   errors; raw malformed protocol requests rejected before dispatch are not guaranteed server
   execution traces. The provided client separately traces protocol failures it observes and
   failed connections and discovery. Include a subprocess stdio test.
4. Assert no raw questions, employee records, draft text, injected secrets, or SDK request
   bodies appear in logs. Verify persisted traces with an operational sink; simulate server and
   client trace persistence failures and verify explicit errors and no successful tool result,
   without requiring a persisted trace of the failed write. Confirm no email/network actions or
   data mutation.
5. Run Ruff and the complete pytest suite in Python 3.11 on Windows and Linux; separately
   document an optional real-embedding smoke test and any dependency or resource limits.
6. Follow the implemented documentation to launch the server via the provided client, discover
   all six tools, compare their names, descriptions and schemas with the contract, and invoke a
   documented synthetic example over MCP. Compare the architecture and transport description
   with the implementation and record the commands and results or unverified limitations.
7. For FR-011 and SC-009, use the documented credential-free local/test configuration and the
   real MCP server and handlers to discover and invoke all six tools, reusing the deterministic
   stdio integration tests. Review required dependencies and record the configuration, commands,
   platform, per-tool results and limitations. A synthetic test-approved baseline is not approval
   of the production baseline. T033's execution does not depend on T032, a production model, or
   production baseline review; record its results or limitations for T032's final documentation
   review and serialize shared-file edits. Complete both checks before feature acceptance. This
   demonstrates local compatibility only; F006 measures deployed resources, provider quotas,
   runtime limits and operating costs and verifies integrated free-tier compliance.

## Requirement Mapping and Deferred Ownership

| Requirement | Design / verification |
|---|---|
| QR-002, QR-052 | Fictional JSON records, checked-in MCP code and deterministic fixtures. |
| QR-023, QR-024, QR-025 | FastMCP stdio server, six defined tools, real client discovery and invocation. |
| QR-027 | FR-010 and SC-005/SC-007; T028 updates linked implementation documentation and T032 verifies architecture, live discovery, schemas and an example invocation. F003 documents its actual agent-client integration. |
| QR-020, QR-021, QR-022 | Redacted client traces, explicit no-result/errors, safe mock-only actions; full agent behavior remains F003/F004. |
| QR-018, QR-026 | F002 supplies real protocol client; agent selection and agent-driven calls remain F003. |
| QR-003-QR-005, QR-007 | Reproducible installation and local docs; FR-011, SC-009 and T033 verify a credential-free, no-paid-service local/test configuration. F006 owns final hosting, deployed resource and cost measurements, and full setup verification. |
| QR-035 | Separate MCP deployment is not planned; conditional URL configuration remains F006 if architecture changes. |
| QR-038 | F002 adds a real MCP discovery/call test; F006 owns application-start and final CI/deployment gates. |

F002 alone cannot verify agent orchestration, workflow completion, final deployment, live
provider behavior, end-to-end evaluation, or free-tier resource limits. Project-level
traceability statuses and governance documents are not changed by this plan.

## Risks and Dependencies

- F001 `_active_metadata` is private and not an advertised API. Adapter tests must detect
  changes; a public F001 interface requires separate approval rather than silent source edits.
- Existing F001 snapshot validation does not validate all chunk fields; the adapter must
  validate fields, ranges, and document association before returning evidence.
- The document-level compliance baseline requires explicit full-document review and activation;
  verified source files must remain available and match the active snapshot. The fixed governing
  set requires reassessment if another policy is identified; the rule cannot decide legal
  exceptions or overall eligibility.
- Default SDK logs and exception text may expose inputs; restrict logging and sanitize
  outputs before recording traces. Protocol stdout is reserved for MCP.
- Instrumenting FastMCP's request-dispatch boundary may require an isolated dependency on
  private SDK internals; verify its behavior against the exact pinned SDK, including errors.
- SDK dependency resolution and real platform behavior are unverified until implementation;
  no live inference or Linux success is claimed.

## Complexity Tracking

No constitution violation or exception identified.
