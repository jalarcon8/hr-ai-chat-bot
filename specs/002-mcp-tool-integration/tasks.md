# Tasks: MCP Tool Integration

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [mcp-tools.md](contracts/mcp-tools.md), and
[quickstart.md](quickstart.md).

**Prerequisite**: Feature 001's existing retrieval implementation and snapshot format.
Do not modify Feature 001 or create another retrieval pipeline. Its remaining Linux and
live-model verification is not evidence that F002 has passed.

**Verification**: Required by FR-009 and SC-001 through SC-009. Use fictional fixtures, deterministic
embedders, and actual MCP stdio calls; routine tests must not require provider credentials.

**Format**: `[P]` marks tasks that can run concurrently once their stated prerequisites are
complete and do not edit the same files. `[US1]`, `[US2]`, and `[US3]` identify user stories.

## Phase 1: Setup

**Purpose**: Establish dependencies, package structure, and fictional data.

- [ ] T001 Pin `mcp==1.28.1` consistently in `pyproject.toml` and `requirements.txt`; retain Python 3.11 support and verify resolution and FastMCP imports without changing unrelated dependencies (QR-003, QR-004, QR-023).
- [ ] T002 [P] Create the `src/hr_mcp/__init__.py` package and small, clearly fictional `data/employees.json` and `data/pto.json` datasets matching `specs/002-mcp-tool-integration/data-model.md`, including a known employee without a PTO record (QR-002, QR-052).

## Phase 2: Foundational

**Purpose**: Provide shared contracts and test dependencies for all stories.

- [ ] T003 Define strictly validated inputs, successful outcome models, evidence metadata, the machine-readable server error classification/origin/code envelope, the client-side `UNCLASSIFIED_ERROR` with null origin, and allowlisted trace event types in `src/hr_mcp/models.py` according to `specs/002-mcp-tool-integration/contracts/mcp-tools.md`; reject unknown arguments, invalid types, blank required strings, boolean/nonpositive `k`, and unsupported enums (FR-002d, FR-006).
  Define the optional nested `approval_facts` fields, including boolean/null
  `no_other_approvals`, timestamp format, null/unknown handling, and contradictory-fact
  validation exactly as specified in the contract; reject the old top-level `approval_status`
  argument.
- [ ] T004 Create isolated synthetic policy, employee and PTO fixtures and deterministic subprocess-compatible embedding doubles in `tests/fixtures/mcp/`, including a test-approved document-level HR-004/HR-001 baseline, missing records, and changed or incomplete policy variants; do not modify `corpus/` (FR-009, QR-002).

**Checkpoint**: Shared contracts and fixtures are ready. No user story starts before T001-T004.

## Phase 3: User Story 1 - Discover and invoke MCP tools (Priority: P1)

**Goal**: Discover exactly six named tools and invoke them through a real stdio MCP session.

**Independent test**: Using isolated deterministic handlers, start the actual server/client
transport, discover six names and schemas, invoke each through MCP, and surface unavailable
server and unknown-tool failures. This establishes the protocol slice; the story's full
acceptance requires the real six handlers and end-to-end test in T020-T021. This slice does
not require the structured adapter errors or tracing implemented in T024-T025.

### Tests for User Story 1

- [ ] T005 [US1] Add real-stdio discovery and six-call protocol tests with deterministic test handlers in `tests/test_mcp_discovery.py`; assert tool names, descriptions, schemas, protocol invocation, unknown-tool handling, and unavailable-server failure (FR-001, FR-003, QR-023, QR-024).

### Implementation for User Story 1

- [ ] T006 [P] [US1] Implement the FastMCP server factory, six named tool registrations with declared schemas, stdio entry point, and injectable handlers in `src/hr_mcp/server.py`; reserve stdout exclusively for MCP and keep test handlers isolated from production (FR-001, FR-003, QR-023, QR-025).
- [ ] T007 [P] [US1] Implement the real stdio client lifecycle, discovery, tool invocation, unknown-tool and transport errors, and `--discover`/`--example TOOL_NAME` entry points in `src/hr_mcp/client.py`; do not bypass MCP (FR-003, FR-010, QR-023, QR-027).
- [ ] T008 [US1] Run `tests/test_mcp_discovery.py` against the pinned SDK and verify all six calls traverse stdio with deterministic handlers; record failures explicitly rather than substituting direct function calls (QR-023, QR-024, QR-038).

**Checkpoint**: The protocol slice works with doubles. Six real operations and full US1
acceptance are completed by T020-T021; do not claim the feature is complete at T008.

## Phase 4: User Story 2 - Retrieve policy evidence and employee data (Priority: P1)

**Goal**: Expose traceable F001 evidence, synthetic records, bounded compliance, and safe drafts.

