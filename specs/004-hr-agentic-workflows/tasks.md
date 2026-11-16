# Tasks: HR Agentic Workflows

**Input**: Approved design documents in `specs/004-hr-agentic-workflows/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/workflows.md`, and `quickstart.md`

**Tests**: Deterministic acceptance, provider-adapter, and MCP integration tests are required by the approved plan and this task request. No routine test requires live model credentials.

**Organization**: User-story phases remain the primary organization. The requested milestones map to the Spec Kit phases as follows: Milestone 1 is Foundational; Milestones 2 and 3 are User Stories 1 and 2; Milestone 4 is User Story 3 plus final cross-cutting validation.

**Closure status**: Implementation is conditionally complete: T001-T020 are complete, but
T021 remains open because the hosted CI matrix and required live workflow acceptance are
not verified. The recorded limitations below are not a claim of full F004 acceptance.

## Implementation Strategy

- Reuse F003's bounded sequential agent loop, response vocabulary, MCP discovery, trace events, citations, failure handling, and proposal-bound confirmation.
- Reuse F002's employee, PTO, compliance, and unsent-draft tools and F001 policy retrieval. Do not add a workflow engine, tool, service, dependency, persistence, or evaluation framework.
- Deliver Milestone 1 before workflow-specific changes. Then complete PTO before remote-work because both extend the same agent prompt and acceptance suite.
- Keep provider tests deterministic with mocked Groq responses. Verify the same-completion disposition mapping and unchanged native tool-call path; do not make routine tests depend on a live provider. Before Milestone 1 is considered complete, perform a separate manual compatibility checkpoint against the configured provider.
- F004 supplies reproducible scenarios for QR-032 and workflow-specific documentation for QR-047. F005 retains ownership of its grader-facing interface; F006 retains project-wide evaluation and final-demo deliverables.

## Phase 1: Setup

**Purpose**: Reuse the existing Python project, pytest/Ruff configuration, MCP harness, synthetic data, and CI matrix. No initialization, dependency, or infrastructure task is required.

---

## Phase 2: Foundational — Milestone 1: Completion Disposition

**Purpose**: Add the minimal optional completion disposition and record it through the existing completion event without changing the public `AgentResponse` shape or status vocabulary. This phase blocks both workflow stories.

- [X] T001 [P] Add mocked Groq-adapter tests for a final answer carrying `human_review_recommended` in the same provider completion, unchanged native tool-call handling, default-`None` compatibility, and rejection of unsupported disposition values in `tests/unit/test_agent_llm.py` (FR-010; QR-020).
- [X] T002 [P] Add trace tests for an optional completion-event `disposition`, existing `partial` outcome, omission when the value is `None`, and privacy-safe event contents in `tests/unit/test_agent_trace.py` (FR-010; QR-020).
- [X] T003 Add the optional typed `final_disposition: Literal["human_review_recommended"] | None = None` field to `LLMCompletion` in `src/hr_agent/types.py`; leave `AgentResponse` unchanged (FR-010; QR-020).
- [X] T004 Update `GroqLLMClient.complete` to use the configured Groq provider's supported structured final-output representation and map/validate its answer plus disposition in one completion in `src/hr_agent/llm.py`; preserve native tool-call parsing, reject invalid non-`None` values explicitly, and do not issue an additional completion (FR-010; QR-020).
- [X] T005 Update `HRAgent` final-completion handling in `src/hr_agent/agent.py` so the final answer and disposition are produced together, a set disposition requires an explicit human-review recommendation, the public status remains `partial`, and the existing completion event records only the allowlisted disposition (FR-010; QR-020).
- [X] T006 Preserve the `None` default in scripted completions in `tests/unit/agent_orchestration_helpers.py` so existing controlled callers remain compatible (FR-010; QR-020).
- [X] T007 Document the optional internal completion field and optional completion-event member in `specs/003-agent-orchestration/contracts/python-interface.md` and `specs/003-agent-orchestration/data-model.md`, without changing the public response contract (FR-010; QR-020).
- [X] T008 Run the focused provider-boundary and trace regression tests in `tests/unit/test_agent_llm.py` and `tests/unit/test_agent_trace.py`, plus the existing stdio MCP integration in `tests/integration/test_agent_mcp.py`; verify successful MCP calls can lead to the typed disposition trace, use no additional model call, and do not alter tool-call turns (FR-010; QR-020).

