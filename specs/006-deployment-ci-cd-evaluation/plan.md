# Implementation Plan: Deployment, CI/CD, and Evaluation

**Branch**: `006-deployment-ci-cd-evaluation` | **Date**: 2026-11-16 | **Spec**: [spec.md](spec.md)

**Input**: Clarified feature specification from
`specs/006-deployment-ci-cd-evaluation/spec.md`

## Summary

Deliver a deployed F005 vertical slice first on Streamlit Community Cloud, using the existing
Streamlit chat, Groq adapter, stdio MCP server, synthetic records, and F001 policy retrieval.
The only application integration needed for credentials is a small Streamlit-secret-to-
environment bridge at the UI boundary. Ship the already-generated FAISS snapshot with the
repository so the deployed app does not build an index at startup; load the embedding model
only when policy search first needs it. Verify one synthetic PTO workflow in the deployed UI
before spending the approved quota on one sequential 20-30 case evaluation run.

Reuse `.github/workflows/ci.yml`, pytest, Ruff, F005 AppTest startup coverage, and the existing
stdio MCP integration test. Let Streamlit Community Cloud deploy only from `main`, protected
by the existing required CI checks; do not add a deploy service or a second CI workflow.
Complete evaluation scoring, the k=3 versus k=5 retrieval comparison, required documentation,
and human submission checks after the deployed slice works.

## Technical Context

**Language/Version**: Python 3.11, matching `pyproject.toml` (`>=3.11,<3.12`).

**Primary Dependencies**: Existing Streamlit, Groq, FastMCP/MCP SDK, FAISS, Sentence
Transformers, NumPy, pytest, and Ruff. No new runtime or evaluation framework.

**Storage**: No database or remote state. Reuse the synthetic JSON data and commit the
generated `.hr_rag_index` active snapshot needed by the hosted app. Store evaluation cases
and partial/final results under `evaluation/`; do not store credentials or identity documents.

**Testing**: Existing pytest suite and Ruff workflow. Reuse `tests/test_chat_interface.py`
AppTest startup coverage and `tests/integration/test_agent_mcp.py` stdio discovery/call
coverage. Add focused tests for the secret bridge and evaluation input/scoring only.

**Target Platform**: Streamlit Community Cloud, single app service, selected Python 3.11
runtime, existing app entry point `src/hr_app/app.py`.

**Project Type**: Python package with a Streamlit UI, asynchronous agent runtime, and
same-service MCP stdio subprocess.

**Performance Goals**: No new service SLO. Report p50/p95 for 10-20 sequential agent requests
from the one evaluation run; separately note hosted cold-start behavior if observed.

**Constraints**: No payment-dependent setup, paid database, separately deployed MCP server,
additional model provider, provider calls in routine CI, application-start index build, raw
provider logs, or unnecessary repeat of a failed live run.

**Scale/Scope**: One hosted workflow smoke test; one 20-30 case live evaluation run; one
retrieval-only k comparison; final delivery artifacts and manual checks.

## Constitution Check

### Pre-design gate

| Principle/constraint | Status | Plan application |
|---|---|---|
| I. Simplicity First | Pass | Use the existing Streamlit service, agent, MCP tools, CI workflow, and pytest suite; no new service or evaluation framework. |
| II. Python-First Implementation | Pass | Keep the small settings bridge, evaluation runner, and tests in Python 3.11. |
| III. Modular Separation | Pass | Read Streamlit secrets at the UI boundary; keep provider configuration and MCP ownership in existing modules. |
| IV. Grounded AI Responses | Pass | Verify returned policy citations and synthetic employee/PTO evidence in the deployed workflow and evaluation. |
| V. MCP-Compliant Tool Integration | Pass | Reuse the existing stdio MCP client/server and discovered tools; do not bypass MCP. |
| VI. Synthetic Data and Safe Operations | Pass | Use synthetic records, keep the email draft unsent, and keep credentials out of tracked files and logs. |
| VII. Automated Testing and Reproducibility | Pass | Extend existing CI coverage; routine checks remain deterministic and provider-free. Document setup, deployment, tests, and evaluation. |
| Single-service/free-tier constraint | Pass, pending host validation | Community Cloud runs the existing UI and MCP subprocess together; validate resource and account limits before declaring success. |
| Feature ownership | Pass | Reuse F001-F005 behavior; F006 adds integration, evaluation, delivery docs, and submission verification only. |

