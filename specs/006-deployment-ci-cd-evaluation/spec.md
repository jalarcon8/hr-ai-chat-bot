# Feature Specification: Deployment, CI/CD, and Evaluation

**Feature ID**: F006

**Feature Branch**: `006-deployment-ci-cd-evaluation`

**Created**: 2026-11-16

**Status**: Approved - clarification complete; ready for implementation

**Input**: Integrate, deploy, evaluate, document, and prepare the completed HR chatbot
submission so a grader can access the application, reproduce its workflows, review results,
and inspect the repository and recorded demonstration.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reproduce the application locally and access the deployment (Priority: P1)

As a grader or developer, I want to install and run the project locally and access a
shareable deployed application so that I can reproduce its workflows and inspect the
submission.

**Why this priority**: Local reproducibility and a grader-accessible application are the
foundation for validating the integrated project and completing the assignment.

**Independent Test**: Follow the documented setup in a clean environment, start the
application, exercise both F004 workflows, and check the deployed application and its health
status.

**Acceptance Scenarios**:

1. **Given** a clean supported local environment, **When** a developer follows the README,
   **Then** they can install documented dependencies, configure required secrets without
   committing them, start the application, and exercise both workflows.
2. **Given** the selected Streamlit Community Cloud configuration meets the project
   constraints, **When** the application is deployed, **Then** the README and deployment
   documentation provide a working shareable URL and the available health URL or equivalent.
3. **Given** the host suspends or otherwise delays an idle service, **When** a grader opens
   the application, **Then** the documentation describes expected cold-start behavior and
   relevant free-tier limits without promising unsupported availability or performance.
4. **Given** deployment cannot be completed because of a platform outage or another
   exceptional issue, **When** the submission is reviewed, **Then** the issue, evidence,
   impact, and remaining steps are documented; an unavailable deployment is not described as
   successful.

### User Story 2 - Verify changes through CI before deployment (Priority: P1)

As a maintainer, I want automated checks to run for repository changes and to gate
deployment so that broken application or MCP integration changes are not published.

**Why this priority**: The assignment requires repeatable automated checks and explicitly
requires deployment to occur only after those checks pass.

**Independent Test**: Inspect and run the workflow on a change; verify dependency
installation, an application build/start/import check, automated tests, application startup,
and MCP discovery or a simple tool call, then verify that failed checks prevent deployment.

**Acceptance Scenarios**:

1. **Given** a push or pull request, **When** the CI workflow runs, **Then** it installs the
   documented dependencies, performs a build, start, or import check, and runs the
   repository's automated tests.
2. **Given** the CI workflow, **When** its integration checks run, **Then** at least one
   automated application-start test and one MCP discovery or simple MCP tool-call test are
   executed.
3. **Given** the existing CI checks have not passed, **When** a change targets the
   auto-deployed main branch, **Then** branch protection prevents the merge and the
   deployment does not update.
4. **Given** routine automated checks run, **When** they exercise the app or agent, **Then**
   they use synthetic fixtures and deterministic replacements where needed and do not
   require real HR services or provider credentials.

### User Story 3 - Review evaluation cases and measured results (Priority: P1)

As a grader or project reviewer, I want a reproducible evaluation set, scoring method, and
reported measurements so that I can assess answer quality, workflow behavior, and performance.

**Why this priority**: A measured evaluation is required to demonstrate that the integrated
agent is grounded, uses tools appropriately, completes workflows safely, and has characterized
latency.

**Independent Test**: Run the documented evaluation using its included data and scripts;
inspect case coverage, expected answers or rubrics, metric definitions, reported results,
latency calculations, and at least one comparison or ablation.

**Acceptance Scenarios**:

1. **Given** the evaluation suite, **When** its cases are inspected, **Then** it contains
   20-30 questions or tasks with gold answers or rubrics covering straightforward policy,
   multi-document, tool-requiring, ambiguous, and out-of-scope requests.