**Checkpoint**: Existing callers that omit the optional field retain their behavior; the controlled insufficient-evidence completion can carry the typed disposition and matching answer in one completion. In addition to mocked adapter tests, manually verify that the configured live provider can return the disposition in the same completion while preserving native tool calls before considering Milestone 1 complete. This checkpoint is not part of routine CI.

**Milestone 1 evidence — FR-010 / QR-020**:

- The mocked provider tests validate application-side JSON envelope mapping, omitted-disposition compatibility, invalid values, one-completion disposition mapping, and unchanged native tool-call request/turn handling. Provider-enforced JSON mode is omitted because Groq rejects it alongside tools.
- The trace tests and stdio MCP integration test verify successful tool evidence can lead to a `partial` response and allowlisted completion-event disposition. They also verify that `AgentResponse` has no new disposition field and that answer text/private data are not persisted in traces.
- Verification: `.venv\Scripts\python -m pytest tests\unit tests\test_agent_acceptance.py tests\integration\test_agent_mcp.py tests\integration\test_agent_provider.py -q` — 69 passed, 1 skipped. The skip is the opt-in live-provider smoke test. Ruff on all modified Python files passed.
- **Live-provider checkpoint passed:** The opt-in provider test passed with Groq `openai/gpt-oss-20b`, using native tool selection, the synthetic stdio MCP policy search, and a validated final JSON envelope containing `human_review_recommended`. A separate synthetic live `HRAgent` run verified a successful policy-search call, cited evidence, a human-review recommendation, `partial` status, and the allowlisted trace disposition. Tool traces retain argument names and output summaries, not raw arguments or results. This checkpoint is not part of routine CI; prompt-based JSON does not provide a provider-enforced format guarantee.
- These results verify the F003 completion/trace foundation only; they do not claim full F004 workflow acceptance or completion of later milestones.

---

## Phase 3: User Story 1 — Get PTO Request Guidance (Priority: P1) — Milestone 2

**Goal**: Combine synthetic employee profile, point-in-time PTO balance, and cited policy evidence; clarify missing information; provide an unsent manager draft only when explicitly requested.

**Independent Test**: Run deterministic cases for `TEST-001`, `TEST-002`, and `TEST-003`, then exercise profile, balance, and policy search through the existing stdio MCP harness.

- [X] T009 [P] [US1] Add a narrow fictional PTO policy document to `tests/fixtures/mcp/f004-policies/hr-pto.md` for the existing integration harness; keep fixture content separate from the production corpus and leave F001 retrieval behavior unchanged (FR-002, FR-003, FR-009, FR-013; QR-019, QR-032).
- [X] T010 [P] [US1] Add deterministic PTO acceptance cases in `tests/test_f004_workflows.py` for profile/balance/policy grounding, the `as_of` date, missing PTO versus a found zero balance, missing employee ID before lookup, and an ambiguous employee name or identifier that selects no record, requests a valid employee ID before employee-specific lookups or claims, and introduces no name-search or identity-resolution capability; also cover missing dates or hours, insufficient evidence, unavailable-tool failure without a success-shaped answer, explicit-only draft creation, and no projected-balance or approval claims (FR-001-FR-005, FR-009, FR-011, FR-013; QR-019, QR-021, QR-022, QR-032).
- [X] T011 [US1] Add a controlled-LLM PTO scenario to the actual stdio MCP integration tests in `tests/integration/test_f004_workflows_mcp.py`; use the fixture from T009 and verify existing profile, PTO, and policy-search schemas/results, sequential result propagation, returned citation, and balance date without requiring a globally fixed call order (FR-001-FR-003, FR-009-FR-011, FR-013; QR-019, QR-021, QR-032).
- [X] T012 [US1] Add only the PTO-specific guidance needed by `HRAgent` in `src/hr_agent/agent.py`; require profile, balance, date, and policy evidence when relevant, distinguish missing from zero and available from projected balance, and avoid claims of submission, approval, exception, or legal entitlement (FR-001-FR-003; QR-019).
- [X] T013 [US1] Run the PTO acceptance and stdio integration tests in `tests/test_f004_workflows.py` and `tests/integration/test_f004_workflows_mcp.py`; verify the explicitly requested draft follows existing confirmation behavior, remains unsent, and is not represented as a submitted request (FR-005, FR-012; QR-022).

