# Tasks: Deployment, CI/CD, and Evaluation

**Input**: Approved design documents from `specs/006-deployment-ci-cd-evaluation/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, and `quickstart.md`

**Organization**: Four user-reviewed milestones, ordered to establish and verify the hosted
vertical slice before implementing the bounded evaluation and completing submission evidence.
Tasks marked **MANUAL: USER** require your account, credentials, or submission action.
`[~]` indicates partial completion or evidence limited by a documented blocker.

## Milestone 1: Foundation

**Purpose**: Prepare the current app, secure host-secret bridge, deployment artifact, and
existing CI gate. Do not start hosted deployment until this milestone is reviewed.

- [X] T001 **[MANUAL: USER]** Confirm Streamlit Community Cloud account/setup is available without payment information and that Python 3.11, the existing app, and same-service MCP subprocess fit current host limits. If not, stop and report the blocker for approval before considering another host (QR-003, QR-033–QR-035). **Evidence:** user confirmed free hosting, Python 3.11, and the `app.py` entry point; the app is deployed and the user reports successful prompts. Exact host resource limits and per-request MCP/RAG traces were not retained.
- [X] T002 Add editable project installation to the existing `requirements.txt` and verify the editable install and project imports from Python 3.11 without adding providers or evaluation frameworks (QR-004, QR-058). **Evidence:** `pip install -e .` and imports of `hr_app`, `hr_agent`, and `hr_mcp` passed in the existing Python 3.11 `.venv`; clean-environment reproduction remains in T015.
- [X] T003 Add the minimal `st.secrets["GROQ_API_KEY"]` to environment bridge at `src/hr_app/app.py`; preserve an explicit process environment value, allow startup when the host secret is absent, and never persist or expose the secret. Add focused tests in `tests/test_chat_interface.py` or a directly related test file for mapping, precedence, missing secret, and redaction (QR-007). **Evidence:** all 16 AppTest tests passed, including mapping, precedence, missing-secrets-file, and error-redaction cases. User reports successful hosted chatbot prompts; the host secret value/presence was not independently inspected.
- [X] T004 Extend `.github/workflows/ci.yml` with the named `Run Streamlit AppTest startup` step for `tests/test_chat_interface.py`; retain the existing Python 3.11 matrix, Ruff/import checks, stdio MCP integration, full pytest, and push/PR triggers (QR-037, QR-038). **Evidence:** YAML validation passed; merged-main run #16 passed Ruff, named AppTest, MCP integration, and pytest on both matrix jobs.
- [X] T005 Build the F001 index from the checked-in synthetic corpus; include only `.hr_rag_index/active.json` plus its referenced generation in the deployment artifact. Verify checksums, embedding identity, retrieval, and repository size; do not add model caches or startup-time index building (QR-003, QR-006, QR-034). **Evidence:** generated 12-document/298-chunk index (600,764 bytes); local pointer/checksum/model identity and HR-002 retrieval validated. At merged-main commit `7c33ec5`, GitHub contains the active pointer and referenced `index.faiss` and `metadata.json`; the user reports the app is deployed from that revision.
- [X] T006 Run the foundation's focused tests and CI checks. **[MANUAL: USER]** Configure required existing CI checks on protected `main`, prevent bypass/direct pushes that skip them, confirm Community Cloud will track `main`, and record the actual required check names (QR-037–QR-039). **Evidence:** user confirmed branch protection and required checks. [PR run #15](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/43815149004) and [merged-main run #16](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/43815690838) passed both matrix jobs, including Ruff, named AppTest startup, MCP integration, and pytest. Run #16 tested merge commit `7c33ec581026a006ab3b54b2fe3ef446df7f739e`.

**Milestone 1 review gate**: Stop and wait for your review before configuring the hosted app.

## Milestone 2: Core vertical slice

**Purpose**: Deploy the existing application and verify one real hosted PTO workflow with
Groq before spending quota on evaluation.

- [X] T007 **[MANUAL: USER]** Merge the approved changes to protected `main` after required checks pass, then create/configure the Streamlit Community Cloud app from that branch with Python 3.11 and `src/hr_app/app.py`; store `GROQ_API_KEY` only in host Secrets (QR-007, QR-033–QR-035, QR-039). **Evidence:** user supplied the deployed URL <https://hr-ai-chat-bot-jonathan-alarcon.streamlit.app/>. F006 was merged as `7c33ec581026a006ab3b54b2fe3ef446df7f739e`; hosted run #16 passed on that revision. User reports the app is deployed. The exact commit currently serving on Community Cloud was not independently exposed.
- [X] T008 **[MANUAL: USER]** Record the deployed smoke-test status and distinguish direct observations from details not retained (QR-033–QR-036, QR-057, QR-060). **Evidence:** user reports several successful prompts at the deployed URL. This is user-reported evidence of successful chatbot responses, not an independently observed transcript. Exact MCP tool names/results, RAG citations, and a specific `SYN-001` PTO response were not provided; those details remain partially verified. The authoritative local fixture gives `SYN-001` 80 available hours as of `2026-01-01`; the intended policy source is `HR-002`. No deployed failure has been reported. The previous local production-index timeout is not treated as a reproduced hosted defect.
- [X] T009 If the hosted request returns `llm_request_failed`, investigate only enough to check secret presence without printing it, model selection, host startup/resource status, and existing sanitized diagnostics. Classify it as a provider failure; claim a more specific cause only when safe evidence supports it. Do not blindly retry or add a provider (QR-007, QR-033, QR-057). **Not triggered:** user reports successful chatbot responses and no `llm_request_failed` failure. No cause investigation or repeated smoke request was performed.

**Milestone 2 review gate**: Closed from the user-reported deployment and smoke testing plus
the passing hosted CI run. Groq-backed responses are user-reported; MCP execution, RAG
citations, and the exact `SYN-001` workflow remain only partially verified because no
per-prompt tool trace or answer evidence was provided. No known hosted failure blocks the MVP.

## Milestone 3: Remaining MVP

**Purpose**: Implement and run the single bounded Groq evaluation, then complete the
provider-free retrieval comparison.

- [X] T010 Create 20 unique synthetic cases with rubrics, expected evidence/tool/safety outcomes, coverage of all five required categories, and a fixed 10-case latency subset (QR-006, QR-040). **Evidence:** `evaluation/cases.json` validates as 20 cases, four per category, with 10 selected latency cases; all employee-specific scenarios use `SYN-001` or `SYN-003`.
- [X] T011 Implement `evaluation/run_evaluation.py` using the existing agent, Groq adapter, and stdio MCP client. It supports a one-case `--diagnostic` gate and the bounded `--live` run, writes to an optional isolated output directory, runs sequentially with no retries, measures `AgentSession.process_request`, appends privacy-safe rows immediately, and separates failure classes (QR-041–QR-043, QR-054). **Evidence:** prior live attempt preserved; diagnostic and full-suite runner paths are covered by deterministic tests. Incomplete runs return a failing process status.
- [X] T012 Add deterministic tests for case validation/category coverage, fixed latency selection, nearest-rank percentiles, retrieval aggregation, failure classification, diagnostic gating, and isolated output/partial-result preservation; tests make no Groq calls (QR-006, QR-040–QR-043). **Evidence:** `tests/unit/test_f006_evaluation.py`: 18 passed; Ruff passed.
- [X] T013 Run local F001 retrieval comparison for expected-source cases at k=3 and k=5 and report measured recall without extra Groq calls (QR-044, QR-054). **Evidence:** 15 applicable cases / 24 expected source labels; k=3 retrieved 16/24 (66.7%), k=5 retrieved 17/24 (70.8%).
- [~] T014 **[MANUAL: USER]** Use the existing Groq credential and explicit authorization for one suite run; score answer correctness, groundedness, citations, escalation, and action safety from retained outputs where available (QR-041–QR-043, QR-054, QR-057). **Evidence/blocker:** one suite run was attempted exactly once. Case `EVAL-001` selected `search_policy_documents`, then its MCP call timed out after 302.20 seconds (`mcp_tool_call_failed` / `timeout`). One bounded, provider-free MCP diagnostic reproduced a 60-second timeout (protocol 408) after successful initialization and discovery; no server tool-completion trace was written. A separate child-process check using the MCP environment loaded the embedding model in 8.02 seconds and completed direct index retrieval in 0.08 seconds. The active index and model cache exist, narrowing the unresolved fault to the MCP tool execution/response path rather than startup, discovery, or direct RAG. No Groq provider failure was observed; 19 cases were not run, 0/10 latency samples completed, and no HR answer was available for answer-level scoring. A diagnostic-first Ubuntu Actions job is now available in the existing workflow, but it has not been triggered. Its first diagnostic must succeed before the suite step runs; the run writes to a separate artifact directory and preserves the partial local results.

**Milestone 3 review gate**: Stop here for review. The case set, runner, tests, and k comparison
are complete, but the live evaluation remains blocked by an unresolved local MCP tool
execution/response timeout. Startup, discovery, active index files, cached model availability,
and direct child-process retrieval were verified. Provider failure count is zero; evaluation is
incomplete, so no p50/p95 or answer-level correctness score is claimed. The existing partial
evidence is preserved. The manual-only Ubuntu job is implemented but has not been triggered.
Do not mark this milestone complete or start Milestone 4 until its diagnostic and, if allowed
by that gate, bounded suite artifacts have been reviewed.

## Milestone 4: Verification and closure

**Purpose**: Verify implementation against the assigned requirements and complete the
deployment, evaluation, and submission record. Manual results remain explicitly labeled.

- [ ] T015 Run the complete pytest suite, Ruff, the named AppTest, and the stdio MCP integration locally; follow the README from a clean environment and exercise both workflows; push the final changes and verify the existing hosted GitHub Actions matrix passes. Confirm failed/skipped checks are not reported as passing (QR-004, QR-037–QR-039, QR-058).
- [ ] T016 Update `README.md`, `docs/deployed.md`, `docs/design-and-evaluation.md`, and `docs/ai-tooling.md` with reproducible local/deployment/evaluation instructions, verified URLs and health equivalent, actual host/cold-start limitations, architecture and safety choices, both F004 tool sequences, evaluation methods/results, AI-tooling use/strengths/limitations/responsibility, and citations for external sources. Document QR-035 as not applicable to the selected single-service stdio topology (QR-003–QR-005, QR-035–QR-036, QR-045–QR-047, QR-053–QR-054, QR-056, QR-058, QR-060).
- [ ] T017 Review repository artifacts, including tracked synthetic mock data, MCP server/tool definitions, and evaluation cases/scripts/results, and review the requirement-to-evidence mapping below against the final implementation. Mark each item verified only with evidence of the appropriate scope; record pending, blocked, or not-applicable status without substituting local tests for hosted/live evidence (QR-003–QR-007, QR-033–QR-060).
- [ ] T018 **[MANUAL: USER]** Verify the final repository, deployed, and demo links; grant `quantic-grader` access; submit the dashboard and any conditionally requested group agreement; confirm the participant limit; and record the 7–10 minute screen-share showing both deployed workflows, tool names/arguments/outputs, citations, final behavior, design, deployment, CI/CD, and evaluation. Ensure all group members speak, appear on camera, and follow the ID instruction; do not store identity documents in the repository (QR-048–QR-051, QR-055, QR-059).

**Milestone 4 review gate**: Stop and present the completed verification and submission
evidence for your final review.

## Requirement-to-task coverage

| Requirement | Implementation tasks | Verification tasks |
|---|---|---|
| QR-003 | T001, T005, T007 | T001, T005, T008, T016 |
| QR-004 | T002 | T002, T015 |
| QR-005 | T016 | T015, T017 |
| QR-006 | T005, T010, T011 | T012, T013 |
| QR-007 | T003, T007 | T003, T008, T009 |
| QR-033 | T007, T008 | T001, T008, T017 |
| QR-034 | T005, T007 | T008, T017 |
| QR-035 | T016 | T016, T017 |
| QR-036 | T008, T016 | T008, T016, T017 |
| QR-037 | T004 | T006, T015 |
| QR-038 | T004 | T006, T015 |
| QR-039 | T006 | T006, T015 |
| QR-040 | T010 | T012, T014 |
| QR-041 | T011, T014 | T012, T014 |
| QR-042 | T011, T014 | T012, T014 |
| QR-043 | T010, T011, T014 | T012, T014 |
| QR-044 | T013 | T013 |
| QR-045 | T016 | T017 |
| QR-046 | T016 | T017 |
| QR-047 | T016 | T017 |
| QR-048 | T016, T018 | T018 |
| QR-049 | T018 | T018 |
| QR-050 | T018 | T018 |
| QR-051 | T016, T018 | T018 |
| QR-052 | T017 | T017 |
| QR-053 | T016 | T015, T017 |
| QR-054 | T010–T014, T016 | T012–T014, T017 |
| QR-055 | T018 | T018 |
| QR-056 | T016 | T017 |
| QR-057 | T008, T011, T014 | T008, T014, T017 |
| QR-058 | T002, T016 | T002, T015 |
| QR-059 | T018 | T018 |
| QR-060 | T016 | T008, T016, T017 |

QR-035 is conditional and not applicable to the selected stdio, single-service deployment;
document that decision. Streamlit account/secrets setup, protected-branch settings,
hosted-workflow verification, live Groq evaluation, grader access, demo recording, dashboard
submission, and presenter/participant checks require user participation.
