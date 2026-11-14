# Tasks: MCP Tool Integration

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [mcp-tools.md](contracts/mcp-tools.md), and
[quickstart.md](quickstart.md).

**Prerequisite**: Feature 001's existing retrieval implementation and snapshot format.
Do not modify Feature 001 or create another retrieval pipeline. Its remaining Linux and
live-model verification is not evidence that F002 has passed.

**Tests**: Required by FR-009 and SC-001 through SC-006. Use fictional fixtures, deterministic
embedders, and actual MCP stdio calls; routine tests must not require provider credentials.

**Format**: `[P]` marks tasks that can run concurrently once their stated prerequisites are
complete and do not edit the same files. `[US1]`, `[US2]`, and `[US3]` identify user stories.

## Phase 1: Setup

**Purpose**: Establish dependencies, package structure, and fictional data.

- [ ] T001 Pin `mcp==1.28.1` consistently in `pyproject.toml` and `requirements.txt`; retain Python 3.11 support and verify resolution and FastMCP imports without changing unrelated dependencies (QR-003, QR-004, QR-023).
- [ ] T002 [P] Create the `src/hr_mcp/__init__.py` package and small, clearly fictional `data/employees.json` and `data/pto.json` datasets matching `specs/002-mcp-tool-integration/data-model.md`, including a known employee without a PTO record (QR-002, QR-052).

## Phase 2: Foundational

**Purpose**: Provide shared contracts and test dependencies for all stories.

- [ ] T003 Define strictly validated inputs, successful outcome models, evidence metadata, sanitized error categories, and allowlisted trace event types in `src/hr_mcp/models.py` according to `specs/002-mcp-tool-integration/contracts/mcp-tools.md`; reject unknown arguments, invalid types, blank required strings, boolean/nonpositive `k`, and unsupported enums (FR-002d, FR-006).
- [ ] T004 Create isolated synthetic policy, employee and PTO fixtures and deterministic subprocess-compatible embedding doubles in `tests/fixtures/mcp/`, including reviewed HR-004 section 2.2, missing records, and changed or incomplete policy variants; do not modify `corpus/` (FR-009, QR-002).

**Checkpoint**: Shared contracts and fixtures are ready. No user story starts before T001-T004.

## Phase 3: User Story 1 - Discover and invoke MCP tools (Priority: P1)

**Goal**: Discover exactly six named tools and invoke them through a real stdio MCP session.

**Independent test**: Using isolated deterministic handlers, start the actual server/client
transport, discover six names and schemas, invoke each through MCP, and surface unavailable
server and unknown-tool failures. This establishes the protocol slice; the story's full
acceptance requires the real six handlers and end-to-end test in T020-T021.

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
- [ ] T011 [P] [US2] Add bounded-compliance tests in `tests/test_mcp_compliance.py` for approved, not approved, unknown and omitted facts; unsupported checks; reviewed, absent, changed, incomplete and corrupted HR-004 evidence; and no overall-eligibility claim (FR-002a, SC-006).
- [ ] T012 [P] [US2] Add deterministic-draft and safety tests in `tests/test_mcp_draft.py` for required fields, optional details, repeatable output, and absence of sending, network calls, persistence, or synthetic-data mutation (FR-002c, FR-008, QR-022).

### Implementation for User Story 2

