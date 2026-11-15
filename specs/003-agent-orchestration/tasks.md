# Tasks: Agent Orchestration

**Branch**: `003-agent-orchestration`  
**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [python-interface.md](contracts/python-interface.md),
and [quickstart.md](quickstart.md).

**Scope**: Generate tasks for Feature 003 only. Reuse the asynchronous Feature 002 MCP client.
Do not add direct Feature 001 calls, new MCP business tools, persistent state, or an
orchestration framework.

**Task count**: 18

## Checklist Format

Each task follows `- [ ] T### [P?] [US#?] Description with file path`.
`[P]` appears only where the task can proceed independently on separate files. Story tags map
to the five stories in `spec.md`: `[US1]` intent/tool selection, `[US2]` MCP discovery and
invocation, `[US3]` failures and clarification, `[US4]` grounded responses and traces, and
`[US5]` safe actions.

## Milestone 1: Working Vertical Slice (6 tasks)

**Goal**: Prove configured-model tool calling early, then initialize the async agent, discover
the MCP catalog, call policy search through MCP, and return a grounded answer.

**Independent test criteria**: A live configured provider/model can complete one tool-call
round trip; deterministic tests can exercise the same interface without network access; the
agent discovers the F002 catalog and answers a policy-only request using only
`search_policy_documents`.

- [X] T001 [P] [US2] Add an opt-in provider capability test in `tests/integration/test_agent_provider.py` and run it against the configured provider/model; verify a native tool call with schema-valid arguments, feed a tool result back, and receive a final response. If credentials or provider access are unavailable, report the validation blocked instead of substituting a mock. **Live verification:** user-reported run with Groq `openai/gpt-oss-20b` passed (1 test, 2.95s).
- [X] T002 [P] Create the `src/hr_agent/` package foundation in `src/hr_agent/__init__.py`, `src/hr_agent/config.py`, `src/hr_agent/types.py`, and `src/hr_agent/errors.py`; define the async interface types, environment-backed model/token/MCP settings, and explicit error types from the planning contract.
- [X] T003 [US2] Implement the minimal async Groq provider adapter in `src/hr_agent/llm.py`; convert discovered MCP schemas to native tool definitions, request `n=1` and `parallel_tool_calls=False`, and cover tool-call/result serialization with deterministic tests in `tests/unit/test_agent_llm.py`.
- [X] T004 [US2] Implement asynchronous `HRAgent` initialization and per-request MCP discovery in `src/hr_agent/agent.py` using the existing `hr_mcp.client.MCPClient`; validate discovered schemas and cover readiness/catalog behavior plus MCP connection or discovery failure in `tests/unit/test_agent_discovery.py`, verifying the agent reports the failure and does not silently fall back to direct Python tool invocation.
- [X] T005 [US1] Implement the one-tool policy vertical slice in `src/hr_agent/agent.py`: let the LLM select `search_policy_documents`, invoke it through `MCPClient.call()`, and return a response grounded in its evidence; cover policy-only routing and citations with deterministic tests in `tests/unit/test_agent_vertical_slice.py`.
- [X] T006 [US2] Add a protocol integration test in `tests/integration/test_agent_mcp.py` using the existing Feature 002 stdio server; verify all six tool names/schemas are discovered, the SC-001 minimum of four is met, and a policy request invokes `search_policy_documents` through MCP without a direct Feature 001 call.

## Milestone 2: Core Orchestration (4 tasks)

**Goal**: Support sequential multi-tool work, structured lookups, clarifications, evidence
limitations, and explicit partial failures.

**Independent test criteria**: Deterministic LLM/MCP doubles prove at least two representative
multi-step sequences, missing arguments produce clarification rather than guesses, conflicting
evidence is reported without invented resolution, and tool failures do not appear successful.