**Independent test**: Invoke each real policy/data operation through MCP against an isolated
F001 index and fictional records; check exact sources, record matches, valid absences,
compliance limitations, and no external email or mutation.

### Tests for User Story 2

- [ ] T009 [P] [US2] Add search and section contract tests in `tests/test_mcp_policy.py` for ranked candidate evidence, unrelated nonempty results, empty retrieval, default/invalid `k`, exact section matching, ordered excerpts, source metadata, generation changes, invalid chunk metadata, and corrupt snapshots (FR-002b, FR-004, FR-004a).
- [ ] T010 [P] [US2] Add synthetic-data tests in `tests/test_mcp_data.py` for exact employee/PTO records, unknown employees, known employees without PTO, malformed files, duplicate IDs, invalid fields, and dangling PTO references (FR-005, FR-006, QR-002).
- [ ] T011 [P] [US2] Add bounded-compliance tests in `tests/test_mcp_compliance.py` for approved, not approved, unknown and omitted caller facts; unsupported checks; unchanged approved HR-004/HR-001; edits to existing sections and conflicting provisions elsewhere in each governing document; a new `2.2.1 Exception`; and changes to an unrelated document. For the added subsection explicitly assert the original indexed 2.2 chunk remains unchanged but the complete HR-004 canonical hash changes and the result is `indeterminate`. Cover missing governing records/files, unreadable or invalid UTF-8, unsafe paths, raw source/snapshot mismatches, missing or invalid citations, and missing, malformed, wrong-set/version or pin-mismatched baselines. Separately verify valid pinned approval records and `indeterminate` for missing fields, unapproved status, invalid approver/timestamp/reference, malformed or duplicate records, mismatched baseline ID/version, document ID/digest, normalization version, or any pinned approval field; matching document hashes alone must not establish approval. Treat synthetic review references as fixtures, not proof of real GitHub approval. Assert an unrelated document change alone does not invalidate the check, and unavailable/corrupt index remains an operational error. Verify CRLF/CR/LF and canonically equivalent Unicode produce equal canonical hashes when reindexed, other whitespace changes do not, and stale raw bytes fail even if canonical hashes match. Check exact indexed citations, documented execution contexts, and no overall-eligibility claim (FR-002a, SC-006).
  Add synthetic fact cases for `approved` with timely written People Operations approval;
  `not_approved` with no approval granted; and `approved` or `unknown` status with verbal,
  wrong-authority, late, and equal-time candidate details. For each disqualifier, assert
  `noncompliant` when `no_other_approvals` is `true`, and `indeterminate` when it is `false`,
  null, or omitted because a separate qualifying approval remains possible. An approval granted
  after travel uses `approved` with the actual timestamp and is not an invalid-argument error.
  Verify a qualifying `approved` candidate is `compliant` regardless of other approvals,
  `unknown` status with otherwise qualifying details is `indeterminate`, and a disqualifier with
  `no_other_approvals: true` remains conclusive despite unrelated missing facts. Cover the
  one-microsecond-before boundary; equivalent instants with different offsets; each
  missing/null/unknown fact; and null/omitted `approval_facts`. Verify malformed timestamps,
  offsets, enums, types (including non-boolean `no_other_approvals`), unknown fields,
  `not_approved` with a grant timestamp, `not_approved` with `no_other_approvals: false`,
  other contradictory `not_approved` details, and the old top-level `approval_status` are invalid
  arguments, including when the baseline is invalid. Verify `not_approved` with
  `no_other_approvals: true` or null/omitted is valid. Check every
  conclusion discloses unauthenticated caller assertions and limited scope. A missing or
  unreviewed baseline yields `indeterminate` even for otherwise disqualifying facts.
  Add F001-ingested fixtures with accented characters, emoji and other multibyte UTF-8 characters
  before the relevant evidence; assert the indexed zero-based half-open character offsets extract
  the exact snippet from the strictly decoded source, differ from byte positions, and do not work
  when applied to raw bytes. Cover CRLF and decomposed Unicode before the evidence so LF/NFC
  baseline normalization cannot be used for offset slicing. Test equivalent reindexed sources
  using their own offsets, invalid required offsets (negative, reversed, out of bounds, non-integer
  and boolean), snippet mismatch, and an unreconstructable decoded representation: each invalid
  citation or reconstruction yields `indeterminate` with an explanatory limitation. Exercise
  invalid citation metadata in a fixture that still passes F001 pointer, checksum and structural
  validation; distinguish it from a missing snapshot or one failing those checks, which remains
  an operational error.