- [ ] T013 [P] [US2] Implement read-only employee/PTO JSON loading and validation in `src/hr_mcp/data.py`, returning `not_found` with the correct missing record category while surfacing malformed or unavailable data as errors (FR-005, FR-006, QR-002).
- [ ] T014 [US2] Implement `search_policy_documents` in `src/hr_mcp/policy.py` using F001 `retrieve`; preserve top-k ordering, scores and generation metadata, label nonempty results as candidates, and use `not_found` only for an empty successful retrieval (FR-004a, QR-024).
- [ ] T015 [US2] Implement exact section lookup in `src/hr_mcp/policy.py` using one F001 `_active_metadata` snapshot; validate consumed document/chunk fields, offsets and associations, match complete case-sensitive IDs, order unscored excerpts, preserve generation ID, and surface corrupt snapshots without reading live corpus files (FR-002b, FR-004).
- [ ] T016 [US2] Implement `out_of_state_prior_approval` in `src/hr_mcp/tools.py` using caller-supplied facts and cited HR-004 section 2.2 from one active snapshot; compare the fully reconstructed, newline-normalized section to the reviewed baseline, return `indeterminate` for unknown facts or absent/changed/incomplete evidence, and never imply overall eligibility (FR-002a, QR-021).
- [ ] T017 [US2] Implement deterministic `draft_hr_email` in `src/hr_mcp/tools.py` from nonblank recipient and purpose plus optional synthetic details; return subject/body only and do not send, persist, mutate, or perform external actions (FR-002c, QR-022).
- [ ] T018 [US2] Wire the six real handlers to their strict schemas and structured outcomes in `src/hr_mcp/server.py`; propagate F001 and data operational errors as MCP errors, not `not_found` or `indeterminate` successes (FR-001, FR-002, FR-006).
- [ ] T019 [US2] Implement documented synthetic example arguments and safe subprocess configuration for all six tools in `src/hr_mcp/client.py`, using the actual F001 index and synthetic data rather than test doubles outside tests (FR-010, QR-027).
- [ ] T020 [US2] Add and run an actual stdio subprocess integration test in `tests/test_mcp_stdio.py` that builds an isolated F001 snapshot with deterministic doubles, discovers and invokes all six real handlers, verifies structured results and source metadata, and exercises missing records and changed policy evidence (SC-001, SC-002, QR-024, QR-025).
- [ ] T021 [US2] Run `tests/test_mcp_discovery.py`, `tests/test_mcp_policy.py`, `tests/test_mcp_data.py`, `tests/test_mcp_compliance.py`, `tests/test_mcp_draft.py`, and `tests/test_mcp_stdio.py`; confirm US1's six-call acceptance against the real handlers as well as US2's evidence/data acceptance (SC-001, SC-002).

**Checkpoint**: All six real tools work through MCP. Operational trace and error acceptance
remain in US3; neither F003 orchestration nor F004 workflows are implemented here.

## Phase 5: User Story 3 - Diagnose and safely handle tool calls (Priority: P2)

**Goal**: Surface validation and operational failures and provide inspectable, redacted traces.

**Independent test**: Through both the provided client and a raw MCP client, exercise valid
and invalid calls, dependency failures, discovery/transport failures, and a failing trace sink;
inspect traces and assert raw questions, secrets, records, snippets, and drafts are absent.

### Tests for User Story 3

- [ ] T022 [P] [US3] Add MCP error and validation tests in `tests/test_mcp_errors.py` for missing, incorrectly typed, blank or extra arguments, unsupported checks, broken index/data, unknown tools, discovery/connectivity failures, and distinct successful absence versus `isError` responses (FR-006, SC-003).
- [ ] T023 [P] [US3] Add trace tests in `tests/test_mcp_trace.py` using a raw SDK client and the provided client to cover calls rejected before tool execution, successful and failed calls, connection/discovery errors, injected secrets and user text, server stdout separation, and trace-sink failure (FR-007, SC-004).

### Implementation for User Story 3

- [ ] T024 [US3] Implement allowlisted trace events and an explicit, configurable sink in `src/hr_mcp/trace.py`; record tool/operation, safe argument names, source IDs when available, and outcome/error category without raw values, and surface write failures (FR-007, QR-020).
- [ ] T025 [US3] Instrument the MCP tool-request dispatch boundary before SDK schema validation in `src/hr_mcp/server.py` so calls from any client, including pre-handler validation failures, are traced; isolate SDK-internal coupling, sanitize errors/logging, and surface trace failures without corrupting protocol stdout (FR-006, FR-007).
- [ ] T026 [US3] Add client-side discovery, unknown-tool, connection, and transport error categories and trace events in `src/hr_mcp/client.py`; sanitize SDK messages and preserve MCP tool errors as failures rather than success-shaped results (FR-006, FR-007, QR-021).
- [ ] T027 [US3] Run `tests/test_mcp_errors.py` and `tests/test_mcp_trace.py` against the real pinned SDK and stdio transport; verify both successful and failed calls have inspectable traces and failures to write traces are surfaced (SC-003, SC-004).

**Checkpoint**: The three stories' protocol, evidence/data, error, and trace acceptance
scenarios are covered without real HR integrations or external actions.

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Make installation, execution, CI, and acceptance reproducible.