- [X] T007 [US1] Extend the bounded loop in `src/hr_agent/agent.py` to execute one model-selected MCP call per turn, return each structured result to the next LLM turn, and stop at `max_tool_calls`; cover sequential result-dependent behavior and at least two representative multi-step sequences, each combining `search_policy_documents` with at least one existing structured-data MCP tool, in `tests/unit/test_agent_orchestration.py`. Keep Feature 004's dedicated business workflows out of scope.
- [X] T008 [US3] Implement discovered-schema argument validation and missing-context clarification in `src/hr_agent/agent.py`; reject invalid arguments and ask for required identifiers/details instead of guessing, with tests in `tests/unit/test_agent_validation.py`.
- [X] T009 [US4] Implement evidence-grounded synthesis and citation/limitation handling in `src/hr_agent/agent.py`; cite policy claims from `search_policy_documents`, ground structured claims in MCP results, and report absent, incomplete, or conflicting evidence without inventing a resolution, with tests in `tests/unit/test_agent_evidence.py`.
- [X] T010 [US3] Implement MCP tool error, timeout, and valid `not_found`/`indeterminate` handling in `src/hr_agent/agent.py` and `src/hr_agent/errors.py`; do not automatically retry failed MCP tool calls, surface failures clearly, and allow a subsequent user request to initiate a fresh call. Return partial answers only when remaining evidence supports them and test failure, no automatic reissue, and subsequent-request retry behavior in `tests/unit/test_agent_errors.py`.

## Milestone 3: Safety and Hardening (4 tasks)

**Goal**: Complete the existing email-draft confirmation flow, unsupported-action refusal,
observable privacy-safe traces, and remaining error paths.

**Independent test criteria**: Confirmation is bound to the exact draft across requests;
changed drafts need fresh confirmation; no email is sent; unsupported actions are refused; and
traces expose observable choices/outcomes without hidden reasoning or sensitive raw data.

- [X] T011 [US5] Implement the existing `draft_hr_email` proposal/confirmation flow in `src/hr_agent/agent.py` and `src/hr_agent/types.py`; carry the pending proposal through caller context, require explicit action-specific confirmation before reporting the simulated outcome, and require reconfirmation after material changes, with tests in `tests/unit/test_agent_confirmation.py`.
- [X] T012 [US5] Enforce refusal of actual email sending, approvals, employee-record updates, and unsupported MCP actions at the agent execution boundary in `src/hr_agent/agent.py`; verify requests are refused even when the LLM proposes them in `tests/unit/test_agent_safety.py`.
- [X] T013 [US4] Implement allowlisted operational trace creation in `src/hr_agent/agent.py` and `src/hr_agent/types.py`; record concise intent categories, selected tools, outcome categories, allowlisted argument summaries, tool-result summaries, evidence references, and answer-basis categories. In `tests/unit/test_agent_trace.py`, verify traces exclude credentials, raw employee records, raw user questions, email drafts, internal prompts, and hidden chain-of-thought.
- [X] T014 [US3] Harden request handling in `src/hr_agent/agent.py` and `src/hr_agent/errors.py` for provider failures, multiple tool calls returned in one model turn, exhausted call bounds, and trace persistence errors; surface explicit outcomes and verify each path in `tests/unit/test_agent_hardening.py`.

## Milestone 4: Verification and Delivery (4 tasks)

**Goal**: Verify measurable acceptance criteria, preserve QR traceability, run quality checks on
both supported CI platforms, and keep the usage guide minimal and accurate.

**Independent test criteria**: Acceptance cases meet the specification’s scenario counts;
Ruff and pytest pass in the existing Ubuntu/Windows CI matrix; the quickstart accurately
describes the implemented MCP-only policy path and confirmation behavior; QR coverage has
evidence references and no requirement is marked Verified without evidence.