- [ ] T012 [P] [US2] Add deterministic-draft and safety tests in `tests/test_mcp_draft.py` for required fields, optional details, repeatable output, and absence of sending, network calls, persistence, or synthetic-data mutation (FR-002c, FR-008, QR-022).

### Implementation for User Story 2

- [ ] T013 [P] [US2] Implement read-only employee/PTO JSON loading and validation in `src/hr_mcp/data.py`, returning `not_found` with the correct missing record category while surfacing malformed or unavailable data as errors (FR-005, FR-006, QR-002).
- [ ] T014 [US2] Implement `search_policy_documents` in `src/hr_mcp/policy.py` using F001 `retrieve`; preserve top-k ordering, scores and generation metadata, label nonempty results as candidates, and use `not_found` only for an empty successful retrieval (FR-004a, QR-024).
- [ ] T015 [US2] Implement exact section lookup in `src/hr_mcp/policy.py` using one F001 `_active_metadata` snapshot; validate consumed document/chunk fields, offsets and associations, match complete case-sensitive IDs, order unscored excerpts, preserve generation ID, and surface corrupt snapshots without reading live corpus files (FR-002b, FR-004).
  Preserve individual citation-validation failures distinctly from F001 snapshot validation
  failures so the compliance handler can return `indeterminate` for invalid required offsets.
- [ ] T016 [US2] Implement `out_of_state_prior_approval` in `src/hr_mcp/tools.py` using caller-supplied facts and indexed HR-004 section 2.2 citations from one active snapshot. Create the versioned `data/compliance-baselines/out-of-state-prior-approval-v2.json` for the complete HR-004 and HR-001 governing set. Obtain explicit full-document review and have an authorized maintainer verify each independent repository review record before activation; pin every per-document field in `data-model.md` separately in version-controlled implementation configuration. Validate approval records for completeness, format, approved status, binding and exact equality to the pin independently of content hashing; do not claim offline checks authenticate reviews. For each governing document safely resolve its indexed source under the configured corpus root, read it once, verify raw SHA-256 against that snapshot's F001 `content_hash`, and compare its complete UTF-8/LF/NFC canonical SHA-256 against the pin without trimming. For indexed citations, strictly decode those same bytes as UTF-8 without newline or Unicode normalization, validate zero-based, half-open Python string character offsets and exact snippet equality as specified in `data-model.md`, and never slice raw bytes or canonicalized text with those offsets; never use source files as a substitute for indexed citations. Return `indeterminate` with limitations for invalid required citation offsets, unreconstructable indexed text, missing/invalid/unapproved/unverifiable approval metadata, invalid baseline, missing/changed/unverifiable governing documents or insufficient citations; retain corrupt-index operational errors. Do not activate v2 before review or imply overall eligibility. New governing documents or policy changes require a new version and explicit review before activation (FR-002a, QR-021).
  The handler and baseline-validation implementation may be completed and exercised with the
  isolated test-approved fixture before production document review. Until the production baseline
  is reviewed and activated, real checks must fail closed as specified. T016 is complete only
  after its production review and activation requirements are satisfied; synthetic fixture
  approval is not production approval.
  Evaluate structured caller assertions under the contract's ordered rules, comparing timestamps
  as instants and requiring written People Operations approval strictly before travel. Reject
  malformed or contradictory inputs first; a disqualified candidate is conclusive only when the
  caller also asserts no other approval was granted. Otherwise, missing or unknown necessary
  facts are indeterminate unless a qualifying approval or absence of all approvals is established.
  Apply the baseline and citation guard before any definitive conclusion and disclose
  unauthenticated caller facts and limited scope in every result.
- [ ] T017 [US2] Implement deterministic `draft_hr_email` in `src/hr_mcp/tools.py` from nonblank recipient and purpose plus optional synthetic details; return subject/body only and do not send, persist, mutate, or perform external actions (FR-002c, QR-022).
- [ ] T018 [US2] Wire the six real handlers to their strict schemas and structured outcomes in `src/hr_mcp/server.py`; allow typed F001 and data operational failures to reach the T025 adapter for classification, never convert them to `not_found` or `indeterminate` successes (FR-001, FR-002, FR-006).

### Shared US3 prerequisites for US2 integration

- [ ] T024 [US3] Implement allowlisted trace events and an explicit, configurable persistent sink in `src/hr_mcp/trace.py`; record tool/operation, safe argument names, source IDs when available, and outcome/error category without raw values, and surface write failures as `trace_persistence_failure` without a secondary sink or retry infrastructure (FR-007, QR-020).
- [ ] T025 [US3] Implement one tool-request adapter at the dispatch boundary after SDK envelope acceptance in `src/hr_mcp/server.py`: bypass SDK tool-input validation and error-wrapping execution that would consume error types, validate advertised schemas and strict models before calling the underlying server-side handlers, classify typed validation/dependency and unexpected failures in the required structured MCP error envelope, and persist the required trace for every invocation reaching the adapter from any client before returning its result, including validation and execution errors. On persistence failure return the structured `OPERATIONAL_ERROR` with `isError=true`. Preserve FastMCP discovery, isolate SDK-internal coupling, and do not corrupt protocol stdout (FR-006, FR-007).