2. **Given** the evaluation suite is run once against the existing Groq integration, **When**
   results are reported, **Then** they include groundedness, citation accuracy,
   tool-selection accuracy, workflow completion, escalation or clarification accuracy, and
   action-safety pass rate, scored against case-specific rubrics and observable evidence.
3. **Given** 10-20 representative cases from that evaluation run are timed, **When** latency
   results are reported, **Then** p50 and p95 are calculated and cold and warm results are
   separated where possible if cold starts affect latency.
4. **Given** the evaluation includes a comparison or ablation, **When** results are reported,
   **Then** at least one controlled comparison is described with its changed condition and
   observed results; no unmeasured improvement is claimed.
5. **Given** an evaluation depends on a live provider or hosted service, **When** it is run,
   **Then** its external dependency, configuration, and limitations are documented, and
   routine automated tests remain runnable without live provider calls.

### User Story 4 - Inspect the design and complete the submission (Priority: P2)

As a grader, I want the repository and presentation materials to explain the system,
evaluation, AI-tooling use, deployment, and two workflows so that I can review how the
submission was built and reproduce the demonstrated behavior.

**Why this priority**: These materials make the project auditable and satisfy the assignment's
final delivery and presentation requirements.

**Independent Test**: Follow the README and evaluation instructions, inspect the required
documentation and repository artifacts, and compare the recorded presentation with the
submission checklist.

**Acceptance Scenarios**:

1. **Given** a reviewer opens the repository, **When** they follow its documentation,
   **Then** it includes setup, local run, deployment, evaluation, architecture and design
   choices, AI-tooling usage and limitations, and the available deployment and health URLs.
2. **Given** the design documentation is reviewed, **When** the system is described, **Then**
   it identifies the web app, agent orchestrator, MCP client/server and transport, RAG index,
   synthetic data, LLM provider, tool schemas, safety behavior, and expected call sequences
   for both demo workflows.
3. **Given** the repository is inspected, **When** the required submission artifacts are
   checked, **Then** it contains synthetic mock data where used, MCP server and tool
   definitions, and an evaluation directory or equivalent with cases, expected answers or
   rubrics, scripts, and results.
4. **Given** the final presentation is recorded, **When** it is reviewed, **Then** it is a
   7-10 minute screen-share with voiceover showing both deployed workflows end to end and
   explaining tool names, arguments, outputs, citations, final behavior, design, deployment,
   CI/CD, and evaluation.
5. **Given** the presentation is prepared, **When** it is recorded, **Then** all group
   members speak, are on camera, and show government ID as required by the assignment;
   identity documents are not stored in the repository.
6. **Given** submission is ready, **When** its links and access are checked, **Then** the
   README includes the deployed URL, repository link, and recorded-demo link, the
   repository is shared with `quantic-grader`, and the project has no more than three
   members; dashboard submission and any conditionally requested group agreement are
   handled by the submitter.

### Edge Cases

- Streamlit Community Cloud's current availability, resource limits, persistence, or
  cold-start behavior differ from assumptions or change; these facts are validated and
  documented rather than assumed.
- A deployment secret is absent or invalid; setup and deployment report the configuration
  problem without exposing secret values or returning a success-shaped result.
- A CI test fails, is skipped, or cannot run on the configured platform; results distinguish
  pass, failure, skip, and unverified status, and a failure cannot be bypassed to deploy.
- A live evaluation case encounters a provider or quota failure; it is recorded separately
  from a functional failure, and the evaluation is not repeatedly rerun just to fill the
  sample.
- Evaluation cases do not cover a required category or fall outside the 20-30 case range;
  the evaluation is incomplete and is not reported as meeting the requirement.
- Too few representative requests are timed, or the cold/warm distinction is not applicable;
  the report states the actual sample count and limitation rather than implying compliance.
- No acceptable comparison data are available; the comparison is recorded as incomplete
  rather than claiming an ablation result.
- A deployment is unavailable because of an exceptional issue; local operation, evidence of
  the issue, and remaining limitations are documented, without claiming the shareable
  deployment criterion is satisfied.