**Checkpoint**: PTO guidance is independently reproducible with fixed fixtures and actual MCP integration, including missing-record and safe-draft outcomes.

**Milestone 2 evidence**:

- FR-001-FR-005, FR-009, FR-011-FR-013 / QR-019, QR-021, QR-022, QR-032: deterministic scripted cases cover grounded results and their propagation, point-in-time balance, missing versus zero, missing or ambiguous identity, missing request and draft details, insufficient evidence, tool failure, and unsent confirmation. The actual stdio MCP scenario verifies profile, balance, policy evidence and citation. The F004 fixture is isolated from the pinned F002 compliance-policy corpus and copied into the temporary integration corpus.
- Targeted pytest: 102 passed; Ruff on modified Python files passed. A separate synthetic live-provider PTO run successfully used all three MCP tools and returned the balance, date and PTO citation without a draft. An earlier live run failed an exact balance/date assertion and another returned `llm_request_failed`; their causes remain unverified. Scripted cases verify orchestration under controlled model selections, not guaranteed model compliance.
- QR-019 remains incomplete until remote work is delivered; QR-032 remains partially F004-owned and F005 owns the grader-facing interface. Full workflow trace and documentation review remain in Milestone 4.

---

## Phase 4: User Story 2 — Get Remote-Work Guidance or Escalation (Priority: P1) — Milestone 3

**Goal**: Combine the employee's current profile with cited location, remote-work, and security evidence; use only the supported prior-approval check; explicitly recommend human review when the evidence cannot establish eligibility.

**Independent Test**: Run controlled remote-work cases for current versus proposed location, supported and incomplete caller-provided approval facts, missing employee-specific security facts, and successful MCP calls with insufficient eligibility evidence.

- [X] T014 [US2] Add deterministic remote-work acceptance cases in `tests/test_f004_workflows.py` for current profile versus proposed arrangement, location/security citations, the supported out-of-state prior-approval check only, exact propagation and unverified treatment of caller facts, indeterminate facts, missing security posture, MCP failure, unsupported or insufficient evidence, and the same-completion human-review disposition when all MCP calls succeed. Include an unsupported international-work request; verify the out-of-state prior-approval tool is not invoked, available policy evidence is cited, and the response recommends human review without claiming eligibility (FR-001, FR-006-FR-009, FR-011, FR-013; QR-019-QR-021, QR-032).
- [X] T015 [US2] Add a controlled-LLM remote-work scenario to the actual stdio MCP integration tests in `tests/integration/test_f004_workflows_mcp.py`; use existing policy/profile/compliance tools and fixed fixtures, then verify the successful-MCP/insufficient-evidence answer has `partial` status and the typed disposition in the existing completion trace (FR-001, FR-006-FR-011, FR-013; QR-019-QR-021, QR-032).
- [X] T016 [US2] Add only the remote-work guidance needed by `HRAgent` in `src/hr_agent/agent.py`; distinguish current location from authorization, never infer device/network/account security, constrain the compliance tool to its supported check, and direct unresolved eligibility to human review (FR-001, FR-006-FR-008; QR-019, QR-021).
- [X] T017 [US2] Run the remote-work acceptance and stdio integration tests in `tests/test_f004_workflows.py` and `tests/integration/test_f004_workflows_mcp.py`; verify the successful-MCP/insufficient-evidence answer has `partial` status and the typed disposition appears in the existing completion trace (FR-001, FR-006-FR-011, FR-013; QR-019-QR-021, QR-032).