### US2 integration

- [ ] T019 [US2] Implement documented synthetic example arguments and safe subprocess configuration for all six tools in `src/hr_mcp/client.py`, using the actual F001 index and synthetic data rather than test doubles outside tests (FR-010, QR-027).
- [ ] T020 [US2] Add and, after T025, run an actual stdio subprocess integration test in `tests/test_mcp_stdio.py` that builds an isolated F001 snapshot with deterministic doubles, discovers and invokes all six real handlers, verifies structured results and source metadata, and exercises missing records and changed governing documents, including a new subsection whose original 2.2 chunk remains unchanged (SC-001, SC-002, QR-024, QR-025).
  Using standard and raw MCP clients with a synthetic reviewed baseline, exercise all T011
  approval scenarios, including unknown status with verbal-only, late-only, and
  wrong-authority-only candidates and each corresponding case where another qualifying approval
  remains possible; malformed or contradictory inputs, timezone-equivalent instants, equality
  and the smallest accepted earlier interval. Assert exact status, conclusion and nonempty
  limitations. For both `compliant` and `noncompliant`, assert nonempty verified supporting
  policy evidence and corresponding citations. For `indeterminate`, assert limitations explain
  why no definitive determination was possible: exercise missing facts with verified supporting
  evidence and check its citations, and unavailable or unverifiable supporting evidence with an
  empty evidence list and no fabricated citations. Assert structured `INVALID_ARGUMENT` for
  malformed calls and an operational error for a missing or corrupt index; neither error requires
  policy citations. Verify old top-level `approval_status` is rejected and an `approved` status
  alone is indeterminate. Repeat a known violation with an invalid baseline to verify fail-closed
  behavior rather than a definitive verdict. Through MCP, exercise the multibyte, CRLF and
  decomposed-Unicode citation fixtures and invalid-offset and unreconstructable-text cases from
  T011; assert exact indexed citations for valid evidence and `indeterminate` with an explanatory
  limitation for invalid required citation offsets or unreconstructable text.
- [ ] T021 [US2] Run `tests/test_mcp_discovery.py`, `tests/test_mcp_policy.py`, `tests/test_mcp_data.py`, `tests/test_mcp_compliance.py`, `tests/test_mcp_draft.py`, and `tests/test_mcp_stdio.py`; confirm US1's six-call acceptance against the real handlers as well as US2's evidence/data acceptance (SC-001, SC-002).

**Checkpoint**: All six real tools work through MCP. Operational trace and error acceptance
remain in US3; neither F003 orchestration nor F004 workflows are implemented here.

## Phase 5: User Story 3 - Diagnose and safely handle tool calls (Priority: P2)

**Goal**: Surface validation and operational failures and provide inspectable, redacted traces.

**Independent test**: Through both the provided client and a raw MCP client, exercise valid
and invalid calls, dependency failures, malformed protocol requests, discovery/transport
failures, and a failing trace sink; inspect persisted traces for calls reaching the server
adapter when the sink is operational and assert raw questions, secrets, records, snippets, and
drafts are absent. Verify SDK-rejected pre-dispatch protocol requests do not reach the adapter
or require a server execution trace. On persistence failure, verify explicit errors and no
successful tool result without expecting a persisted trace of the failed write.

### Tests for User Story 3

- [ ] T022 [P] [US3] Add MCP error and validation tests in `tests/test_mcp_errors.py` using a standard MCP client and a raw MCP client: assert `isError` and the exact `structuredContent.error` classification, origin, and code for invalid arguments, recognized dependency failures, and unexpected handler and adapter exceptions. Verify invalid input never invokes the handler; cover missing, incorrectly typed, blank or extra arguments, unsupported checks, and broken index/data. Separately verify independently established unknown-tool and discovery/connectivity client errors without requiring a server error envelope. Send malformed protocol envelopes with non-object arguments and a missing tool name through raw MCP; use boundary instrumentation to verify the pinned SDK rejects them before the adapter and handler with JSON-RPC `-32602`. Inject ambiguous SDK errors and missing or unrecognized envelopes into the provided client; assert `UNCLASSIFIED_ERROR`, null origin, and unchanged classification regardless of error text or missing trace information. Preserve known categories when reliably established and distinguish valid absence from errors (FR-006, SC-003).
  Cover every row of the FR-009 matrix below through actual MCP stdio calls to the real
  registrations and dispatch adapter, with synthetic fixtures and deterministic fault injection.
  Direct handler tests and the T005 isolated protocol handlers are not substitutes.