- Submission links, host status, evaluation results, or demo recording are not yet available;
  placeholders or pending status are explicit and are not represented as verified artifacts.

## Scope Boundaries

**In scope**: Single-service free-tier or zero-cost deployment and documented local
operation; environment configuration, shareable URL, health information, and cold-start
notes; CI checks on push or pull request, including application startup and MCP discovery or
a tool call; test-gated deployment; a 20-30 case evaluation suite and required quality,
behavior, latency, and comparison results; project-wide design, evaluation, AI-tooling,
deployment, README, and submission materials; and the recorded demo and final submission
checklist.

**Out of scope**: New HR capabilities or workflows; real HR systems or employee data; a
separately deployed MCP service; infrastructure that requires a paid database or paid-tier
service; unsupported quality or availability guarantees; and changes to project-level
governance documents or assignment requirements.

## Dependencies

- **F001 - HR Policy RAG**: supplies corpus, retrieval, and citation behavior for integration,
  evaluation, and documentation.
- **F002 - MCP Tool Integration**: supplies MCP server, tool schemas, synthetic data, and
  discovery/call behavior for CI, evaluation, and architecture documentation.
- **F003 - Agent Orchestration**: supplies agent behavior, tool selection, traces, and
  safety controls to evaluate and describe.
- **F004 - HR Agentic Workflows**: supplies the two demo workflows, representative scenarios,
  and expected tool sequences.
- **F005 - Chat Interface**: supplies the grader-facing browser application and health
  equivalent to run locally, deploy, and exercise in the recorded demo.

F006 is the final integration and delivery feature. Component evidence from F001-F005 may be
used, but it does not replace required integrated, hosted, CI, or submission verification.

## MVP Classification

**Required for F006**

- Integrate and document local operation and one shareable, single-service deployment using
  a validated free-tier or zero-cost host, unless an exceptional deployment issue is
  documented.
- Configure and document environment variables and secrets without committing or exposing
  credentials; report health, cold-start behavior, and relevant host/provider limitations.
- Run dependency installation, an application build/start/import check, automated tests,
  application startup, and MCP discovery or a simple tool call in CI on push or pull request.
- Gate deployment on successful required checks.
- Supply 20-30 evaluation questions/tasks with expected answers or rubrics and the required
  coverage categories; provide reproducible scoring and results for all required quality,
  workflow, escalation, safety, and latency measures.
- Measure p50 and p95 latency over 10-20 representative tasks and include at least one
  controlled ablation or comparison, documenting limitations and external dependencies.
- Provide required architecture, design and evaluation, AI-tooling, deployment, setup,
  repository, evaluation, and submission documentation and artifacts.
- Verify the final README, repository access, deployed and recorded-demo links, and
  presentation requirements; do not claim a pending item is complete or verified.

**Supporting**

- Reuse F001-F005 interfaces, synthetic fixtures, deterministic tests, workflow scenarios,
  citations, and safe traces. Record prior-feature evidence with its actual scope and status.

**Deferred from F006, not dropped from the project**

- Any outstanding upstream F001-F005 component work remains with its owning feature. F006
  integrates and verifies required end-to-end behavior; it does not introduce new HR
  features to compensate for component gaps.
- The selected host and provider are Streamlit Community Cloud and the existing Groq
  integration. Account access, no-payment eligibility, resource ceilings, quota, and
  compatibility with the same-service MCP subprocess remain validation gates; no deployment
  or quota outcome is assumed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST run locally using documented dependency installation,
  environment configuration, application startup, and workflow instructions. Required
  secrets MUST be supplied through environment configuration or the host's secret store and
  MUST NOT be committed or exposed in logs or documentation. The hosted Groq secret MUST be
  made available to the existing agent configuration without changing providers.
- **FR-002**: The application MUST target Streamlit Community Cloud as the free or zero-cost
  host and use the existing Streamlit app and same-service MCP stdio subprocess. The
  selected setup MUST NOT require payment information; if account setup requires it, record
  the blocker and seek approval before selecting another host. The deployment MUST provide
  a shareable URL unless a platform outage or exceptional deployment issue is documented
  with its evidence and impact. It MUST NOT require a paid database or separately deployed
  MCP service. If the platform cannot run the existing application within its limits,
  document the blocker and seek approval before changing hosts or architecture.
