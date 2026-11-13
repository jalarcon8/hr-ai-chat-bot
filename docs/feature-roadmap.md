# HR AI Chatbot Feature Roadmap

## Purpose and baseline

This roadmap divides the [Quantic assignment](requirements/Quantic%20AI%20Agent%20project.pdf)
into six proposed features. The [requirements matrix](requirements/traceability.md) identifies
primary ownership, supporting features, and verification for each assignment requirement.
The [constitution](../.specify/memory/constitution.md) governs implementation. These documents
are planning guidance, not evidence that a feature is implemented or verified.

The initial architecture is Python, Streamlit, LLM tool calling via Groq or OpenRouter,
FastMCP over stdio, Sentence Transformers embeddings, FAISS, synthetic JSON data, pytest,
GitHub Actions, and a single free-tier-compatible Render, Railway, or equivalent service.
Provider, model, and host availability and limits must be validated during planning. The
architecture is a proposed baseline, not a justification for additional services or frameworks.

## Phases and dependencies

| Phase | Features | Dependency and outcome |
|---|---|---|
| 1 | F001 | Establish policy ingestion, retrieval, and cited answers. |
| 2 | F002 | Depends on F001; expose its evidence and synthetic data over MCP. |
| 3 | F003 and F004 | F003 depends on F002; F004 depends on F003 and delivers both workflows. |
| 4 | F005 | Depends on F004; expose the workflows through a browser. |
| 5 | F006 | Depends on F005; integrate deployment, CI/CD, evaluation, and submission. |

Within those dependencies, policy authoring, synthetic fixture design, documentation,
evaluation cases, and test/CI scaffolding can begin in parallel. F004 workflow scenarios and
F005 interface designs can be drafted while upstream contracts are being defined, but working
end-to-end integration depends on the preceding features. Incremental tests, reproducibility
instructions, safety checks, and design documentation begin with each feature; F006 integrates
and verifies them rather than postponing all testing and documentation.

## F001 - HR Policy RAG

- **Objective:** Retrieve company HR policy information and produce accurate, cited answers.
- **Capability:** A developer can submit a policy question through a Python interface and
  receive traceable evidence and an answer.
- **In scope:** Synthetic policy corpus; at least two document formats; parsing, cleaning,
  chunking, embeddings, FAISS top-k retrieval; document and section metadata with snippets;
  grounded cited answers; unsupported and out-of-corpus handling; multi-document questions.
- **Out of scope:** MCP integration, agentic workflows, and web interface.
- **Dependencies:** None.
- **Completion:** The Python interface answers covered questions with supporting citations and
  snippets, handles unsupported questions, and supports multi-document evidence.
- **Quantic requirements:** QR-001, QR-003, QR-008-QR-017; supports evaluation and
  reproducibility requirements owned by F006.

## F002 - MCP Tool Integration

- **Objective:** Expose policy retrieval and synthetic employee operations through MCP.
- **Capability:** An MCP client discovers and invokes policy and structured-data tools.
- **In scope:** FastMCP server; stdio MCP client; six proposed tools
  `search_policy_documents`, `get_policy_section`, `lookup_employee_profile`,
  `check_pto_balance`, `check_policy_compliance`, and `draft_hr_email`; synthetic employee
  and PTO JSON data; discovery, validation, invocation, error handling, and safe input/output
  traces. Policy evidence wraps F001; it does not create another retrieval system.
- **Out of scope:** Full agent orchestration and web interface; real HR integration or email
  delivery. Drafting is a mock operation, not sending a message.
- **Dependencies:** F001.
- **Completion:** An MCP client discovers and successfully calls all six tools, including
  F001-backed evidence and synthetic employee/PTO operations; invalid inputs and failures
  are surfaced.
- **Quantic requirements:** QR-002, QR-023-QR-025, QR-027, QR-052; supports QR-018,
  QR-020-QR-022, QR-026, QR-035 and QR-038.

## F003 - Agent Orchestration

- **Objective:** Coordinate tool use and multi-step requests with an LLM-based agent.
- **Capability:** The agent interprets requests, chooses retrieval or MCP tools, and produces
  grounded responses based on tool results.
- **In scope:** Intent interpretation; deciding whether retrieval alone is sufficient;
  dynamic MCP discovery, selection and invocation; multiple tool calls; cited synthesis;
  concise operational traces; ambiguity, missing evidence and unavailable-tool handling;
  safe action controls.
- **Out of scope:** Dedicated PTO and remote-work business workflows and web interface.
- **Dependencies:** F002.
- **Completion:** The agent autonomously discovers, selects, and calls MCP tools to complete
  representative multi-step tasks with grounded, inspectable results.
- **Quantic requirements:** QR-018, QR-020-QR-022, QR-026; supports QR-019, QR-030 and
  evaluation requirements QR-041-QR-042.

## F004 - HR Agentic Workflows