#### FR-009 six-tool verification matrix

For each row, invoke the named tool with both a standard MCP client and a raw MCP client.
Assert invalid calls do not invoke the handler and return `isError=true`, sanitized text and
`structuredContent.error` with `INVALID_ARGUMENT`, `input_validation`, `invalid_argument`.
For successful domain outcomes, assert `isError` is not true and `structuredContent` contains
the specified fields with non-applicable fields absent as specified in the contract; they are
not operational errors. For the listed operational or injected
execution failures, assert `isError=true`, sanitized text, and the exact
`structuredContent.error` classification, origin and code shown. Use valid arguments for
failure cases and inject failures deterministically, without real external services. For every
matrix invocation reaching the adapter with an operational sink, assert its persisted
allowlisted trace identifies the tool and outcome or error; T023 covers the documented
pre-dispatch and sink-failure exceptions.

| MCP tool | Invalid input | Domain outcome or execution failure and expected result |
|---|---|---|
| `search_policy_documents` | Blank `question` and `k: 0` | Empty retrieval: `not_found`, empty `evidence` and `generation_id`; unavailable index: `OPERATIONAL_ERROR`, `tool_execution`, `index_unavailable`; failed query embedding: `OPERATIONAL_ERROR`, `tool_execution`, `embedding_failure`. |
| `get_policy_section` | Blank `document_id` or `section` | Missing section: `not_found`, empty `evidence` and `generation_id`; unavailable index: `OPERATIONAL_ERROR`, `tool_execution`, `index_unavailable`. |
| `lookup_employee_profile` | Missing or blank `employee_id` | Unknown employee: `not_found`, `missing: "employee"`; unavailable or malformed data: `OPERATIONAL_ERROR`, `tool_execution`, `data_unavailable`. |
| `check_pto_balance` | Missing or blank `employee_id` | Unknown employee and known employee without PTO: `not_found`, respectively `missing: "employee"` and `"pto"`; unavailable or malformed data: `OPERATIONAL_ERROR`, `tool_execution`, `data_unavailable`. |
| `check_policy_compliance` | Unsupported `check_id` or contradictory approval facts | Missing facts or unverifiable baseline: `indeterminate`, matching `check_id`, `conclusion: "indeterminate"`, `evidence` and explanatory nonempty `limitations`; unavailable index: `OPERATIONAL_ERROR`, `tool_execution`, `index_unavailable`. Preserve T020's outcome-specific citation assertions. |
| `draft_hr_email` | Blank `recipient_name` or `purpose` | With valid inputs, inject an unexpected exception at handler execution: `UNKNOWN_ERROR`, `tool_execution`, `internal_error`; this is a simulated failure, not a domain outcome or external action. |

- [ ] T023 [P] [US3] Add trace tests in `tests/test_mcp_trace.py` using a raw SDK client and the provided client: with an operational sink, verify persisted server traces for successful invocations, handler failures, and invalid tool arguments that reach the adapter, and separate client traces for observed connection/discovery/protocol failures. Send raw malformed protocol envelopes rejected by the SDK before dispatch; verify the adapter and handler are not invoked and no server execution trace is required. Simulate server sink failure after a successful handler and after a failed call, asserting `isError=true`, `OPERATIONAL_ERROR`, and `trace_persistence_failure` with no successful result; simulate client-side trace persistence failure and assert an explicit operational error. Do not require a trace of a failed write; also verify redaction of injected secrets and user text, including malformed payloads, and server stdout separation (FR-007, SC-004).
  For each matrix tool, exercise its invalid call and listed domain outcome or execution
  failure through MCP and assert the corresponding persisted, allowlisted trace identifies the
  tool and outcome or error when the sink is operational. Verify caller-supplied approval facts
  and timestamps are not recorded as raw trace values. Pre-dispatch SDK rejections require no
  server execution trace; a trace-sink failure is an explicit operational error without a
  guarantee that the failed write is persisted. Also simulate persistence failure while recording
  an invalid-argument trace before the handler runs; assert `isError=true`,
  `OPERATIONAL_ERROR`, `trace_persistence`, `trace_persistence_failure`, and no successful result.

### Implementation for User Story 3

