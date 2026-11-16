# Implementation Plan: HR Agentic Workflows

**Branch**: `004-hr-agentic-workflows` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-hr-agentic-workflows/spec.md`

## Summary

Deliver the two F004 workflows by adding concise workflow-specific guidance to the existing
`HRAgent` system prompt and verifying it with controlled LLM responses and synthetic MCP
fixtures. Keep dynamic native tool selection, one-tool-per-turn bounded sequential execution,
F002 tool contracts, F001 policy retrieval through MCP, citations, safe email-draft
confirmation, and sanitized traces. Do not add a workflow engine, MCP tool, service, runtime
dependency, persistent data, or F005/F006 deliverable.

The current agent already supports the required calls and generic failure handling. The
feature-specific work is to make the interpretation boundaries explicit (point-in-time PTO;
current location versus proposed-location approval; caller-provided facts are unverified;
unknown security posture requires human review), then verify the two composed workflows.
For a model-generated human-review recommendation, extend the existing LLM completion
boundary with an optional typed `final_disposition`; record its single supported value in the
existing completion trace event. The normal response status vocabulary and public response
shape remain unchanged.

## Technical Context

**Language/Version**: Python 3.11 (`requires-python = ">=3.11,<3.12"`).

**Primary Dependencies**: Existing `hr_agent` implementation, F002 MCP client/server, F001
policy retrieval, and existing Groq adapter. No new runtime or development dependencies.

**Storage**: No F004 storage. Reuse F001's local policy index and F002's read-only synthetic
JSON data. Agent request context and email-draft proposals remain transient/caller-carried.

**Testing**: pytest with `ScriptedLLM`, fake MCP responses, fixed synthetic fixtures, and the
existing stdio MCP integration harness; Ruff for changed Python files. Routine tests require
no model credentials or live model calls.

**Target Platform**: Existing local, single-service Python application and its MCP stdio
boundary; no new deployment target.

**Project Type**: Python agent/application with separately testable RAG and MCP components.

**Performance Goals**: Preserve F003's bounded sequential tool-call limit; no new latency or
throughput target is assigned to F004.

**Constraints**: F001 policy evidence is available only through `search_policy_documents`.
Use only discovered F002 tools and schemas. Keep employee and policy data synthetic. Do not
send email, submit or approve requests, update records, infer security posture, or extend the
existing prior-approval check.

**Scale/Scope**: Two workflows (PTO and remote work), a small set of deterministic acceptance
scenarios, and no new service, persistence, framework, or generalized evaluation system.

## Constitution Check

### Pre-design gate

| Principle/constraint | Status | Plan application |
|---|---|---|
| I. Simplicity First | Pass | Reuse the existing agent loop and tools; add only narrowly scoped workflow instructions and tests. |
| II. Python-First Implementation | Pass | Keep runtime, fixtures, and tests in Python; no other language is needed. |
| III. Modular Separation | Pass | Keep orchestration in `hr_agent`; do not duplicate retrieval, MCP, or UI responsibilities. |
| IV. Grounded AI Responses | Pass | Require profile/PTO claims to come from structured results and policy claims from cited search evidence; preserve unknowns and conflicts. |
| V. MCP-Compliant Tool Integration | Pass | Continue using discovered schemas and `MCPClient.call`; preserve sequential, bounded calls and explicit failures. |
| VI. Synthetic Data and Safe Operations | Pass | Use synthetic fixtures only; retain the unsent draft and existing proposal-bound confirmation. |
| VII. Automated Testing and Reproducibility | Pass | Use deterministic LLM/MCP doubles for routine tests and the existing actual stdio MCP harness for integration coverage. |
| Single-service and free-tier constraints | Pass | No additional service, hosted dependency, or paid resource. |
| Feature ownership | Pass | F004 supplies workflows/scenarios; F005 owns the grader-facing UI/API; F006 owns project-wide evaluation and final demo deliverables. |

### Post-design gate

The selected architecture still passes the constitution gates above: no new external
interface, service, dependency, persistent state, or action capability is introduced. One
additive optional field on the existing internal completion contract supplies the final
disposition without parsing answer text or adding a model call. The same completion carries
the answer and disposition; when the disposition is present, the answer must explicitly
recommend human review. The agent maps that result to the existing `partial` response status
and records the disposition in the existing completion event. This resolves the design gap
for QR-020, FR-010, and SC-007 without adding a public `AgentResponse` field or status.

## Minimum Viable Design

### Required

1. Add workflow-specific instructions to the existing `_SYSTEM_PROMPT` in
   `src/hr_agent/agent.py`:
   - PTO guidance combines the employee profile, the available balance, its `as_of` date, and
     relevant policy evidence; a missing balance is not zero, and an available balance is not
     a projection or approval.
   - Remote-work guidance distinguishes current profile location/arrangement from approval
     for a proposed arrangement. Use `check_policy_compliance` only for the existing
     out-of-state prior-approval check, with caller-provided facts described as unverified.
   - Do not claim employee-specific security posture from policy requirements or synthetic
     profile fields. Identify unsupported eligibility determinations and route them to the
     relevant human reviewer.
   - Preserve missing-ID clarification, evidence limitations, candidate-evidence citations,
     explicit errors, and the existing unsent-draft confirmation behavior.
2. Keep the existing LLM-native tool choice and sequential loop. Do not encode fixed call
   order in code; document representative sequences and allow other valid orders.
3. Add deterministic acceptance coverage for complete and incomplete PTO and remote-work
   cases, plus a stdio MCP integration scenario using the existing fixture harness. Reuse
   existing fixtures and add only the narrow synthetic policy fixture data needed to exercise
   F004 evidence through actual MCP.
4. Extend `LLMCompletion` with
   `final_disposition: Literal["human_review_recommended"] | None = None`. The model emits
   the optional disposition as structured metadata in the same final response as its answer;
   the provider adapter validates and maps it into `LLMCompletion`. Tool-call completions and
   callers/adapters that omit it retain the default `None`. Reject any non-`None` value
   outside the single allowed literal as an explicit invalid completion.
5. On that disposition, preserve the existing public response shape, use the existing
   `partial` status, and add the disposition to the existing completion trace event. The
   answer/disposition pair must be produced together; never infer disposition from prose.
6. Document workflow inputs, representative tool calls, output/evidence expectations, failure
   paths, and the typed disposition contract in the F004 workflow contract and quickstart.

### Necessary supporting work

- Verify the caller receives the balance's `as_of` value and the model receives the structured
  employee/PTO/policy results across sequential turns.
- Verify `TEST-002` remains a found employee with no PTO record and is not reported as having
  zero hours; verify `TEST-003` with a zero-hour record remains distinct from missing.
- Verify a missing or ambiguous employee identifier produces a request for a valid employee
  ID without selecting a record or performing an employee-specific lookup; do not add
  employee-name search or identity resolution.
- Verify the existing supported prior-approval check receives only explicitly supplied
  `approval_facts`, and an inconclusive result remains indeterminate.
- Verify email drafting is reachable only from an explicit draft request and still returns an
  unsent proposal requiring the existing confirmation behavior.
- Keep user-facing scenarios and machine-readable tool traces separate from hidden reasoning
  and raw employee records.

### Deferred / explicitly excluded

- New orchestration graph, workflow engine, intent router, MCP tools, or HR integrations.
- New security-posture data, remote-work compliance rules, legal determinations, or approval
  authority.
- Changes to the public `HRAgent`, MCP, or F005 interface; only the approved internal
  `LLMCompletion` boundary is extended.
- Grader-facing UI/API (F005), evaluation set/metrics, deployed demo, recorded presentation,
  and final design/submission deliverables (F006).

## Requirements-to-Design Traceability

| Requirement | Design/reuse | New work | Acceptance verification |
|---|---|---|---|
| QR-019 | Reuse `HRAgent.process_request`, dynamic tool discovery, sequential calls, F002 employee/PTO/compliance tools, and F001-backed policy search. | Workflow-specific prompt guidance and two composed scenario suites. | PTO scenario consumes profile + PTO + relevant policy evidence; remote scenario consumes profile + relevant location/security policy evidence and uses the supported prior-approval check only when applicable. |
| QR-020 | Reuse `OperationalTrace` and its completion event, allowlisted tool summaries, policy `source_refs`, and current statuses. | Add an optional typed final disposition to `LLMCompletion`; write it into the existing completion event only when present. | With successful MCP calls and insufficient candidate policy evidence, assert `human_review_recommended` in the trace and a matching human-review recommendation in the final answer; verify no raw answer or reasoning enters the trace. |
| QR-021 | Reuse schema validation, missing-required-argument clarification, `not_found`/`indeterminate` statuses, bounded execution, and explicit MCP failure handling. | Add workflow cases for missing and ambiguous identity, no PTO record, insufficient policy evidence, unavailable tool, and incomplete approval facts. | Deterministic tests assert clarification before employee-specific lookup, no identity selection/search, distinct missing-vs-zero result, partial/error status, and no fabricated evidence or result. |
| QR-022 | Reuse the discovered `draft_hr_email` tool and proposal-bound `confirm_action`; unsupported sending/approval/mutation is refused. | Add PTO-specific explicit-draft and no-send acceptance case. | Assert no draft tool call absent a request, `confirmation_required` when requested, and no send call or success claim. |
| QR-032 | F004 provides stable synthetic requests and expected outcomes; F005 remains the owner of the grader-facing entry point. | Document reusable request fixtures and results; do not add UI/API code. | Run deterministic tests that F005 can later expose through its interface; verify F004 has no dependency on that interface. |
| QR-047 | Reuse existing tool schemas, policy evidence metadata, and trace events. | Add `contracts/workflows.md` with representative call sequences, inputs/outputs, evidence, and escalation conditions. | Compare documented sequences and outcomes against acceptance/integration traces; sequences are examples, not mandatory fixed order. |

**QR-020 acceptance linkage**: The F004 mapping is FR-010 and SC-007. US3-AS1 requires the
trace to show any clarification or escalation; US2-AS3 requires a human-review recommendation
when missing facts prevent determining eligibility. The typed completion disposition is
verified in the successful-MCP/insufficient-evidence remote-work case.

**Supporting, not F004-owned**: QR-040-QR-042 (F006 evaluation and metrics) and QR-049/QR-051
(F006 final demo) may reuse F004's deterministic cases and workflow contract. F004 does not
create evaluation infrastructure, claim grader UI availability, or produce the final demo.

**Requirements coverage**: QR-020 is addressed by an explicit, optional final disposition on
the existing completion boundary and trace event. It is not inferred from answer text.
FR-010/SC-007 remain covered by ordered tool events, allowlisted summaries, source references,
answer basis, and the final disposition for human-review recommendations.

## Test and Acceptance Plan

| Layer | Planned coverage |
|---|---|
| Deterministic agent acceptance | `tests/test_f004_workflows.py`: scripted PTO and remote-work tool responses; order-independent valid sequences; result chaining; citations; point-in-time balance; missing PTO versus zero; missing and ambiguous employee identity (clarify before lookup, without name search or identity resolution); unsupported/inconclusive remote eligibility, including international work with no out-of-state compliance call, cited available policy evidence, and human review without an eligibility claim; explicit unsent draft; trace allowlist/privacy. Include a successful-MCP/insufficient-policy case whose same final completion carries both a human-review answer and typed disposition, a `None` compatibility case, and explicit rejection of an invalid disposition. |
| Provider-boundary unit tests | Extend `tests/unit/test_agent_llm.py` to verify the configured adapter maps structured final metadata into the typed field in the same response, leaves tool-call handling unchanged, and rejects invalid disposition values; use a mocked provider response, not a live call. Before Milestone 1 is considered complete, separately perform a manual compatibility checkpoint against the configured live provider for same-completion disposition and native tool-call behavior. This checkpoint is not routine CI. |
| Actual MCP integration | `tests/integration/test_f004_workflows_mcp.py`: reuse `tests/fixtures/mcp/harness.py` to discover and invoke existing tools over stdio with a controlled LLM. Use fixed synthetic data and a narrow policy fixture for each workflow as needed; have the controlled final completion return the typed disposition for the insufficient-evidence remote-work scenario; no live provider call. |
| Existing regression coverage | Run the agent acceptance, confirmation, trace, and MCP integration tests to ensure F003 behavior and F002 contracts remain unchanged. |
| Static validation | Ruff on changed Python files; repository plan-artifact checks for traceability, internal references, unresolved template placeholders, disposition vocabulary, and scope boundaries. |

No project-wide evaluation suite, routine live-model test, benchmark, or deployment check is
added by F004. Mocked adapter tests verify the provider-boundary mapping and tool-call
regression deterministically, but do not establish compatibility with the configured live
provider. A separate manual compatibility checkpoint against that provider is required
before Milestone 1 is considered complete; it uses synthetic inputs and is not a routine CI
test or deterministic acceptance oracle.

## Risks and Decisions for Review

1. **Provider structured completion compatibility**: the configured provider adapter must
   return the optional disposition with the same final completion while preserving tool calls.
   Validate its structured-output path without adding a second model call. Mocked
   provider-boundary tests verify adapter mapping but do not prove live-provider
   compatibility; perform a separate manual compatibility checkpoint before Milestone 1
   completion. Existing adapters and callers that omit the optional field remain compatible
   through its `None` default; F004 acceptance still requires the configured adapter to
   supply the value for the human-review scenario.
2. **Disposition/answer consistency**: the final-output contract must require an explicit
   human-review recommendation in the accompanying answer when the disposition is set.
   Deterministic tests verify the pair; implementation must not infer the disposition from
   free-form text. The provider-boundary test validates the structured field without a live
   model call.
3. **Policy fixture parity**: the existing isolated MCP integration fixture has remote-work
   evidence but may not have a PTO-specific excerpt. Add only test fixture evidence if needed;
   do not alter production policy content or F001 retrieval behavior for F004.
4. **Dynamic ordering**: tool call order can vary with the request and model. Contracts and
   tests should assert required evidence and sequential result propagation, not one globally
   fixed sequence.
5. **No security facts in employee data**: policy describes required controls; it cannot prove
   that a synthetic employee's device/network/account satisfies them. Do not add such facts to
   fixtures simply to make the workflow appear complete.

## Project Structure

### Documentation (this feature)

```text
specs/004-hr-agentic-workflows/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── workflows.md
└── checklists/
    └── requirements.md
```

### Source and tests

```text
src/hr_agent/
├── agent.py                          # Workflow instructions and disposition-to-response/trace mapping
├── types.py                          # Optional typed LLMCompletion final_disposition
└── llm.py                            # Map same provider completion into the typed field

tests/
├── test_f004_workflows.py            # Deterministic composed workflow acceptance
├── integration/
│   └── test_f004_workflows_mcp.py    # Actual stdio MCP integration with controlled LLM
├── unit/
│   └── agent_orchestration_helpers.py # Preserve default None in scripted completions
└── fixtures/mcp/                     # Reuse fixtures; add only required synthetic policy evidence
```

**Structure Decision**: Keep F004 inside the existing Python agent package and pytest layout.
Do not add production modules, a new package, a service, or a separately deployed component.
The implementation must also update F003's existing Python interface and data-model trace
contracts to document the optional field and completion-event disposition; these updates
preserve rather than replace the shared F003 boundary.

## Complexity Tracking

No constitution exception or additional project is proposed. The optional field is a focused
extension to the existing final-completion contract, limited to the currently required
human-review recommendation.