- [X] T015 Add the deterministic acceptance suite in `tests/test_agent_acceptance.py`; assert SC-002 through SC-010 thresholds (3 policy-only, 3 data lookups, at least 3 representative multi-step requests each combining `search_policy_documents` with at least one existing structured-data MCP tool, 2 clarification cases, 2 evidence-limitation cases, 2 tool-failure cases, trace fields/privacy, confirmation/refusal, and no automatic retry with a subsequent user request able to retry). Extend the actual-protocol integration scenario in `tests/integration/test_agent_mcp.py` to demonstrate successful invocation through `HRAgent` of at least five distinct existing Feature 002 MCP tools; discovery alone does not count. Do not use `get_policy_section` as an alternate policy-evidence path, and use `draft_hr_email` only within the approved confirmation flow. Keep Feature 004's dedicated business workflows out of scope; reuse focused test fixtures rather than duplicating their unit-test logic. Reference T006 for SC-001 discovery.
- [X] T016 [P] Extend the existing cross-platform workflow in `.github/workflows/ci.yml` to import the new `hr_agent` package and run the F003 MCP discovery/integration test on both existing Ubuntu and Windows matrix jobs; retain Ruff and full pytest execution without requiring live provider credentials.
- [X] T017 [P] Update `specs/003-agent-orchestration/quickstart.md` and `specs/003-agent-orchestration/contracts/python-interface.md` to match the implemented async API, environment configuration, MCP discovery/invocation, deterministic test commands, and caller-carried email confirmation behavior. Also reconcile the feature overview in `README.md` and `00-SUMMARY.md`.
- [X] T018 Review the QR-to-task mapping in this file against `docs/requirements/traceability.md`; update the assigned QR-018, QR-020, QR-021, QR-022, and QR-026 rows using implementation and test evidence. Run `python -m ruff check .`, `python -m pytest`, and `git diff --check`; report local and hosted CI evidence. Do not mark requirements Verified without supporting evidence. Current-branch Ubuntu and Windows GitHub Actions results reviewed and passed.

## Requirements Traceability

| Quantic requirement | Coverage tasks | Verification |
|---|---|---|
| QR-018 (assigned to F003) | T003-T005, T007, T009, T015 | Provider-backed tool calling, policy and structured selection, sequential multi-step tests, grounded synthesis, acceptance thresholds. |
| QR-020 (assigned to F003) | T013, T015 | Allowlisted argument/result summaries, trace field and privacy tests, then acceptance inspection. |
| QR-021 (assigned to F003) | T004, T008, T010, T014, T015 | MCP initialization/discovery failure without direct-call fallback; missing-input, invalid-schema, unavailable/failed tool, timeout, partial-result, and acceptance tests. |
| QR-022 (assigned to F003) | T011, T012, T015 | Action-bound confirmation, changed-proposal reconfirmation, unsent labeling, refusal, and acceptance tests. |
| QR-026 (assigned to F003) | T004, T006, T015 | Async MCP discovery and actual protocol invocation; no direct server-function or Feature 001 calls. |
| QR-019 (F004-owned; supported by F003) | T007, T015 | F003 verifies general multi-step orchestration; dedicated PTO and remote-work workflows remain in F004. |
| QR-015 / QR-016 (F001-owned; supported by F003) | T005, T009, T015 | Policy citation, unsupported-question, and limitation behavior. |
| QR-027 (F002-owned; supported by F003) | T006, T017 | Document and verify Feature 003's MCP client integration; F002 retains server/tool documentation ownership. |
| QR-030 (F005-owned; supported by F003) | T002, T005, T009, T013 | Structured response carries answers, citations/snippets, limitations, and concise tool traces for the consuming interface. |
| QR-041 / QR-042 (F006-owned; supported by F003) | T009, T013, T015 | Groundedness/citation evidence, selected-tool outcomes, workflow results, clarification, and action-safety outcomes remain observable for F006 evaluation. |

No task adds the dedicated F004 business workflows, a new MCP tool, direct retrieval, persistent
confirmation storage, or a new orchestration dependency.

## Milestone 1 Execution Evidence

| Requirement | Milestone 1 evidence |
|---|---|
| QR-018 | T003/T005 deterministic tests verify native tool-call serialization and an LLM-selected policy search; T006 verifies the agent returns a grounded response from the MCP result. The user-reported T001 live test passed with Groq `openai/gpt-oss-20b`, validating native tool selection, discovered MCP schema-compatible arguments, and a final response after the MCP result. |
| QR-021 | T004 tests MCP discovery failure reporting, invalid schemas, and readiness checks. |
| QR-026 | T006 runs HRAgent against the existing Feature 002 stdio server, verifies all six discovered tool schemas and the four-tool minimum, and observes `search_policy_documents` invoked over MCP. The Feature 003 package has no direct Feature 001 import or retrieval call. |
| QR-015 / QR-016 | T005/T006 verify policy evidence citations and explicit handling when search returns no supporting evidence. |