### Post-design gate

The planned design adds no provider, persistent service, database, or new application
framework. The committed index is a small derived artifact of the existing synthetic
corpus, not a second retrieval system. The credential bridge is confined to the Streamlit
boundary and must preserve local environment-variable precedence. GitHub branch protection
is a manual repository setting, not a new deployment service. Evaluation remains one
sequential run with explicit partial-result handling.

## Architecture and Delivery Sequence

### Phase 1 - Working deployed vertical slice

This is the first implementation outcome. Use existing CI as the prerequisite; do not start
live provider calls until the app, MCP health probe, required configuration, and index artifact
are ready.

1. **Verify the local launch contract**
   - Configure Streamlit Community Cloud to use the repository root, Python 3.11, the existing
     pinned requirements, and `src/hr_app/app.py`.
   - Add `-e .` to the existing `requirements.txt` so the hosted environment installs the
     project's `src/` package using its existing `pyproject.toml` metadata.
   - Confirm `tests/test_chat_interface.py` runs through the existing pytest step and starts
     the app with Streamlit `AppTest`.
2. **Bridge the hosted secret**
   - Add a small helper at the Streamlit boundary to read `GROQ_API_KEY` from `st.secrets`
     and make it available to `get_agent_setting` via the process environment.
   - Preserve an explicitly set process environment value; do not print, serialize, persist,
     or add the secret to `AgentConfig`, the trace, or an exception message.
   - When the host secret is absent, allow the UI to start and retain the existing safe
     `missing_llm_credentials` request failure. Local `.env` behavior remains unchanged.
   - Add focused tests for host-secret mapping, existing environment precedence, missing
     secret behavior, and exclusion of secret values from displayed errors/traces.
3. **Prepare the policy index**
   - Build the active FAISS snapshot from the checked-in synthetic `corpus/` using existing
     `build_index`, `ChunkingConfig`, and `SentenceTransformerEmbedder` configuration.
   - Commit only the active pointer and its referenced generation under `.hr_rag_index/`;
     include no model cache or stale generations. Confirm the snapshot loads, its checksums
     validate, its embedding identity matches the configured model, and its size is suitable
     for the repository.
   - Do not make Streamlit or the MCP server build the index at startup. The embedding model
     remains lazily loaded on the first policy search, as in the current implementation.
   - Before deployment, complete Phase 2's existing-workflow checks, named AppTest step,
     protected-`main` rules, and Community Cloud branch verification. These are deployment
     prerequisites even though the detailed CI tasks are listed in the following section.
4. **Deploy and smoke-test once**
   - Deploy the current `main` commit to Community Cloud after its required checks pass.
     Configure Python 3.11 and the Groq secret in the host settings; do not add secrets to
     repository files.
   - Verify app startup and use the sidebar health check to confirm MCP stdio discovery and
     the six-tool catalog. This health check does not call Groq and is not proof of provider
     readiness.
   - In the browser, enter synthetic employee ID `TEST-001` and run the F004 PTO scenario:
     8 hours on `2026-02-01`. Verify the profile, 40-hour balance as of `2026-01-01`,
     matching returned `HR-002` policy citation, visible safe tool trace, and no claim that a
     request was submitted or approved.
   - Treat this as one controlled smoke test. If the UI returns `llm_request_failed`, do not
     blindly retry. First verify secret presence without printing its value, configured model
     selection, deployment logs/resource status, and any existing sanitized provider
     diagnostic. Classify `llm_request_failed` as a provider failure; distinguish
     authentication, quota, or request rejection only when the existing safe code/diagnostic
     supports it, otherwise record an unknown provider failure. Keep this separate from
     application, MCP, index, or evidence failure. Stop and record the result if unresolved;
     do not introduce another provider.
   - Record the deployed URL, health-equivalent behavior, commit, test run, smoke-test result,
     model identifier, and any cold-start/host limits without recording credentials or
     unnecessary raw content.

### Phase 2 - CI and protected deployment gate

1. Keep the existing Windows/Ubuntu Python 3.11 matrix, Ruff, imports, actual stdio MCP
   integration, and full pytest run in `.github/workflows/ci.yml`.
