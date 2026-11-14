# Implementation Plan: MCP Tool Integration

**Feature**: `002-mcp-tool-integration` | **Date**: 2026-11-14 |
**Spec**: [spec.md](spec.md)

**Branch**: No feature branch created; the repository was on `main` during planning.

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

**Storage**: Existing F001 active FAISS snapshot; small version-controlled synthetic employee
and PTO JSON files. No database or second index. Trace events use a configurable local sink.

**Testing**: pytest and Ruff; deterministic embedder and synthetic fixtures; real MCP stdio
subprocess tests including discovery, all six calls, bad schemas, failures, and traces.
Do not require Groq, a live model, or a provider key for routine tests.

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
  tasks.md                 # Future /speckit-tasks output; not produced by planning
```

### Proposed implementation layout

```text
src/hr_rag/                # Existing F001; no retrieval replacement
src/hr_mcp/
  server.py                # FastMCP registrations and stdio entry point
  client.py                # stdio lifecycle, discovery, calls, examples and client traces
  policy.py                # F001 search and active-snapshot section adapter
  data.py                  # validated read-only synthetic JSON records
  tools.py                 # bounded compliance and deterministic drafting
  models.py                # tool inputs, outputs, errors, safe trace events
data/
  employees.json
  pto.json
tests/
  test_mcp_tools.py
  test_mcp_stdio.py
  fixtures/                # isolated fictional records and deterministic doubles
```

These are proposed paths, not existing implementations. Keep modules cohesive and adjust
the split if unnecessary during tasks. Add the SDK to `pyproject.toml` and keep
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
- For the initial compliance check, use caller-supplied approval status and the reviewed
  `HR-004` section 2.2. Reconstruct the complete section only from overlapping/adjacent
  indexed excerpts and compare its newline-normalized content with the reviewed baseline.
  Changed, incomplete, or absent policy evidence produces `indeterminate`; a corrupt/missing
  index is an operational error. This check is not overall remote-work eligibility.
- Keep synthetic JSON deterministic and validated. Distinguish missing employee from missing
  PTO; malformed data is an error. Drafts are returned but never stored or sent.
- Instrument the server at the MCP tool-request dispatch boundary, outside SDK schema
  validation, so calls from any client are traced. Instrument the provided client for
  discovery and client-side failures. Sanitize SDK logging and errors; record argument names,
  never arbitrary values. Surface trace-sink failures.
- Offer planned `--discover` and `--example TOOL_NAME` client commands documented in
  [quickstart.md](quickstart.md). They launch the server using stdio; no long-running server
  is assumed. The example environment explicitly passes only required nonsecret settings.

### Verification and acceptance

1. Contract tests exercise required/default/invalid inputs and all success statuses through
   MCP, including unsupported checks, missing/unknown approval, empty retrieval, missing
   records, and changed/incomplete policy evidence.
2. Verify provenance and exact excerpts for search and section lookup, including active
   generation changes and corrupt snapshots. Do not silently fall back to current source files.
3. Use a subprocess stdio test with deterministic F001 doubles and isolated synthetic data;
   discover exactly six tools, call each, interrupt transport, and verify `isError` and client
   errors. Server tracing must cover schema errors occurring before tool execution, including
   calls from a raw SDK client; the provided client traces failed connections and discovery.
4. Assert no raw questions, employee records, draft text, injected secrets, or SDK request
   bodies appear in logs; test a failing trace sink. Confirm no email/network actions or data
   mutation.
5. Run Ruff and the complete pytest suite in Python 3.11 on Windows and Linux; separately
   document an optional real-embedding smoke test and any dependency or resource limits.

## Requirement Mapping and Deferred Ownership

| Requirement | Design / verification |
|---|---|
| QR-002, QR-052 | Fictional JSON records, checked-in MCP code and deterministic fixtures. |
| QR-023, QR-024, QR-025 | FastMCP stdio server, six defined tools, real client discovery and invocation. |
| QR-027 | Contracts, quickstart and implementation README document schemas, architecture, transport, discovery and calls. |
| QR-020, QR-021, QR-022 | Redacted client traces, explicit no-result/errors, safe mock-only actions; full agent behavior remains F003/F004. |
| QR-018, QR-026 | F002 supplies real protocol client; agent selection and agent-driven calls remain F003. |
| QR-003-QR-005, QR-007 | Reproducible installation, local docs, bounded resources, environment secrets; final hosting and full setup ownership remains F006. |
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
- The reviewed compliance baseline intentionally requires review after any section change;
  the initial rule cannot decide other policies or legal exceptions.
- Default SDK logs and exception text may expose inputs; restrict logging and sanitize
  outputs before recording traces. Protocol stdout is reserved for MCP.
- Instrumenting FastMCP's request-dispatch boundary may require an isolated dependency on
  private SDK internals; verify its behavior against the exact pinned SDK, including errors.
- SDK dependency resolution and real platform behavior are unverified until implementation;
  no live inference or Linux success is claimed.

## Complexity Tracking

No constitution violation or exception identified.