Verification run from the project `.venv`: targeted Milestone 1 tests **12 passed**; actual
stdio MCP integration test **1 passed**; complete pytest suite **318 passed, 1 skipped, 0
failed**; Ruff **passed**. That earlier suite skipped the opt-in live provider check; the user
subsequently ran it with Groq `openai/gpt-oss-20b` and reported **1 passed in 2.95s**.
These results do not mark the full Feature 003 requirements Verified.

## Milestone 2 Execution Evidence

| Task | Implementation and verification evidence |
|---|---|
| T007 | `tests/unit/test_agent_orchestration.py` exercises two LLM-selected sequential sequences: employee-profile lookup then policy search, and policy search then employee-profile lookup. Each result is passed to the following model turn; discovered schemas are used and execution remains within the configured call bound. |
| T008 | `tests/unit/test_agent_validation.py` verifies that a missing employee identifier yields a clarification without an MCP call and that schema-invalid arguments are rejected before invocation. |
| T009 | `tests/unit/test_agent_evidence.py` verifies policy candidate citations and structured-result references are aggregated, conflicting candidate excerpts are both supplied to synthesis, and missing policy or employee evidence is reported as a limitation rather than a supported finding. |
| T010 | `tests/unit/test_agent_errors.py` verifies transport failures and timeouts are surfaced, a repeated failed call is not reissued within the request, and a new request can retry. Failure envelopes are explicitly marked as errors and are not represented as successful MCP results. |

Verification from the project `.venv`: focused Milestone 2 and vertical-slice tests
**13 passed**; complete pytest suite **334 passed, 1 skipped, 0 failed** with
`AGENT_RUN_PROVIDER_SMOKE=0`; `python -m ruff check .` **passed**. The skipped test is the
opt-in live provider test; no live provider call was made. Pylance syntax checks reported no
syntax errors in the changed Python files. These results do not mark the full Feature 003
requirements Verified.

## Milestone 3 Execution Evidence

| Requirement | Evidence |
|---|---|
| QR-022 | T011 confirmation tests cover proposal-specific confirmation, cancellation, changed and forged proposals, and distinct proposals. T012 tests reject model-proposed sending, approvals, record updates, and ticket updates without MCP invocation. The existing MCP draft is unsent; no confirmation state is stored. |
| QR-020 | T013 tests inspect returned and persisted traces for draft, policy, and employee requests; they verify tool and outcome summaries and source references without raw questions, employee records, credentials, or draft text. |
| QR-021 | T014 tests cover provider failure, multiple model tool calls, and trace-write failure; existing focused tests cover discovery failure, invalid arguments, exhausted bounds, and unavailable tools. The MCP client timeout code is mapped to a timeout and tested. |
| QR-026 | Draft preparation invokes the existing discovered tool through `MCPClient.call`; actual-protocol multi-tool acceptance remains T015. |

Focused safety/error tests: **15 passed**. Full pytest with `AGENT_RUN_PROVIDER_SMOKE=0`:
**346 passed, 1 skipped**; Ruff and `git diff --check` passed. No live provider call was made.
The confirmation integrity key is held in the agent instance only; replacing that instance
requires preparing a new proposal. These results do not mark Feature 003 requirements Verified;
after Phase 4A, T017-T018 remain outstanding.

## Milestone 4A Execution Evidence

| Task | Implementation and verification evidence |
|---|---|
| T015 | `tests/test_agent_acceptance.py` adds deterministic cases for 3 policy-only requests, 3 structured-data lookups, 3 policy-plus-data sequences, 2 missing-identifier clarifications, 2 evidence limitations, 2 tool failures, trace fields/privacy, confirmation/refusal, and suppressed same-request retry followed by a successful new request. `tests/integration/test_agent_mcp.py` invokes `search_policy_documents`, `lookup_employee_profile`, `check_pto_balance`, `check_policy_compliance`, and `draft_hr_email` through `HRAgent` and the real Feature 002 stdio MCP client. The draft is prepared and confirmed through the approved flow; the response states no email was sent. The test verifies all five protocol calls and sequential tool-result feedback. |
| T016 | `.github/workflows/ci.yml` now imports `hr_agent` and runs the F003 MCP integration test explicitly in the existing Ubuntu/Windows matrix, retaining Ruff and full pytest. Routine pytest steps set `AGENT_RUN_PROVIDER_SMOKE=0`. Local Windows validation: package import passed; focused acceptance/orchestration/protocol tests **22 passed**; full pytest **365 passed, 1 skipped, 0 failed**; Ruff and `git diff --check` passed. At the end of Phase 4A, hosted Actions results had not yet been reviewed. |