- **Objective:** Deliver two complete workflows combining policy evidence and synthetic data.
- **Capability:** Employees receive cited PTO-request guidance and remote-work eligibility
  guidance or escalation.
- **In scope:** PTO employee identification, balance and policy checks, approval guidance,
  and a manager email draft when requested; remote-work employee profile, location, security
  and approval-policy checks, cited recommendations or escalation. Both use sequential MCP
  calls, trace results, handle missing information and failures, and prevent unauthorized or
  irreversible actions.
- **Out of scope:** Real HR systems, email sending, and unrelated workflows.
- **Dependencies:** F003.
- **Completion:** Both workflows execute end to end using policy evidence, synthetic records,
  and verifiable MCP traces, producing grounded cited responses.
- **Quantic requirements:** QR-019-QR-022, QR-032, QR-047; supports QR-040-QR-042 and
  demo requirements QR-049 and QR-051.

## F005 - Chat Interface

- **Objective:** Provide a simple browser interface to the HR agent.
- **Capability:** Users can run both workflows and inspect answers, citations, snippets, and
  concise tool-call traces.
- **In scope:** Streamlit chat; natural-language input; responses and supporting evidence;
  traces; sample workflow prompts; request-handling and health-check equivalents; loading
  states and user-friendly errors.
- **Out of scope:** Authentication, administrative dashboards, persistent cross-session
  conversation history, and complex front-end frameworks.
- **Dependencies:** F004.
- **Completion:** Both required workflows work through a browser, with responses, citations,
  snippets, and operational traces available for inspection.
- **Quantic requirements:** QR-028-QR-032; supports QR-020 and QR-049.

## F006 - Deployment, CI/CD, and Evaluation

- **Objective:** Integrate, deploy, evaluate, document, and prepare the completed submission.
- **Capability:** A grader can access the application, reproduce its workflows, review results,
  and inspect the repository and recorded demonstration.
- **In scope:** Single-service free-tier deployment and local operation; shareable URL,
  environment configuration and cold-start notes; GitHub Actions checks and test-gated
  deployment; 20-30 evaluation cases, required quality, behavior and latency metrics, and
  an ablation; final README, design/evaluation, AI-tooling, deployment, and submission
  materials, including the recorded demo.
- **Out of scope:** New HR features, paid database requirements, and separate deployed MCP
  services.
- **Dependencies:** F005.
- **Completion:** Application access, required automated checks, evaluation results, and
  submission artifacts are verified and documented; exceptional deployment issues are
  documented if applicable.
- **Quantic requirements:** QR-003-QR-007, QR-033-QR-060; integrates
  evidence from F001-F005.

## Breakdown validation and recommendations for review

- **Coverage:** The matrix assigns an owner to all identified substantive assignment items,
  including the corpus and submission requirements outside the ten numbered sections. No
  assignment requirement is knowingly left unassigned; assignment-level delivery is not
  complete until all features and submission activities are verified.
- **Shared responsibilities:** F001 owns retrieval; F002 wraps it; F003 chooses and orchestrates
  tools; F004 defines workflow-specific decisions; F005 displays results; F006 integrates
  testing, evaluation, documentation, and submission. Citations, safety, and traces cross
  boundaries intentionally and need shared contracts rather than duplicate implementations.
- **Dependencies:** The proposed sequence is coherent. F003 can be tested using representative
  multi-step tasks without implementing F004's dedicated workflow rules; F004 then builds on it.
- **Simplicity and constitution:** Single-service deployment, synthetic data, safe mock
  operations, Python-first design, and modular responsibilities fit the constitution. Streamlit,
  FastMCP, and the proposed model stack should be kept only if they satisfy the required
  interfaces and free-tier limits without extra infrastructure.
- **Review recommendation - existing specifications:** The current F002 draft requests
  clarification about the six tools. The list in this roadmap resolves their names, but
  tool-specific contracts and how `check_policy_compliance` reaches evidence-based conclusions
  still need agreement in the feature specification. `draft_hr_email` must not send email.
  Update the draft separately after review; no feature spec is changed by this roadmap.
- **Review recommendation - interface equivalence:** Confirm during F005 planning that the
  Streamlit design provides a grader-accessible chat request flow and JSON health status,
  including MCP connectivity where feasible. If it cannot, propose the smallest compatible
  equivalent without silently introducing another deployed service.
- **Review recommendation - source link:** The PDF is at
  `docs/requirements/Quantic AI Agent project.pdf`, not the filename in the request or the
  path currently referenced by the constitution. Correct the constitution link separately
  after approval; this roadmap does not modify it.
- **Ambiguity - corpus size:** The PDF describes approximately 5-20 documents totaling
  30-120 pages; Markdown/TXT pagination is not intrinsic. Define a reproducible page-equivalent
  convention or seek clarification before final acceptance; do not lower the target silently.
- **Ambiguity - hosting and offline dependencies:** Validate host free-tier availability,
  memory, model downloads, persistence, cold starts, and provider limits before committing to
  the baseline; no provider availability is assumed.