2. Add one named `Run Streamlit AppTest startup` step to the existing workflow, invoking
   `tests/test_chat_interface.py`. Keep the full pytest run as well; this mirrors the
   workflow's existing explicit MCP integration step and avoids a new workflow or
   provider-dependent check.
3. Configure GitHub `main` branch protection to require both existing matrix test jobs. The
   Community Cloud app tracks `main`, so only a merged change with successful required checks
   updates the deployment. No GitHub Actions deployment job is needed.
4. Manually verify the required check names and the Community Cloud branch setting. Record
   this configuration as manual evidence; repository tests cannot prove the GitHub setting.

### Phase 3 - One bounded evaluation run

1. Add 20-30 synthetic evaluation cases in the simplest structured format, with stable IDs,
   one required category per case, the request and explicit context, a gold answer/rubric,
   expected evidence source IDs where applicable, required/forbidden tools, expected status
   or escalation, and an action-safety assertion.
2. Add one small Python runner using the existing `AgentSession`/`HRAgent`, Groq adapter, and
   stdio `MCPClient`; no LLM-as-judge or third-party evaluation package. Require explicit
   live opt-in and validate case count/category coverage before making provider calls.
3. Execute cases sequentially, with no evaluation-loop retries or parallel calls. Measure
   `time.perf_counter()` around each `AgentSession.process_request`; define the measure as
   agent/MCP/provider completion time, not browser rendering. Select 10-20 representative
   cases from the same run for p50/p95. Record the first-request/cached-model condition and
   report hosted cold-start observations separately when available.
4. Score groundedness and citation accuracy against expected evidence with a manual rubric;
   score tool selection, workflow completion, escalation/clarification, and action safety
   from expected outcomes and the existing sanitized response/trace. Report numerators,
   denominators, executed case count, and provider/quota failures separately. Do not
   misclassify unavailable provider cases as functional passes or failures.
5. Append a privacy-safe result row after every completed case so successful results survive
   a quota limit. On an authentication or quota failure, record a safe failure category,
   stop further provider calls, and preserve completed rows; do not rerun the suite to fill
   missing samples.
6. Use the same evaluation cases and local F001 retrieval interface for the k=3 versus k=5
   evidence-recall comparison against expected source IDs. This uses no additional live LLM
   calls and reports the measured result without presuming an improvement.
7. Test case validation, scoring aggregation, and partial-result handling with deterministic
   unit tests. Do not run live evaluation in CI.

### Phase 4 - Final documentation and submission verification

1. Add the required `docs/deployed.md`, `docs/design-and-evaluation.md`, and
   `docs/ai-tooling.md`; update the README with local setup, app run, evaluation, health
   equivalent, deployed URL, repository link, and demo link when available.
2. Include a text architecture diagram and the two F004 tool sequences, safety behavior,
   transport, and design choices; document exact evaluation case count, scoring definitions,
   results, latency sample count, k comparison, provider model/configuration (not key), and
   limitations.
3. Verify repository artifacts, grader access, demo duration/content, dashboard submission,
   participant count, presenter instructions, and any conditional group agreement manually.
   Store no identity documents. Mark external/manual items verified only with appropriate
   evidence.

## Testing and Verification Strategy

| Layer | Automated verification | Manual verification |
|---|---|---|
| Secret bridge | Focused pytest covers host secret mapping, environment precedence, missing configuration, and secret redaction. | Configure `GROQ_API_KEY` in Community Cloud settings without disclosing it; verify one live request can reach the configured provider. |
| App startup | Existing `AppTest` in `tests/test_chat_interface.py`, included in the full pytest CI job. | Open the deployed app URL and verify it renders. |
| MCP integration | Existing `tests/integration/test_agent_mcp.py` discovers and invokes the stdio server under CI. | Use the deployed UI health equivalent to confirm discovery; then verify a workflow produces actual calls. |
| Index artifact | F001 index tests plus a focused integrity/retrieval check for the committed active snapshot; no CI model download. | Verify the deployed policy search returns expected synthetic evidence; observe first-use model download/cold latency if applicable. |
| Live vertical slice | No provider-dependent CI. Deterministic F004 and F005 tests remain the contract checks. | One deployed `TEST-001` PTO scenario; inspect balance date, HR-002 citation, ordered tool outcomes, and final status. Stop on provider failure without blind retry. |
| CI deployment gate | Existing CI jobs pass on push/PR. | Inspect required `main` status checks and Community Cloud's tracked branch; confirm failed checks cannot be merged to the deployment branch. |
| Evaluation | Unit tests validate dataset coverage, metric aggregation, fixed sample selection, and partial result preservation with synthetic records. | One opt-in sequential Groq run; manually assess groundedness/citations; inspect p50/p95 and k comparison; distinguish provider failures. |
| Submission | Documentation/link/case-shape checks where simple and deterministic. | Confirm deployment/demo/repository links, grader access, recording content/duration, dashboard submission, participant count, and presenter requirements. |