These results verify the listed acceptance scenarios locally; they do not constitute hosted CI
evidence. At the end of Phase 4A, hosted CI had not yet been reviewed; Phase 4B review below
found no run for the current branch.

## Milestone 4B Execution Evidence

| Task | Implementation and verification evidence |
|---|---|
| T017 | `quickstart.md` now documents the asynchronous `HRAgent.create`/`process_request` API, live MCP discovery and sequential execution, the MCP-only `search_policy_documents` policy path, environment defaults including `AGENT_TRACE_PATH`, tuple-to-list conversion for MCP server args, deterministic acceptance/protocol test commands, and the caller-carried confirmation exchange using the same agent instance. `contracts/python-interface.md` now matches the implemented `AgentConfig`, response/status, citation, trace, MCP argument, and confirmation types. The stale architecture descriptions in `README.md` and `00-SUMMARY.md` were corrected to describe LLM-native selection, dynamic MCP discovery, bounded sequential calls, and MCP-only policy retrieval. |
| T018 | Reviewed the QR-to-task mapping and updated only QR-018, QR-020, QR-021, QR-022, and QR-026 in `docs/requirements/traceability.md`; each Verified status has requirement-specific test references plus full-suite evidence. Local Windows validation with `AGENT_RUN_PROVIDER_SMOKE=0`: full pytest **365 passed, 1 skipped, 0 failed**; Ruff **passed**; `git diff --check` **passed**. The skipped test is the opt-in live-provider smoke test. Hosted [Python CI run #8](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/43771066729) corresponds exactly to current branch HEAD `f8dc8559c125ebd34f3ccf3fcad8d36d48f3c7de`. Both Ubuntu and Windows jobs passed Ruff, Feature 003 import, MCP integration (**2 passed**), and full pytest (**365 passed, 1 skipped**); the MCP imports step also passed. Routine CI disabled the opt-in live-provider test. T018 acceptance criteria are met. |

## Dependencies and Execution Order

- **Milestone 1**: T001 and T002 may proceed in parallel. T003 depends on T001's provider
  capability result and T002; T004 depends on T002; T005 depends on T003 and T004; T006 depends
  on T004 and T005.
- **Milestone 2**: Starts after the vertical slice. T007-T010 extend the agent and its focused
  behavior tests; complete them before safety hardening.
- **Milestone 3**: Starts after core orchestration. T011-T014 depend on the response/tool loop
  from Milestones 1-2.
- **Milestone 4**: Starts after Milestone 3. T015 depends on the focused tests; T016 and T017
  can proceed in parallel once interfaces stabilize; T018 is final and requires hosted CI review.

## Parallel Opportunities

```text
Milestone 1: T001 provider capability check || T002 package/config/types foundation
             T003 LLM adapter || T004 MCP initialization/discovery (after T001/T002 as applicable)
Milestone 4: T016 cross-platform CI || T017 quickstart/contract updates
```

## Implementation Strategy

1. **MVP**: Complete Milestone 1 and independently verify the configured model tool-call
   round trip and MCP-backed cited policy response.
2. **Core behavior**: Complete Milestone 2 before adding confirmation and trace hardening.
3. **Safety gate**: Complete Milestone 3 before exposing the agent to F004/F005.
4. **Delivery**: Complete acceptance coverage, CI, documentation, and QR evidence review in
   Milestone 4.

Phase 4B documentation, traceability review, local verification, and hosted Ubuntu/Windows CI
verification are complete. Do not start Feature 004 without explicit authorization.