- **FR-003**: The README and deployment documentation MUST state the deployment URL, health
  URL when available, environment configuration, expected cold-start behavior when
  applicable, and relevant hosting or external-provider limitations.
- **FR-004**: The existing `.github/workflows/ci.yml` MUST be extended rather than
  duplicating CI. It MUST continue to run on push or pull request, install project
  dependencies, perform its existing lint, import, MCP integration, and pytest checks, and
  include at least one automated application-start check and one MCP discovery or simple
  tool-call check.
- **FR-005**: The main branch MUST require the relevant existing CI checks before merge.
  Streamlit Community Cloud MUST deploy from that protected branch, so deployment updates
  occur only after required checks pass. Failed, skipped, or unavailable checks MUST NOT be
  represented as passed.
- **FR-006**: Routine automated checks MUST use synthetic data and deterministic doubles
  where required and MUST NOT require real HR systems or live model-provider credentials.
  Fixed seeds MUST be used for applicable evaluation sampling or chunking. Any opt-in
  provider-dependent evaluation MUST document its required configuration and limits.
- **FR-007**: The project MUST provide 20-30 evaluation questions or tasks, each with a gold
  answer or scoring rubric, covering straightforward policy questions, multi-document
  questions, tool-requiring requests, ambiguous requests, and out-of-scope requests.
- **FR-008**: One live evaluation run MUST report groundedness, citation accuracy,
  tool-selection accuracy, workflow completion rate, escalation or clarification accuracy,
  and action-safety pass rate. Scores MUST use case-specific gold answers or rubrics and
  observable citations, tool traces, and outcomes; use manual evidence review for grounding
  and citations and trace-based scoring for operational metrics. Report metric numerators
  and denominators. The evaluation MUST NOT require an LLM judge. Provider or quota
  failures MUST be recorded separately from functional failures.
- **FR-009**: The evaluation MUST report p50 and p95 end-to-end latency over 10-20
  representative cases selected from the same 20-30 case run. Requests MUST be issued
  sequentially at a controlled rate. The report MUST separate cold and warm starts where
  possible if cold starts affect latency, and MUST identify sample count, measurement
  conditions, and provider or quota failures.
- **FR-010**: The evaluation MUST compare retrieval evidence at k=3 and k=5 against the
  evaluation cases' expected source IDs, reporting the measured evidence-recall comparison.
  This comparison MUST reuse the evaluation corpus and MUST NOT require additional live LLM
  calls. It MUST report observed results without claiming unmeasured effects.
- **FR-011**: The submission MUST include setup and evaluation instructions; design and
  evaluation details; AI-tooling usage, strengths, and limitations; deployment and health
  information; evaluation data, scripts, and results; synthetic mock data where used; and
  MCP server and tool definitions.
- **FR-012**: Design documentation MUST describe the architecture and justify applicable
  orchestration, MCP server and transport, tool schemas, embeddings, chunking, retrieval k,
  vector store, deployment, and safety choices. It MUST show or describe the web app, agent,
  MCP client/server, RAG index, synthetic data, and LLM provider, and document expected
  tool-call sequences for both demo workflows.
- **FR-013**: The README MUST include the repository link, deployed URL, and recorded-demo
  link when available. The project MUST provide the required `design-and-evaluation.md`,
  `ai-tooling.md`, and `deployed.md` content and an evaluation directory or equivalent
  containing cases, expected answers or rubrics, scripts, and results.
- **FR-014**: The final recorded screen-share MUST be 7-10 minutes, include voiceover, and
  show both deployed workflows end to end. It MUST explain the tools, relevant arguments and
  outputs, citations, final behavior, design, deployment, CI/CD, and evaluation.