- [ ] T026 [US3] Add client-side discovery, unknown-tool, connection, transport, and observed protocol error trace events in `src/hr_mcp/client.py`; preserve valid structured error fields and independently established client failures, and report errors lacking reliable classification metadata as `UNCLASSIFIED_ERROR` with null origin. Do not infer categories or origins from message text or missing execution traces. Surface independently detected client-side trace persistence failures as explicit `OPERATIONAL_ERROR` errors with code `trace_persistence_failure`; sanitize SDK messages and preserve tool failures (FR-006, FR-007, QR-021).
- [ ] T027 [US3] After T018, T021 and T024-T026, run `tests/test_mcp_errors.py` and `tests/test_mcp_trace.py` against the real pinned SDK, real tool registrations and stdio transport; verify every FR-009 matrix row and its trace assertions, classifications with both clients, persisted inspectable traces for all invocations reaching the adapter when the sink is operational, and SDK-rejected pre-dispatch protocol failures are not required to have server execution traces. Include T020-T021's definitive compliance outcome and citation results in FR-009 acceptance. Verify trace persistence failures produce explicit errors without successful tool results or a required persisted failure trace (FR-009, SC-003, SC-004).

**Checkpoint**: The three stories' protocol, evidence/data, error, and trace acceptance
scenarios are covered without real HR integrations or external actions.

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Make installation, execution, CI, and acceptance reproducible.