## Requirements-to-Design Traceability

| Requirement | Implementation activity | Verification activity |
|---|---|---|
| QR-003 | Use free Streamlit Community Cloud, existing local embeddings/index, and no paid database or service. | Manually verify account/setup requires no payment, host resource use and current limits; document actual constraints. |
| QR-004 | Reuse Python 3.11, `pyproject.toml`, `requirements.txt`, and README environment instructions. | Existing Python 3.11 CI install; manually follow setup in a clean environment. |
| QR-005 | Update README and `deployed.md` with setup, local run, deployment, and evaluation steps. | Manually follow all instructions; record any external limitation. |
| QR-006 | Preserve existing deterministic index/chunking configuration and use fixed case IDs/order and a fixed latency sample subset. | Existing F001 reproducibility tests; deterministic test of case selection and repeated retrieval comparison. |
| QR-007 | Map host `st.secrets["GROQ_API_KEY"]` to existing environment-backed configuration at the UI boundary; never persist/log it. | Unit tests for mapping/precedence/redaction; manual host secret setup and repository inspection. |
| QR-033 | Deploy the existing app to Streamlit Community Cloud. | Manually open the shareable URL; document an exceptional blocker rather than claiming success. |
| QR-034 | Keep UI and MCP stdio process in one Community Cloud app; add no database. | Inspect deployment configuration and verify app/MCP operation in the hosted smoke test. |
| QR-035 | No separate MCP host is planned, so the conditional MCP URL requirement is not applicable. | Record stdio transport and single-service topology in design/deployment docs. |
| QR-036 | Document host sleep, cold-start, first-use model download, and observed resource limitations. | Manually observe and record actual behavior; do not claim a cold-start metric not measured. |
| QR-037 | Reuse `.github/workflows/ci.yml` for dependency installation, lint/import, integration, and tests. | Review workflow and obtain a passing hosted push/PR Actions run. |
| QR-038 | Reuse AppTest startup coverage and actual `test_agent_mcp.py` MCP discovery/call coverage. | Confirm both checks are included and pass in hosted Actions. |
| QR-039 | Use protected `main` with required existing CI checks; let Community Cloud update only from `main`. | Manually inspect branch rules and Cloud branch setting; verify green required checks before merge. |
| QR-040 | Add 20-30 synthetic cases with gold answers/rubrics across all required categories. | Automated count, ID, category, and rubric validation plus manual content review. |
| QR-041 | Add case-specific evidence review for groundedness and citations. | Human-score returned policy claims against the expected evidence; report numerator/denominator. |
| QR-042 | Score tool selection, workflow completion, clarification/escalation, and action safety from expected outcomes and trace. | Run the single live suite; inspect safe trace/result rows and report each metric denominator. |
| QR-043 | Time 10-20 preselected cases within the same sequential live run; aggregate p50/p95. | Verify raw per-case durations, sample count, calculation, cold/warm notes, and provider errors. |
| QR-044 | Compare F001 retrieval evidence recall for k=3 and k=5 against expected source IDs. | Deterministic local run over the same policy cases; no extra provider calls. |
| QR-045 | Document and justify existing orchestration, MCP/stdio, tool schemas, embeddings, chunking, k, FAISS, host, and safety choices. | Review `design-and-evaluation.md` against the implemented configuration and interfaces. |
| QR-046 | Add a concise text architecture diagram covering UI, agent, MCP, RAG/index, synthetic data, and Groq. | Check every component and connection is represented in the documentation. |
| QR-047 | Document expected PTO and remote-work tool sequences using the existing F004 workflow contract. | Compare documented examples with F004 contracts and actual traces; do not prescribe a fixed model ordering. |
| QR-048 | Add repository/deployment/demo links and share the repository with `quantic-grader`. | Manually open links and verify grader access. |
| QR-049 | Record the required 7-10 minute screen-share with both deployed workflows. | Human review of recording duration and end-to-end results. |
| QR-050 | Follow presenter requirements without checking identity documents into the repository. | Presenter confirms all members speak, appear on camera, and follow the ID instruction; verify no identity files are committed. |
| QR-051 | Prepare the demo outline with tools, arguments, outputs, citations, outcomes, design, deployment, CI/CD, and evaluation. | Review the recording against the checklist. |
| QR-052 | Keep application code, synthetic datasets, MCP server, and tool definitions in the repository. | Inspect tracked files and repository contents. |
| QR-053 | Create `design-and-evaluation.md`, `ai-tooling.md`, and `deployed.md`; update README. | Check required topics, URLs, health equivalent, setup, and cold-start notes. |
| QR-054 | Add evaluation cases, runner, per-case results, and metric report under `evaluation/`. | Reproduce deterministic k comparison and review the one live run's script/config/results. |
| QR-055 | Prepare the project-dashboard submission and conditional group agreement if requested. | Manual submitter confirmation; not a CI-verifiable requirement. |
| QR-056 | Disclose AI tools, their use, strengths, limitations, and responsibility; cite external material. | Manual review of `ai-tooling.md` and documentation citations. |
| QR-057 | Integrate the existing RAG, MCP, agent, workflows, and chat; deliver deployment and evaluation. | Hosted PTO smoke test plus live evaluation evidence; preserve partial/unverified statuses. |
| QR-058 | Retain documented local operation and synthetic workflows. | Follow local README setup and run both workflows using existing deterministic checks. |
| QR-059 | Do not change project membership; verify assignment limit at submission. | Manual confirmation that there are at most three project members. |
| QR-060 | Include deployed URL, health equivalent if available, and cold-start notes in `deployed.md`. | Manually open URL and health view; compare documentation with actual host behavior. |

