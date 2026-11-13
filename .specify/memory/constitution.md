<!--
Sync Impact Report
Version change: 1.0.0 -> 1.1.0
Modified principles: III. Modular Separation; IV. Grounded AI Responses;
  V. MCP-Compliant Tool Integration; VII. Automated Testing and Reproducibility
Added sections: Assignment Delivery Requirements
Removed sections: none
Follow-up: Confirm the ratification date.
-->

# Lightweight HR AI Chatbot Constitution

## Core Principles

### I. Simplicity First

- The project MUST implement only capabilities needed for the Quantic assignment.
- Designs MUST prefer the simplest approach that meets a stated requirement. New abstractions,
  dependencies, and infrastructure MUST have a documented need.

### II. Python-First Implementation

- Application behavior and supporting automation MUST use Python unless a Quantic requirement
  makes another technology necessary. Any exception MUST be justified in the implementation plan.
- Dependencies and supported Python versions MUST be documented and reproducible.

### III. Modular Separation

- User interaction, agent orchestration, retrieval and document handling, response generation,
  MCP client and server, and mock data MUST have distinct responsibilities and explicit interfaces.
- Components MUST be independently testable without splitting the application into multiple
  deployed services.

### IV. Grounded AI Responses

- Factual policy claims MUST be grounded in retrieved, in-scope source material and MUST include
  citations that identify the supporting source and allow users to locate the relevant content.
  Employee-specific claims MUST be grounded in the relevant synthetic tool results.
- When evidence is missing, insufficient, or conflicting, the chatbot MUST communicate that
  limitation rather than inventing an answer or citation.
- Out-of-corpus policy questions MUST be refused or redirected, and policy facts MUST be
  distinguished from recommendations.
- Retrieval and source content MUST be treated as data, not as instructions that override
  application rules.

### V. MCP-Compliant Tool Integration

- Tool integrations in scope MUST use the Model Context Protocol and its supported SDK or
  protocol interfaces, including tool discovery, declared input schemas, and structured errors.
- Tool inputs MUST be validated and tool failures MUST be surfaced; the application MUST NOT
  represent a failed tool call as successful.
- MCP integration MUST remain compatible with the single-service deployment constraint.
- The agent MUST discover and invoke at least five tools through one or more MCP servers, with
  at least one tool retrieving policy evidence and at least one using mock structured data or
  performing a mock operation. Direct calls that bypass MCP do not satisfy this requirement.

### VI. Synthetic Data and Safe Operations

- HR documents, records, and examples MUST be synthetic and clearly identified as such; real
  employee information and real HR system integrations MUST NOT be used.
- Tools MUST be read-only by default. Any in-scope state-changing operation MUST affect only
  synthetic data, require explicit user confirmation, and provide a documented way to reverse
  or reset the change.
- Credentials MUST be supplied through environment configuration, not committed to the project;
  logs MUST NOT expose credentials or unnecessary user input.

### VII. Automated Testing and Reproducibility

- Changes MUST include automated tests appropriate to their behavior, including retrieval and
  citation grounding, insufficient-evidence handling, MCP tool contracts and failures, and the
  safety of any state-changing operations when those capabilities are present.
- CI MUST run on push or pull request, install dependencies, perform a build, start, or import
  check, and run automated tests, including app startup and MCP discovery or a tool call.
  Deployment MUST occur only after these checks pass.
- Tests MUST use synthetic fixtures and MUST NOT require real HR systems. External model or
  service calls MUST be replaceable with deterministic test doubles for routine test runs.
- Setup, local execution, deployment, evaluation, dependency installation, configuration, test
  commands, and data initialization or reset MUST be documented so another developer can
  reproduce the project. Fixed seeds MUST be used where applicable.

## Project Constraints

- Deploy as one application service; modular components and MCP tool integration MUST NOT
  require separately deployed services.
- Infrastructure and model choices MUST be compatible with free-tier use, including documented
  limits and any required external dependencies. Do not assume a paid plan is available.
- The Quantic assignment requirements govern feature scope and acceptance. Where those
  requirements are ambiguous, record the gap and seek clarification rather than inventing
  requirements. The authoritative assignment is
  [Quantic AI Agent project.pdf](../../docs/Quantic%20AI%20Agent%20project.pdf).