- [ ] T028 [P] Update `README.md`, `specs/002-mcp-tool-integration/quickstart.md`, and `specs/002-mcp-tool-integration/contracts/mcp-tools.md` to reflect the implemented system: document client/server architecture and component connections to F001 and synthetic data, stdio transport choice, how the provided client discovers names and schemas and invokes tools through MCP, and reproducible synthetic example commands, arguments and expected results. Keep all six implemented tool names, descriptions and input schemas in the contract and link to them from the README and quickstart rather than duplicating them; distinguish the implemented client from future agent integration. Preserve Python 3.11 installation, synthetic datasets, F001 index/model prerequisites, trace allowlist/sink, safe failure behavior, baseline location and review/activation procedure, and reviewed-policy limitations. Document the separate SC-009 local/test configuration, its deterministic fixtures, credential-free execution and commands, and its distinction from the production baseline and deployed free-tier verification (FR-010, FR-011, SC-009, QR-003, QR-004, QR-005, QR-027).
- [ ] T029 Ensure `.github/workflows/ci.yml` installs the declared MCP dependency and executes the real MCP discovery/call tests and full pytest suite on Python 3.11; add an appropriate import or startup check if absent without adding deployment or changing unrelated CI behavior (QR-023, QR-038).
- [ ] T032 Verify QR-027 documentation after implementation and T028: inspect the README, quickstart and contract against the implemented client, server, F001 and synthetic-data connections and actual transport. Follow the documented local setup and commands to launch the server through the real stdio client, discover all six tool names, descriptions and input schemas, and compare them with the documented contract. Invoke the documented `lookup_employee_profile` synthetic example through MCP; compare the documented arguments and expected result with the actual client example and response. Record the platform, commands and results in the README or quickstart; record failures or unavailable prerequisites explicitly and do not mark verification passed if any step was not completed. For the final documentation review, consider T033's recorded results or its explicitly recorded unverified limitations and ensure the documentation accurately distinguishes synthetic and standard setups; T033 success is not a prerequisite for executing the QR-027 check (FR-010, SC-005, SC-007, QR-027).
- [ ] T033 Verify FR-011 and SC-009 using the local/test configuration and existing T020 stdio integration infrastructure. Execution requires the T018 real server registrations and handlers, the T024 sink and T025 adapter, the authored T020 integration tests, T004 synthetic fixtures and installed local test dependencies; it does not require T032, T021 or T027 to have passed, a production embedding model, a reviewed production baseline, or paid external services. T016's handler and baseline-validation implementation must exist, but its production review and activation need not be complete. Review the manifests, transitive runtime/test dependencies and documented setup for mandatory paid services, subscriptions, infrastructure or API credentials; identify the dependencies and their sources and record any mandatory paid or authenticated access as a failure. Use locally installed packages or unauthenticated free public package sources for installation. Run with API credentials absent from the test process and server subprocess, including any credential variables identified in the dependency and configuration review; isolate accessible credential files and provider profiles as needed. Record variable names and absence only, never values. Use the real server, registrations and handlers, deterministic F001 embedder and isolated snapshot, synthetic records, local trace sink and a synthetic test-approved baseline. Verify no live model or hosted runtime service is required, and use existing doubles or fault injection to reject external model/service calls. Start the server over stdio, discover exactly six agreed tools and invoke each at least once with valid synthetic inputs; assert `isError` is not true and each structured result matches its contract, including applicable compliance evidence and limitations. Record the platform, commands, dependency and access review, environment configuration, per-tool inputs or test identifiers and actual outcomes, and any failures or limitations in `specs/002-mcp-tool-integration/quickstart.md`; do not record credentials. T028 must document this configuration before T033 is marked complete. Mark SC-009 unverified if any check is missing or fails. The synthetic review does not authorize a production baseline, and successful local tests do not establish production readiness or deployment compliance. F006 owns deployed resource usage, provider quotas, runtime limits, operating costs and integrated free-tier verification (FR-011, SC-009, QR-003).
- [ ] T030 Run the documented clean-install, Ruff, full pytest suite, six-tool stdio examples, and acceptance checks on Windows and Linux Python 3.11; record actual results and dependency, model-resource, or unavailable-platform limitations in `README.md` and do not mark unrun checks as passed (SC-005, QR-003, QR-004, QR-005).
- [ ] T031 Review `specs/002-mcp-tool-integration/spec.md`, `specs/002-mcp-tool-integration/plan.md`, `specs/002-mcp-tool-integration/contracts/mcp-tools.md`, and this task list against F002's assigned requirements; document unverified evidence and dependencies without changing project-level requirement statuses (QR-002, QR-023-QR-027, QR-052).
  Record FR-009 verification evidence in `specs/002-mcp-tool-integration/quickstart.md`: for
  each matrix row include executed test identifiers, commands, platform, actual result and any
  unverified scenarios or limitations. Include T027 trace and client results, and recommend
  applicable project traceability updates without modifying governance documents or marking
  unexecuted checks as verified.
  For FR-012, SC-008 and the F002 contribution to QR-052, verify that each required file below
  exists as a file in the working tree and is tracked by Git, using
  `git ls-files --error-unmatch -- <path>` or an equivalent explicit tracked-file check:
  - Source and tool definitions: `src/hr_mcp/__init__.py`, `server.py`, `client.py`,
    `policy.py`, `data.py`, `tools.py`, `models.py`, and `trace.py` under `src/hr_mcp/`,
    plus any other source files required by the implemented F002 tools.
  - Synthetic data and baseline: `data/employees.json`, `data/pto.json`, and
    `data/compliance-baselines/out-of-state-prior-approval-v2.json`, plus the version-controlled
    implementation configuration containing the baseline pin.
  - Tests: `tests/test_mcp_discovery.py`, `test_mcp_policy.py`, `test_mcp_data.py`,
    `test_mcp_compliance.py`, `test_mcp_draft.py`, `test_mcp_stdio.py`, `test_mcp_errors.py`,
    and `test_mcp_trace.py` under `tests/`; every persistent fixture file required by those tests
    must exist and be tracked, including at least one tracked file in `tests/fixtures/mcp/`.
  - Contract and documentation: `README.md` and `specs/002-mcp-tool-integration/spec.md`,
    `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, and
    `contracts/mcp-tools.md` under the feature directory.
  - Configuration: `pyproject.toml`, `requirements.txt`, and `.github/workflows/ci.yml`.
  Record the complete inventory, Git revision or branch and staged/unstaged context, commands,
  per-file presence and tracking results, and any missing, untracked or unverified items in
  `specs/002-mcp-tool-integration/quickstart.md`. Do not count generated indexes, caches, logs
  or runtime-created temporary fixtures as required repository files. All applicable required
  files must pass before SC-008 is satisfied; tracking may include staged files and does not
  itself prove a commit or submission. Report only partial QR-052 coverage and recommend
  traceability updates; F006 retains final project-wide completeness and submission checks.
  Preliminary evidence, 2026-11-14, branch `002-mcp-tool-integration`: PowerShell `Test-Path`
  found `src/hr_mcp/`, all eight listed MCP test files, both synthetic data files, the v2
  baseline, and `tests/fixtures/mcp/` absent. `git ls-files --error-unmatch -- <path>` confirmed
  the README, dependency manifests, CI workflow, feature spec, tasks, contract and quickstart
  are tracked. `git status --short -- <path>` showed the feature spec, tasks, contract and
  quickstart have unstaged changes. This is a partial pre-implementation inventory, not T031
  completion or SC-008 verification; repeat and record the full inventory after implementation.

## Dependencies and Execution Order

### Phase dependencies

- T001-T002 precede T003-T004; T003-T004 block all story implementation.
- US1 establishes the real protocol boundary. T006 and T007 are independent after the
  foundation, but T008 requires T005, T006, and T007. Its protocol-only tests do not depend on
  the later classification adapter.
- US2 tests T009-T012 can be written in parallel after the foundation. T013 is independent
  of T014-T015; T015 follows T014 because both edit `policy.py`. T016 requires T015 and
  follows T017 or precedes it serially because both edit `tools.py`. T018 requires T006,
  T013-T015, T017, and T016's handler and baseline-validation implementation, not T016's
  production review or activation. T019 requires T007 and T018. T024 requires the foundation; T025 requires T018
  and T024. T020 requires T018, T019, and T025; it can be authored earlier but must not be
  required to pass until those prerequisites are complete. T021 requires T020 and the preceding
  tests. Full US1 acceptance depends on T020-T021.
- US3 test drafts T022-T023 can be written after the foundation; their execution in T027
  requires T018, T021 and T024-T026 as well as both test files. T018 requires the real handlers
  T013-T017, with T016's implementation sufficient before production review; T021 includes the T020 compliance outcome tests, and T025 provides the
  error-classification adapter. T026 requires T019 and T024.
  T025 and T026 edit different files but should start only after their respective US2 edits are
  complete.
- T028-T029 can proceed after story interfaces stabilize and edit different files. T032's
  QR-027 check requires T021, T027, and T028; its execution does not require T033 to pass.
  T033 execution requires T018, T024-T025, authored T020 tests, T004 fixtures and installed
  local test dependencies, but neither T032 nor production baseline review or activation.
  T028 must document the tested configuration before T033 completion. Record T033 results or
  limitations before T032's final documentation review, and serialize edits to shared files;
  documentation-edit ordering is not a runtime dependency between the checks.
  T030 requires completed T016, T021, T027-T029, T032 and T033; both checks must pass before
  Feature 002 acceptance. T031 follows T030 so unverified evidence is reported.

### Story dependencies

| Story | Independent slice | Full acceptance dependency |
|---|---|---|
| US1 | Six named protocol handlers tested through stdio with deterministic doubles | US2 real handlers and T020-T021 |
| US2 | Real evidence/data/tools exercised via the US1 stdio server/client | US1 protocol foundation and T024-T025; US3 acceptance remains in T027 |
| US3 | Raw/provided clients exercise failures and inspect traces | US1 server/client, US2 real handlers, T024-T026 |

### Parallel examples

- After T003-T004, draft `tests/test_mcp_policy.py`, `tests/test_mcp_data.py`,
  `tests/test_mcp_compliance.py`, and `tests/test_mcp_draft.py` concurrently.
- After the foundation, develop `src/hr_mcp/server.py` and `src/hr_mcp/client.py` separately
  for T006-T007. Coordinate before subsequent wiring tasks.
- After interfaces stabilize, update `README.md`/quickstart and `.github/workflows/ci.yml`
  concurrently for T028-T029.

## Implementation Strategy

1. Establish the Python 3.11 MCP dependency, fictional fixtures, and shared contracts.
2. Deliver the US1 stdio discovery/invocation slice with deterministic handlers as the MVP
   protocol milestone; it is not complete feature acceptance.
3. Implement and integrate all six real operations for US2; add the T024 trace sink and T025
   server adapter before T020-T021 run against real handlers.
4. Complete US3's client-side error and trace behavior, then run its cross-boundary tests.
5. Execute the local compatibility check T033 independently of T032; use its recorded results
   or limitations in T032's final documentation review. Complete both checks and T016's
   production review before Feature 002 acceptance, then run clean-install and full acceptance
   checks on both target platforms and report gaps.

## Requirement Coverage

| Requirement | Implementation / verification tasks |
|---|---|
| FR-009 | T004, T020-T023, T027, T031; six-tool matrix and recorded verification evidence |
| FR-011 | SC-009; T020-T021, T028 and T033 verify and document credential-free local compatibility; F006 verifies integrated deployment |
| QR-002 | T002, T004, T010, T013, T020 |
| QR-023 | T001, T005-T008, T020, T029 |
| QR-024 | T005-T008, T014, T018, T020-T021 |
| QR-025 | T005-T007, T009-T012, T013-T021 |
| QR-027 | T007, T019, T028, T032; FR-010, SC-005 and SC-007 |
| QR-052 | FR-012, SC-008; T002, T006, T013-T018, T031 verifies and records F002's tracked repository contribution; final verification remains F006 |
| QR-020-QR-022 (supporting F003/F004) | T011-T012, T016-T017, T022-T027 |
| QR-018, QR-026 (supporting F003) | T005-T008, T020-T021; agent selection and agent-driven calls remain F003 |
| QR-003-QR-005, QR-007 (supporting F006) | T001, T023-T024, T028-T030, T033; SC-009 checks local compatibility, while free-tier deployment and final evaluation remain F006 |
| QR-035 (conditional, F006-owned) | T031; separate MCP deployment is not planned |
| QR-038 (supporting F006) | T005, T008, T020, T029; final application-start and deployment gates remain F006 |

F002 does not independently verify F003 orchestration, F004 workflows, F005 UI, or F006
deployment, complete application-start behavior, evaluation, and submission.