**Checkpoint**: The supported compliance conclusion remains narrow and caller assertions remain unverified; unknown eligibility is not converted into a definitive decision.

**Milestone 3 evidence**:

- FR-001, FR-006-FR-011, FR-013 / QR-019-QR-021, QR-032: controlled scenarios cover
  profile versus proposed location, policy and security citations, unchanged caller facts,
  indeterminate approval, international work, failures, and human-review disposition.
  Stdio MCP integration verifies actual profile, policy, and supported compliance calls,
  exact approval arguments, `partial` status, and the disposition trace. The synthetic
  security fixture is isolated from the pinned F002 baseline and production corpus.
- Targeted pytest: 109 passed; Ruff on modified Python files passed. Scripted completions
  verify orchestration under controlled selections, not guaranteed provider compliance.
- One synthetic live PTO run returned `answered`, used the profile, balance and policy
  tools, returned a PTO citation, and made no draft call; its safe classifier did not
  observe the balance/date wording indicators, so the earlier balance/date assertion risk
  remains unresolved. One live remote-work run failed with a provider `RateLimitError`
  before a workflow result could be checked. This is another provider-failure occurrence;
  neither the earlier `llm_request_failed` cause nor live remote acceptance is resolved.

---

## Phase 5: User Story 3 — Inspect Workflow Evidence and Outcomes (Priority: P2) — Milestone 4

**Goal**: Reproduce both workflows and compare observable, privacy-safe traces and documented expected outcomes without requiring a fixed tool sequence.

**Independent Test**: Run the documented acceptance and MCP integration scenarios, inspect ordered tool/evidence/completion events, and verify escalation and failure behavior without exposing raw records or model reasoning.

- [X] T018 [US3] Run both workflow acceptance and integration scenarios, inspect the ordered and privacy-safe traces in `tests/test_f004_workflows.py`, and run existing failure/action-safety regressions in `tests/unit/test_agent_errors.py`, `tests/integration/test_agent_mcp.py`, and `tests/unit/test_agent_confirmation.py`; verify evidence references, answer basis, clarification/escalation or failure outcomes, and that unsupported email-sending, approval, or record-update actions are not completed (FR-010-FR-013; QR-020-QR-022).
- [X] T019 [US3] Reconcile representative call sequences, fixed inputs, expected evidence, missing-data behavior, escalation outcomes, and validation commands with `specs/004-hr-agentic-workflows/contracts/workflows.md` and `specs/004-hr-agentic-workflows/quickstart.md`; retain that sequences are representative, QR-032 is F005-facing, and QR-047's final project-wide documentation remains F006-owned (FR-013-FR-014; QR-032, QR-047).
- [X] T020 [US3] Verify the functional-requirement and Quantic-requirement coverage tables in `specs/004-hr-agentic-workflows/tasks.md` against `specs/004-hr-agentic-workflows/spec.md`, `specs/004-hr-agentic-workflows/plan.md`, and the acceptance/integration evidence; report any requirement without implementation or verification coverage before completion (FR-001-FR-014; QR-019-QR-022, QR-032, QR-047).

**Final acceptance risk follow-up**: In a separate manual live-provider check using only
synthetic data, exercise missing and ambiguous employee identity and a PTO guidance request
without an explicit draft request. Verify no employee-specific tool is called before a valid
ID is supplied, clarification is requested, and no draft tool is called without a request.
Record actual calls and outcomes without raw input, credentials or employee data. Scripted
tests alone do not guarantee model compliance. Also record whether the earlier live PTO
balance/date assertion failure or `llm_request_failed` recurs; do not treat a later pass as
proof that their causes are resolved. These checks are manual and are not routine CI.