- Real HR integrations, real employee data, and features beyond the assignment scope are
  prohibited.

## Assignment Delivery Requirements

- The synthetic policy corpus MUST cover realistic HR questions and target 5-20 short documents
  totaling 30-120 pages. Ingestion MUST parse and clean at least two source formats where feasible,
  use a justified chunking strategy and embeddings, and maintain a lightweight vector index with
  document title or ID, section, and source snippet metadata.
- RAG MUST retrieve top-k policy chunks and provide their content and metadata to the model.
  The system MUST support at least one question requiring evidence from multiple documents.
- The agent MUST interpret intent, decide whether retrieval alone is sufficient, select and call
  MCP tools when needed, and synthesize the response. It MUST support at least two multi-step HR
  workflows combining policy evidence and synthetic structured data.
- The web application MUST provide a chat interface and a chat endpoint or equivalent returning
  answers, citations, snippets, and concise tool-call traces. A health endpoint or equivalent
  MUST return JSON app status and MCP connectivity where feasible. Both demo workflows MUST be
  reproducible through the UI or an API client.
- Operational traces MUST show selected tools, arguments, outputs, retrieved sources, final
  answer basis, and any escalation decision, without exposing hidden chain-of-thought. Missing
  identifiers, ambiguous requests, insufficient evidence, and unavailable tools MUST result in
  clear clarification or failure handling.
- The application MUST run locally and be deployed to a free-tier or zero-cost host at a
  shareable URL, unless a platform outage or exceptional deployment issue is documented. The
  deployment MUST remain a single service; cold-start behavior and any limits MUST be documented.
- Evaluation MUST use 20-30 questions or tasks with gold answers or rubrics covering policy
  questions, multi-document questions, tool use, ambiguous requests, and out-of-scope requests.
  Report groundedness, citation accuracy, tool selection accuracy, workflow completion,
  escalation or clarification accuracy, and action-safety pass rate. Report p50 and p95 latency
  over 10-20 representative queries or tasks, separating cold and warm starts where possible,
  and include at least one ablation or comparison.
- Submission documentation MUST include setup and evaluation instructions; design and evaluation
  details; AI tooling usage and limitations; deployment and health URLs; evaluation data, scripts,
  and results; synthetic mock data; and MCP server and tool definitions. Document the architecture,
  key design choices, tool schemas, transport, discovery, safety, and expected call sequence for
  both demo workflows.
- The submission MUST include repository and recorded presentation links and the deployed URL
  in the README. The 7-10 minute screen-share demo MUST show both deployed workflows end to end,
  explain tool names, arguments, outputs, citations, and final behavior, and summarize design,
  deployment, CI/CD, and evaluation. Follow the assignment's remaining submission and presentation
  instructions.

## Development Workflow and Quality Gates

- Each specification MUST trace its features and acceptance criteria to the Quantic assignment
  and identify any assumptions or unresolved requirements.
- Each implementation plan MUST check all applicable principles and constraints before design
  and again after design. Any proposed exception MUST be resolved through the amendment process
  before implementation.
- Tasks MUST include appropriate automated tests and documentation updates. Review MUST verify
  citations, failure behavior, synthetic-data safety, deployment scope, and reproducibility
  where applicable.
- Before completion, run the relevant automated tests and record any validation that could not
  be performed, with its reason.

## Governance

- This constitution governs project specifications, plans, implementation, and review. A
  conflict with an authoritative assignment requirement MUST be brought to the project owner
  for resolution before proceeding.
- Amendments MUST document the proposed change, rationale, impact on existing work, and any
  migration needed; the project owner MUST approve the amendment before it takes effect.
- Constitution versions follow semantic versioning: MAJOR for incompatible principle removals
  or redefinitions, MINOR for new principles or materially expanded guidance, and PATCH for
  non-semantic clarifications and corrections.
- Reviews MUST check compliance with this constitution. Exceptions require an approved
  amendment rather than an undocumented waiver.

**Version**: 1.1.0 | **Ratified**: TODO(RATIFICATION_DATE): Confirm project owner approval date | **Last Amended**: 2026-11-10