QR-035 is conditional and not applicable to the selected stdio, single-service deployment.
QR-050, QR-055, and QR-059 require human verification. No local or CI result substitutes for
the hosted request, provider-backed evaluation, branch-rule setup, or final presentation.

## Project Structure

### Documentation (this feature)

```text
specs/006-deployment-ci-cd-evaluation/
├── plan.md
├── research.md
├── data-model.md
└── quickstart.md
```

### Source and tests

```text
.github/
└── workflows/
    └── ci.yml                         # Reuse; add named AppTest step, keep existing matrix
.hr_rag_index/                         # Commit active derived FAISS snapshot for deployment
src/
└── hr_app/
    └── app.py                         # Minimal st.secrets-to-environment bridge at UI boundary
requirements.txt                       # Ensure local src package is installed by Community Cloud
evaluation/
├── cases.json                         # 20-30 synthetic cases and rubrics
├── run_evaluation.py                  # One opt-in sequential Groq run and local k comparison
├── results.jsonl                      # Append-only, privacy-safe per-case results
└── results.md                         # Aggregate metrics, latency, ablation, limitations
tests/
├── test_chat_interface.py             # Extend for host secrets if needed; AppTest startup
└── unit/
    └── test_f006_evaluation.py        # Case validation, scoring, partial result handling
docs/
├── deployed.md
├── design-and-evaluation.md
└── ai-tooling.md
README.md                              # Local, evaluation, health, deployment, and links
```

**Structure Decision**: Keep F006 in the existing single Python project. Add only the
evaluation folder, required assignment documents, a host-secret bridge at the existing UI
boundary, and the derived policy index needed by a clean deployment. Do not add a new
package, service, workflow engine, database, or model provider. Do not create `tasks.md`;
that belongs to `/speckit.tasks`.

## Complexity Tracking

No constitution exception or additional infrastructure is proposed. The generated index and
secret bridge are required to make the current F001/F003/F005 path run in a clean Streamlit
deployment without startup-time index building or changing the Groq integration.