- **FR-015**: The submitter MUST verify the assignment's participant limit of no more than
  three people; presenter requirements (all group members speak, are on camera, and show
  government ID); repository access; repository/demo link; dashboard submission; and
  conditional group-agreement requirements. Government identity documents MUST NOT be
  stored in the repository.
- **FR-016**: The project MUST distinguish local component tests, integrated end-to-end
  checks, hosted checks, and submission artifacts in its verification record. It MUST NOT
  mark a requirement Verified without supporting evidence, and MUST document checks that
  remain unavailable or incomplete.
- **FR-017**: F006 MUST NOT add HR capabilities, real HR integrations, real employee data,
  paid-database requirements, or separately deployed MCP services.

### Key Entities

- **Deployment configuration**: The single-service host, application entry point, runtime
  settings, secrets, health URL or equivalent, and documented resource and cold-start
  constraints.
- **CI run**: A repository change's dependency-install, build/start/import, test,
  application-start, and MCP-check outcomes, including failed, skipped, or unavailable
  states.
- **Evaluation case**: A synthetic question or task, its category, expected answer or rubric,
  and observable evidence or behavior used for scoring.
- **Evaluation result**: Metric definition, sample, scoring outcome, latency measurements,
  comparison condition, and documented limitations.
- **Submission artifact**: A required README or supporting document, evaluation asset,
  repository/demo/deployment link, access check, or recorded presentation.
- **Verification record**: Evidence and status for local, integrated, CI, hosted, evaluation,
  and submission checks, without conflating one type of evidence with another.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean-environment reviewer can follow documented dependency installation,
  configuration, and startup steps to run the application locally and reproduce both demo
  workflows.
- **SC-002**: The deployment is accessible at a shareable URL on a validated free-tier or
  zero-cost single-service host, or the exceptional issue and its impact are documented
  without representing deployment as complete.
- **SC-003**: CI is configured for push or pull request and records dependency installation,
  build/start/import validation, automated tests, an application-start check, and MCP
  discovery or tool-call check; a required check failure blocks deployment.
- **SC-004**: The evaluation contains 20-30 cases and explicitly covers all five required
  request categories, each with a gold answer or rubric.
- **SC-005**: Reported evaluation results include all six required quality and behavior
  measures, with documented methodology and results that can be traced to the evaluation
  cases.
- **SC-006**: Latency reporting includes p50 and p95 computed from 10-20 representative
  queries or tasks, records the measurement conditions, and separates cold and warm results
  where possible when cold starts affect latency.
- **SC-007**: At least one ablation or comparison reports the changed condition and measured
  outcome; no improvement is claimed without supporting results.
- **SC-008**: The README and required supporting materials contain reproducible setup,
  deployment, health, evaluation, design, AI-tooling, and submission information; the
  evaluation assets, synthetic data, and MCP definitions are present.
- **SC-009**: The recorded demo satisfies the 7-10 minute duration, voiceover, deployed
  end-to-end demonstration of both workflows, and required explanatory content, or its
  incomplete status is explicitly recorded.
- **SC-010**: Every reported verification status is supported by evidence appropriate to its
  scope; component-level results are not described as hosted or end-to-end verification.

## Assumptions

- Streamlit Community Cloud is the selected host, and the F005 Streamlit application and
  health equivalent are the deployment entry points.
- A single-service Streamlit Community Cloud deployment can run the existing MCP stdio
  subprocess within its free-tier constraints; this must be verified by a hosted smoke test
  rather than assumed.
- The project may document an exceptional deployment issue, as allowed by QR-033, but doing
  so does not imply the shareable deployment requirement has been met.
- The existing Groq integration remains the only provider for live deployment and the one
  bounded evaluation run. `GROQ_API_KEY` is configured directly in host secrets and is not
  shared in source control or chat.
- The live evaluation is a single sequential run of 20-30 cases; its 10-20 latency samples
  are selected from those same cases. A provider/quota failure is retained and reported
  separately, with no unnecessary full rerun.
- Evaluation scoring uses case-specific rubrics and observable application evidence without
  an LLM judge. The retrieval comparison uses expected source IDs to compare evidence
  recall at k=3 and k=5 without additional live LLM calls.