**Earlier final checkpoint evidence and gaps** (subsequent results are recorded below):

- T018: 35 targeted workflow, MCP, error, confirmation, and action-safety tests passed;
  workflow trace assertions check ordered tools, allowlisted summaries, source references,
  answer basis, and exclusion of fixture values and answers.
- Local full pytest: 397 passed, 1 skipped (opt-in provider test); repository-wide Ruff and
  application imports passed on Windows. The existing Ubuntu/Windows CI matrix has no run
  for this branch and no open PR; actual CI remains unverified, so T021 remains open.
- A synthetic live PTO attempt called profile, balance, and policy tools successfully and
  cited `HR-005` without calling a draft tool. The limited balance/date indicators did not
  match; the actual answer was not retained, so an omission cannot be distinguished from
  different wording. A later actual answer stated `40.0 PTO hours available as of
  2026-01-01`, showing that an exact `40 hours` string assertion would be too restrictive.
  That later run called only the balance tool, so it did not verify the full PTO workflow.
  Earlier PTO assertion and provider failures remain unresolved.
- A live ambiguous-identity request made no employee-specific call but returned an `error`
  with no request for an employee ID, failing FR-004. A separate controlled reproduction
  shows that a final completion asking for an ID is replaced by the `missing_policy_evidence`
  fallback when no citations or limitations exist; the live model's original completion was
  not retained, so that reproduction does not prove which live branch caused the failure.
- A live remote-work attempt returned provider `RateLimitError` (HTTP 429). A later attempt
  completed but its diagnostic report failed with `UnicodeEncodeError`, leaving its result
  unverified. A further attempt invoked profile, compliance, and policy tools but ended with
  provider `BadRequestError` (HTTP 400) and `llm_request_failed`; its cause is unverified.
  The earlier manual check made eight PTO provider requests, including a discarded run due
  to a harness-reporting error, and one rate-limited remote provider request.
- QR-019 and FR-002/FR-006-FR-008 have controlled and MCP evidence, but live PTO
  composition and live remote workflow remain open. QR-021/FR-004 have controlled
  identity cases, but the live ambiguous-identity check failed. QR-022/FR-005 has
  controlled confirmation and one live no-draft observation; model-guided selection is
  not guaranteed. QR-020 has controlled privacy/trace evidence and prior live disposition
  evidence, not a verified live remote-work trace. QR-032 remains partially F004-owned
  and requires F005's grader interface; QR-047's final project-wide documentation remains
  F006-owned. Do not mark F004 fully accepted on this evidence.

**Targeted stabilization evidence**:

- The application now maps a validated final employee-ID clarification signal to the existing
  clarification status and fixed prompt; unsupported answers still fail the missing-evidence
  check, and tool failures retain precedence. Controlled tests cover the signal, invalid and
  contradictory values, and policy search before clarification. This does not enforce
  employee-ID binding on model-selected tool calls; the separately approved binding is
  documented below.
- PTO assertions compare the available numeric balance and its associated as-of date, including
  equivalent decimal/date representations, while preserving profile, balance, policy-search,
  citation, and request-process checks. Live end-to-end PTO acceptance remains unverified.
- Groq HTTP 400 failures now record allowlisted request and matching metadata in the existing
  error trace. Mocked tests cover matched/mismatched IDs and exclusion of provider messages and
  private data. The earlier HTTP 400 cause is still unknown; no live diagnostic has reproduced it.
- Targeted pytest: 71 passed; Ruff on modified Python files passed. These checks do not replace
  the outstanding live negative paths, live remote workflow, or T021 CI verification.

**Employee-ID binding**: Employee-specific profile and PTO tool calls now require a nonblank
caller-supplied `context.employee_id` and reject mismatched model-selected IDs before dispatch.
IDs in free-text requests alone are not authoritative. This is an identity-consistency check,
not authentication or authorization; policy-only workflows remain independent of it. Targeted
agent, workflow, and stdio MCP tests passed (142 tests), including mismatches blocked before
MCP dispatch; Ruff passed on modified Python files. Live workflow acceptance and the prior
provider failures remain unverified.

