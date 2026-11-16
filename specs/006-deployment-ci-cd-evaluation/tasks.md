# Tasks: Deployment, CI/CD, and Evaluation

**Input**: Approved design documents from `specs/006-deployment-ci-cd-evaluation/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, and `quickstart.md`

**Organization**: Four user-reviewed milestones, ordered to establish and verify the hosted
vertical slice before implementing the bounded evaluation and completing submission evidence.
Tasks marked **MANUAL: USER** require your account, credentials, or submission action.

## Milestone 1: Foundation

**Purpose**: Prepare the current app, secure host-secret bridge, deployment artifact, and
existing CI gate. Do not start hosted deployment until this milestone is reviewed.

- [ ] T001 **[MANUAL: USER]** Confirm Streamlit Community Cloud account/setup is available without payment information and that Python 3.11, the existing app, and same-service MCP subprocess fit current host limits. If not, stop and report the blocker for approval before considering another host (QR-003, QR-033–QR-035). **Evidence:** user confirmed free hosting, Python 3.11, and the `app.py` entry point; runtime/MCP compatibility remains pending deployment.
- [X] T002 Add editable project installation to the existing `requirements.txt` and verify the editable install and project imports from Python 3.11 without adding providers or evaluation frameworks (QR-004, QR-058). **Evidence:** `pip install -e .` and imports of `hr_app`, `hr_agent`, and `hr_mcp` passed in the existing Python 3.11 `.venv`; clean-environment reproduction remains in T015.
- [X] T003 Add the minimal `st.secrets["GROQ_API_KEY"]` to environment bridge at `src/hr_app/app.py`; preserve an explicit process environment value, allow startup when the host secret is absent, and never persist or expose the secret. Add focused tests in `tests/test_chat_interface.py` or a directly related test file for mapping, precedence, missing secret, and redaction (QR-007). **Evidence:** all 16 AppTest tests passed, including the new mapping, precedence, missing-secrets-file, and error-redaction cases. Hosted secret configuration remains pending.
- [X] T004 Extend `.github/workflows/ci.yml` with the named `Run Streamlit AppTest startup` step for `tests/test_chat_interface.py`; retain the existing Python 3.11 matrix, Ruff/import checks, stdio MCP integration, full pytest, and push/PR triggers (QR-037, QR-038). **Evidence:** workflow YAML validation passed; the targeted test file passed. Hosted GitHub Actions remains pending.
- [X] T005 Build the F001 index from the checked-in synthetic corpus; include only `.hr_rag_index/active.json` plus its referenced generation in the deployment artifact. Verify checksums, embedding identity, retrieval, and repository size; do not add model caches or startup-time index building (QR-003, QR-006, QR-034). **Evidence:** generated 12-document/298-chunk index (600,764 bytes); pointer and file checksums/model identity validated; local PTO-policy retrieval returned `HR-002`. Files remain unstaged and uncommitted.
- [ ] T006 Run the foundation's focused tests and CI checks. **[MANUAL: USER]** Configure required existing CI checks on protected `main`, prevent bypass/direct pushes that skip them, confirm Community Cloud will track `main`, and record the actual required check names (QR-037–QR-039). **Evidence:** user confirmed branch protection and required checks; [main run #14](https://github.com/jalarcon8/hr-ai-chat-bot/actions/runs/43806478040) passed both `test (windows-latest)` and `test (ubuntu-latest)`. That run predates F006 changes; this working branch has no PR or hosted Actions run yet. Local AppTest `16 passed`, MCP integration `3 passed`, Ruff, YAML validation, and `git diff --check` passed.

**Milestone 1 review gate**: Stop and wait for your review before configuring the hosted app.

## Milestone 2: Core vertical slice

**Purpose**: Deploy the existing application and verify one real hosted PTO workflow with
Groq before spending quota on evaluation.

- [ ] T007 **[MANUAL: USER]** After Milestone 1 review, merge the approved changes to protected `main` only after all required checks pass. Create/configure the Streamlit Community Cloud app from that branch, using Python 3.11 and `src/hr_app/app.py`; add `GROQ_API_KEY` through the host Secrets settings without sharing or committing its value (QR-007, QR-033–QR-035, QR-039). **Pending:** no PR/merge, hosted app, or host secret is configured; the generated `.hr_rag_index` must be included in the merged revision.
- [ ] T008 **[MANUAL: USER]** Open the deployed URL, verify the chat renders and **Check MCP health** discovers all six tools, then run the synthetic `TEST-001` PTO request for 8 hours on `2026-02-01`. Check the 40-hour balance as of `2026-01-01`, an `HR-002` citation/snippet, visible tool activity, and that no request is claimed submitted or approved. The `HR-005` PTO source used by F004's integration test is a temporary fixture; the deployed corpus uses the authoritative `HR-002` PTO policy. Record URL, commit, health-equivalent result, outcome, and observed cold-start/host limits (QR-033–QR-036, QR-057, QR-060). **Pending:** requires the hosted app and URL. A local stdio search against the deployment index exceeded 120 seconds; the synthetic MCP integration suite and direct local retrieval passed, so verify the production-index MCP path during deployment and investigate only if the delay reproduces.
- [ ] T009 If the hosted request returns `llm_request_failed`, investigate only enough to check secret presence without printing it, model selection, host startup/resource status, and existing sanitized diagnostics. Classify it as a provider failure; claim a more specific cause only when safe evidence supports it. Do not blindly retry, add a provider, or claim success without a passing workflow (QR-007, QR-033, QR-057). **Not triggered:** no hosted request has been made.

**Milestone 2 review gate**: Stop and wait for your review of the deployment and smoke-test
evidence before building or running the evaluation.

## Milestone 3: Remaining MVP

**Purpose**: Implement and run the single bounded Groq evaluation, then complete the
provider-free retrieval comparison.

- [ ] T010 Create `evaluation/cases.json` with 20–30 unique synthetic cases, rubrics, expected evidence/tool/safety outcomes, coverage of all five required categories, and a stable 10–20-case latency subset selected from the same run (QR-006, QR-040).
- [ ] T011 Implement `evaluation/run_evaluation.py` using the existing agent, Groq adapter, and stdio MCP client. Require explicit live opt-in; issue sequential requests at a controlled rate without retries; measure `AgentSession.process_request`; append privacy-safe per-attempt results to `evaluation/results.jsonl`; capture evidence for manual grounding/citation review, aggregate trace-based metrics and p50/p95 in `evaluation/results.md`, record observable cold/warm conditions, preserve partial results, and separate provider failures from functional failures (QR-041–QR-043, QR-054).
- [ ] T012 Add focused deterministic tests under `tests/unit/test_f006_evaluation.py` for case count/category validation, fixed latency sample selection, metric aggregation, percentile calculation, safe failure classification, and partial-result preservation. These tests must not call Groq (QR-006, QR-040–QR-043).
- [ ] T013 Implement and run the local F001 retrieval comparison for the same cases' expected source IDs at k=3 and k=5; report measured evidence recall in `evaluation/results.md` without extra Groq calls or claims of unmeasured improvement (QR-044, QR-054).
- [ ] T014 **[MANUAL: USER]** Configure the existing Groq credential locally through the approved environment mechanism and authorize/run the suite once. Manually score groundedness and citations against case evidence and review trace-based scores; finalize `evaluation/results.jsonl` and `evaluation/results.md` with every metric's numerator/denominator, latency sample count and conditions, attempted/completed/failed/not-run counts, and provider/quota limitations. Do not repeat the run merely to fill missing cases (QR-041–QR-043, QR-054, QR-057).

**Milestone 3 review gate**: Stop and wait for your review of evaluation results and limitations
before final documentation and submission work.

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