- [ ] T028 [P] Update `README.md` and `specs/002-mcp-tool-integration/quickstart.md` with Python 3.11 installation, stdio server/client and examples, six schemas, synthetic datasets, F001 index/model prerequisites, trace allowlist/sink, safe failure behavior, and reviewed-policy limitations (FR-010, QR-004, QR-005, QR-027).
- [ ] T029 Ensure `.github/workflows/ci.yml` installs the declared MCP dependency and executes the real MCP discovery/call tests and full pytest suite on Python 3.11; add an appropriate import or startup check if absent without adding deployment or changing unrelated CI behavior (QR-023, QR-038).
- [ ] T030 Run the documented clean-install, Ruff, full pytest suite, six-tool stdio examples, and acceptance checks on Windows and Linux Python 3.11; record actual results and dependency, model-resource, or unavailable-platform limitations in `README.md` and do not mark unrun checks as passed (SC-005, QR-003, QR-004, QR-005).
- [ ] T031 Review `specs/002-mcp-tool-integration/spec.md`, `specs/002-mcp-tool-integration/plan.md`, `specs/002-mcp-tool-integration/contracts/mcp-tools.md`, and this task list against F002's assigned requirements; document unverified evidence and dependencies without changing project-level requirement statuses (QR-002, QR-023-QR-027, QR-052).

## Dependencies and Execution Order

### Phase dependencies

- T001-T002 precede T003-T004; T003-T004 block all story implementation.
- US1 establishes the real protocol boundary. T006 and T007 are independent after the
  foundation, but T008 requires both.
- US2 tests T009-T012 can be written in parallel after the foundation. T013 is independent
  of T014-T015; T015 follows T014 because both edit `policy.py`. T016 requires T015 and
  follows T017 or precedes it serially because both edit `tools.py`. T018 requires T006 and
  T013-T017; T019 requires T007 and T018. T020 requires T018-T019; T021 requires T020 and
  the preceding tests. Full US1 acceptance depends on T020-T021.
- US3 test drafts T022-T023 can be written after the foundation. T024 precedes T025-T026;
  T025 requires T018, and T026 requires T019. T027 requires T022-T026. T025 and T026 edit
  different files but should start only after their respective US2 edits are complete.
- T028-T029 can proceed after story interfaces stabilize and edit different files. T030
  requires T021, T027, T028, and T029. T031 follows T030 so unverified evidence is reported.

### Story dependencies

| Story | Independent slice | Full acceptance dependency |
|---|---|---|
| US1 | Six named protocol handlers tested through stdio with deterministic doubles | US2 real handlers and T020-T021 |
| US2 | Real evidence/data/tools exercised via the US1 stdio server/client | US1 protocol foundation; US3 required for complete redacted failure tracing |
| US3 | Raw/provided clients exercise failures and inspect traces | US1 server/client and US2 real handlers |

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
3. Implement and integrate all six real operations for US2, then re-run US1 with real handlers.
4. Complete US3's cross-boundary error and redacted trace behavior, including raw-client tests.
5. Run clean-install and full acceptance checks on both target platforms and report any gaps.

## Requirement Coverage

| Requirement | Implementation / verification tasks |
|---|---|
| QR-002 | T002, T004, T010, T013, T020 |
| QR-023 | T001, T005-T008, T020, T029 |
| QR-024 | T005-T008, T014, T018, T020-T021 |
| QR-025 | T005-T007, T009-T012, T013-T021 |
| QR-027 | T007, T019, T028 |
| QR-052 | T002, T006, T013-T018, T031 |
| QR-020-QR-022 (supporting F003/F004) | T011-T012, T016-T017, T022-T027 |
| QR-018, QR-026 (supporting F003) | T005-T008, T020-T021; agent selection and agent-driven calls remain F003 |
| QR-003-QR-005, QR-007 (supporting F006) | T001, T023-T024, T028-T030; free-tier deployment and final evaluation remain F006 |
| QR-035 (conditional, F006-owned) | T031; separate MCP deployment is not planned |
| QR-038 (supporting F006) | T005, T008, T020, T029; final application-start and deployment gates remain F006 |

F002 does not independently verify F003 orchestration, F004 workflows, F005 UI, or F006
deployment, complete application-start behavior, evaluation, and submission.