- The existing `.github/workflows/ci.yml`, pytest suite, Ruff check, import checks, and MCP
  integration test are reused; the workflow is extended for application startup, and
  protected-main required checks gate Streamlit Community Cloud's deployment updates.
- Existing local validation records for F001-F005 are evidence only for their documented
  scope. Hosted CI, deployment, integrated UI-to-MCP acceptance, live evaluation, and final
  submission checks require their own evidence where applicable.
- All evaluation fixtures and employee examples remain synthetic.
- The assignment's government-ID demonstration instruction is satisfied by presenter
  verification during recording; identity documents are not collected into or stored in
  the repository.
- The submitter is responsible for external account, grader-sharing, dashboard, recording,
  and any conditional group-agreement actions.

## Assignment Requirements Traceability

| Assignment requirement | Functional requirements | Success criteria | Acceptance scenarios |
|---|---|---|---|
| QR-003 - Free or zero-cost choices and modest resource use. | FR-002, FR-003, FR-017 | SC-002, SC-008 | US1-AS2-AS4 |
| QR-004 - Reproducible environment and dependency list. | FR-001 | SC-001, SC-008 | US1-AS1 |
| QR-005 - README setup, local run, deployment, and evaluation instructions. | FR-001, FR-003, FR-011, FR-013 | SC-001, SC-008 | US1-AS1-AS3, US4-AS1 |
| QR-006 - Fixed seeds where applicable. | FR-006-FR-008 | SC-004-SC-005 | US3-AS1-AS2 |
| QR-007 - Environment-based secrets, not committed. | FR-001, FR-003 | SC-001, SC-008 | US1-AS1 |
| QR-033 - Shareable free-tier/zero-cost deployment, subject to documented exception. | FR-002, FR-003 | SC-002 | US1-AS2-AS4 |
| QR-034 - Single service; no paid database required. | FR-002, FR-017 | SC-002 | US1-AS2 |
| QR-035 - Environment-configured MCP URL if separately deployed; conditional. | FR-002, FR-003 | SC-002, SC-008 | US1-AS2 |
| QR-036 - Cold-start behavior documented when applicable. | FR-003 | SC-008 | US1-AS3 |
| QR-037 - CI checks on push/PR, dependency install, build/start/import, and tests. | FR-004 | SC-003 | US2-AS1 |
| QR-038 - Automated app-start and MCP discovery/tool-call checks. | FR-004 | SC-003 | US2-AS2 |
| QR-039 - Deployment only after checks pass. | FR-005 | SC-003 | US2-AS3 |
| QR-040 - 20-30 evaluation cases and required categories. | FR-007 | SC-004 | US3-AS1 |
| QR-041 - Groundedness and citation accuracy. | FR-008 | SC-005 | US3-AS2 |
| QR-042 - Tool selection, workflow completion, escalation/clarification, and action safety. | FR-008 | SC-005 | US3-AS2 |
| QR-043 - p50/p95 over 10-20 representative requests; cold/warm where applicable. | FR-009 | SC-006 | US3-AS3 |
| QR-044 - At least one ablation or comparison. | FR-010 | SC-007 | US3-AS4 |
| QR-045 - Justified design choices. | FR-012 | SC-008 | US4-AS2 |
| QR-046 - Architecture diagram or description. | FR-012 | SC-008 | US4-AS2 |
| QR-047 - Both demo tasks and expected MCP sequences. | FR-012 | SC-008 | US4-AS2 |
| QR-048 - Repository and recorded-demo links, deployed URL, and grader access. | FR-013, FR-015 | SC-002, SC-008 | US4-AS6 |
| QR-049 - 7-10 minute recording with both deployed workflows. | FR-014 | SC-009 | US4-AS4 |
| QR-050 - Presenter participation, camera, and government-ID instruction; no ID stored in repo. | FR-015 | SC-009 | US4-AS5 |
| QR-051 - Explain tools, arguments, outputs, citations, behavior, design, deployment, CI/CD, and evaluation. | FR-014 | SC-009 | US4-AS4 |
| QR-052 - Repository contains code, synthetic mock data, and MCP server/tool definitions. | FR-011, FR-013 | SC-008 | US4-AS3 |
| QR-053 - README and required design, AI-tooling, and deployment documentation. | FR-003, FR-011, FR-013 | SC-008 | US4-AS1 |
| QR-054 - Evaluation cases, rubrics, scripts, and results. | FR-007-FR-010, FR-013 | SC-004-SC-007 | US3-AS1-AS5, US4-AS3 |
| QR-055 - Dashboard submission and conditional group agreement. | FR-015 | SC-008 | US4-AS6 |
| QR-056 - Appropriate citations, AI tooling disclosure, and responsibility. | FR-011, FR-013 | SC-008 | US4-AS1 |
| QR-057 - Integrated, evaluated agentic HR system. | FR-002, FR-004, FR-007-FR-012 | SC-001-SC-008 | US1-AS1-AS2, US2-AS1-AS2, US3-AS1-AS5, US4-AS1-AS3 |
| QR-058 - Local development operation. | FR-001 | SC-001 | US1-AS1 |
| QR-059 - Individual or group of no more than three. | FR-015 | SC-008 | US4-AS6 |
| QR-060 - `deployed.md` includes URL, health URL if available, and cold-start notes. | FR-003, FR-013 | SC-008 | US1-AS2-AS3, US4-AS1 |