---

## Phase 6: Polish and Cross-Cutting Validation

**Purpose**: Complete acceptance, regression, traceability, and platform validation without changing the existing CI design.

- [ ] T021 Run the F004 acceptance and MCP integration scenarios, the repository pytest suite, and Ruff; verify the existing Ubuntu and Windows matrix in `.github/workflows/ci.yml` passes, fixing only F004-related failures and adding no CI infrastructure or dependencies (FR-001-FR-014; QR-019-QR-022, QR-032, QR-047).

**Conditional closure review**:

- Local verification: full pytest **476 passed, 5 skipped**; one opt-in provider smoke
  and four opt-in F004 live cases were disabled. Repository-wide Ruff and staged and
  unstaged Git diff checks passed. The staged changes and pinned F002 baseline were
  preserved. Hosted Ubuntu/Windows CI has not run for this branch; T021 remains open.
- Automated scripted acceptance and actual stdio MCP tests exercise both workflows,
  citations, identity binding, missing data, failures, privacy-safe traces, and unsent
  draft confirmation. Scripted model outputs do not establish live model compliance.
- The latest live PTO attempt successfully executed profile, balance, and policy search,
  returned a relevant citation and `answered` status, and made no draft call. The
  balance/date evaluator did not match; the retained evidence cannot distinguish
  equivalent wording from an omitted or incorrect date. Complete live PTO acceptance
  remains unverified. Earlier PTO assertion and provider `llm_request_failed` failures
  also remain unexplained.
- Live remote-work acceptance remains unverified after HTTP 429 and HTTP 400 provider
  failures; the HTTP 400 cause is not established. An intervening reporting
  `UnicodeEncodeError` also left that run unverified. These failures may prevent
  end-to-end demonstrations and must not be treated as resolved.
- After stabilization, one live ambiguous-identity scenario returned
  `clarification_needed` without employee-specific MCP calls. The earlier failed live
  scenario's original completion was not retained, so its exact cause remains unproven.
  One PTO run had no draft call; the separate live explicit-only drafting negative path
  was not completed. Model-guided clarification and draft selection are not guaranteed
  by scripted tests.
- Some traces contain multiple completion events, including in the pre-F004 agent
  implementation; consumers must not assume one event per request. The approved
  privacy-safe operational trace contract is unchanged.
- QR-019 has deterministic and real-MCP workflow evidence, but not verified live
  completion of both workflows. QR-020-QR-022 retain F003-level verification with
  additional F004 automated coverage; F004 live gaps remain as noted. F004 provides
  scenarios and workflow documentation, while QR-032 remains F005-owned and QR-047
  remains F006-owned. No downstream interface, deployment, or final demo is claimed.

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No work; the project, test tooling, fixtures, and CI already exist.
- **Foundational (Phase 2 / Milestone 1)**: Complete before either workflow story because both rely on the shared completion and trace boundary.
- **User Story 1 (Phase 3 / Milestone 2)**: Starts after the foundation. The PTO fixture and deterministic test cases (T009-T010) can be prepared in parallel; add the MCP scenario before prompt changes; run integration after the prompt and fixture are ready.
- **User Story 2 (Phase 4 / Milestone 3)**: Starts after the foundation and follows User Story 1 because both modify the same prompt and acceptance/integration files. Add deterministic and MCP scenarios (T014-T015) before the prompt change; T017 verifies the integrated behavior.
- **User Story 3 (Phase 5 / Milestone 4)**: Follows both workflows so trace and documentation checks reflect actual acceptance behavior.
- **Polish (Phase 6 / Milestone 4)**: Follows all stories and traceability review.

### Task Dependencies