QR-001 and QR-008-QR-032 are owned by F001-F005. F006 integrates and may use their
evidence but does not change their ownership or mark their requirements verified solely
from final-delivery activity. QR-050, QR-055, and QR-059 include presenter or submitter
actions that repository tests cannot establish; the final checklist must identify the
responsible human verification.

## Clarification Outcomes and Remaining Validation

The following decisions were confirmed for the smallest demonstrable MVP:

- **Host**: Use Streamlit Community Cloud with the existing F005 Streamlit app. Use its
  configured Python 3.11 runtime and host secrets; do not add a separate MCP service or
  payment-dependent infrastructure. Record actual resource, sleep/cold-start, and account
  limitations at deployment time. See the [deployment
  guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
  [app management limits](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app),
  and [secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
- **Deployment gate**: Reuse `.github/workflows/ci.yml`; configure required CI checks on
  protected `main` and let Streamlit Community Cloud update from `main` after successful
  merges.
- **Provider**: Reuse Groq and configure `GROQ_API_KEY` in host secrets. Do not add a second
  provider unless Groq cannot support the required live demonstration; report that blocker
  before expanding scope. Streamlit secrets are exposed through `st.secrets`, while the
  current provider reads process environment or `.env`; verify the integration and add
  only the minimal secure bridge needed to provide the secret to the existing agent config.
  Preserve local environment configuration and never log or persist the secret.
- **Evaluation**: Run the 20-30 case live suite once, sequentially, using Groq. Choose 10-20
  latency samples from the same case run. Use case rubrics and observable traces/evidence,
  without an LLM judge. Record provider/quota failures separately and do not repeat the run
  unnecessarily.
- **Comparison**: Compare expected-source evidence recall at the existing baseline k=5 with
  k=3 using the same evaluation cases; this retrieval-only comparison does not add live
  provider calls.
- **Conditional MCP URL requirement**: QR-035 is not applicable to this single-service
  deployment because the MCP server is not separately deployed.

The hosted smoke test MUST verify app startup, the MCP stdio subprocess, secure availability
of the Groq secret to the existing provider configuration, and both demo workflows within
the selected service limits. If Community Cloud cannot support the existing single-service
architecture or the required no-payment setup, record the exact blocker and seek approval
before changing hosts or architecture. Host limits and quota availability can change and
MUST be verified at implementation time.

Nonblocking details, including the exact cold-start sampling condition and final submission
account steps, are documented with actual deployment/evaluation evidence. The presenter
remains responsible for the assignment's government-ID demonstration instruction; identity
documents MUST NOT be stored in source control.