- T001 and T002 are independent test-first changes; T003 follows both.
- T004 and T006 depend on T003 and can proceed in parallel because they change separate files.
- T005 depends on T003-T004; T007 follows the finalized internal contract. T008 follows T004-T006.
- T009 and T010 are independent; T011 follows T009; T012 follows T010-T011; T013 follows T011-T012.
- T014 follows the foundation and PTO phase; T015 follows T014; T016 follows T014-T015; T017 follows T016.
- T018-T020 follow both workflow phases; T021 follows the entire task list.

## Parallel Execution Examples

### Milestone 1

```text
T001 in tests/unit/test_agent_llm.py
T002 in tests/unit/test_agent_trace.py
```

### Milestone 2

```text
T009 in tests/fixtures/mcp/f004-policies/hr-pto.md
T010 in tests/test_f004_workflows.py
```

These pairs touch different files and have no prerequisite changes. Do not parallelize tasks that edit `src/hr_agent/agent.py`, `tests/test_f004_workflows.py`, or `tests/integration/test_f004_workflows_mcp.py` across milestones.

## Requirements-to-Task Coverage

### Functional Requirements

| Requirement | Implementation/reuse and verification tasks |
|---|---|
| FR-001 | T010-T013, T014-T017 |
| FR-002 | T010-T013 |
| FR-003 | T010-T013 |
| FR-004 | T010 |
| FR-005 | T010, T013 |
| FR-006 | T014-T017 |
| FR-007 | T014-T017 |
| FR-008 | T014-T017 |
| FR-009 | T009-T013, T014-T017 |
| FR-010 | T001-T008, T014, T017-T018 |
| FR-011 | T011, T014-T015, T017-T018 |
| FR-012 | T010, T013, T018 |
| FR-013 | T009-T010, T011, T013-T015, T017-T021 |
| FR-014 | T019-T021 |

### Assigned Quantic Requirements

| Requirement | Tasks and planned acceptance evidence | F004 ownership |
|---|---|---|
| QR-019 | T009-T013 and T014-T017: both workflows combine synthetic employee data, policy evidence, and existing sequential MCP tools. | F004 implementation and verification |
| QR-020 | T001-T008 and T014, T017-T018: same-completion typed disposition, unchanged native tool calling, existing completion event, partial outcome, and privacy assertions. | F004 adds the minimal internal completion/trace extension |
| QR-021 | T010-T011, T014-T015, T017-T018: missing ID/PTO, incomplete or unsupported evidence, indeterminate facts, and MCP failure outcomes. | F004 workflow-specific acceptance; reuse F003 error handling |
| QR-022 | T010, T013, and T018: explicit-only unsent draft, existing confirmation, and refusal of unsupported actions. | F004 verifies workflow safety; F003 remains the capability owner |
| QR-032 | T010-T011, T014-T015, T018-T021: fixed synthetic requests and reproducible expected outcomes. | Partial: F004 supplies scenarios; F005 owns the grader-facing interface |
| QR-047 | T019-T021: representative sequences, inputs/outputs, evidence, and clarification/escalation outcomes are documented and checked. | Partial: F004 supplies workflow documentation; F006 owns final project-wide design documentation and demo deliverables |

**Coverage result**: All F004 FR-001-FR-014 and assigned QR-019, QR-020, QR-021, QR-022, QR-032, and QR-047 have implementation/reuse and verification tasks, but planned coverage does not by itself establish live acceptance. The final checkpoint evidence above identifies remaining verification gaps. No F005 interface task or F006 evaluation/final-demo task is included.

## MVP and Scope Check

- **MVP**: Complete Milestones 1 and 2 first, yielding the compatible disposition foundation and independently tested PTO workflow.
- **Required after MVP**: Milestone 3 delivers the second required workflow; Milestone 4 verifies shared traceability, privacy, reproducibility, documentation, and CI.
- **Excluded**: New orchestration engine, fixed workflow graph, tools, services, databases, dependencies, broad outcome taxonomy, routine live-model test requirement, F005 UI/API, and F006 evaluation or final-demo work.
