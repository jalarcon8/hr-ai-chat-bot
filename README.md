# AI-Powered HR Chatbot

## Project Overview

This project develops an AI-powered HR chatbot as part of the Quantic AI Engineering curriculum. The chatbot is designed to answer employee questions about company policies and support multi-step HR workflows using **Retrieval-Augmented Generation (RAG)**, **Model Context Protocol (MCP)**, and AI agent orchestration.

The application uses a fictional company's HR policies and synthetic employee data to demonstrate grounded question answering, tool integration, and automated workflows.

The project prioritizes a lightweight, modular architecture that satisfies the assignment requirements without unnecessary complexity.

## Deployment and final delivery status

- Deployed application: <https://hr-ai-chat-bot-jonathan-alarcon.streamlit.app/>
- Repository: <https://github.com/jalarcon8/hr-ai-chat-bot>
- Recorded demonstration: **pending; no demo link supplied**.

The owner reports successful deployed prompts. The single authorized Ubuntu continuation
has finished, stopping at its three-provider-failure limit without case retries. Across the
canonical Ubuntu primary results: **7/20 attempted, 3 answers returned and graded,
4 provider failures, 0 operational failures, 13 unattempted**. Diagnostics and Windows
timeouts remain separate. Offline source-backed review passes 0/3 full answer rubrics;
groundedness is 14/18 claims and citation accuracy 10/20 section references.
Only one new latency sample qualified, so required p50/p95 remain unavailable.

The [completion report](evaluation/completion-report.md) records exact denominators,
tool/workflow/safety metrics, preserved traces and remaining gaps. Policy/RAG/MCP/Groq
integration is demonstrated, but both complete employee workflows and representative
evaluation are not verified. **No further live evaluation or EVAL-003 retry is authorized.**
The [bounded execution contract](evaluation/completion-plan.md) is historical, not permission
for another run.

Delivery documents:
[deployment and health equivalent](docs/deployed.md),
[design and evaluation](docs/design-and-evaluation.md),
[AI-tooling disclosure](docs/ai-tooling.md),
[latest evaluation report](evaluation/completion-report.md),
[historical closure report](evaluation/final-report.md),
[demo/submission checklist](docs/demo-checklist.md),
and [requirements traceability](docs/requirements/traceability.md).

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| User interface | Streamlit |
| AI orchestration | Python with LLM tool calling |
| Document retrieval | RAG with FAISS |
| Embeddings | Sentence Transformers |
| Tool integration | FastMCP |
| Employee data | Synthetic JSON |
| Testing | pytest |
| CI/CD | GitHub Actions |
| Deployment | Streamlit Community Cloud; same-service MCP stdio subprocess |

## Feature Roadmap

Development is organized into six sequential features:

| ID | Feature | Description |
|---|---|---|
| F001 | HR Policy RAG | Document ingestion, embeddings, retrieval, and cited responses |
| F002 | MCP Tool Integration | MCP server/client, policy tools, and synthetic employee data |
| F003 | Agent Orchestration | Dynamic tool selection, multi-step execution, and guardrails |
| F004 | HR Agentic Workflows | PTO and remote-work eligibility workflows |
| F005 | Chat Interface | Streamlit-based conversational interface |
| F006 | Deployment, CI/CD & Evaluation | Automated testing, deployment, performance evaluation, and documentation |

The detailed feature definitions, dependencies, and completion criteria are maintained in `docs/feature-roadmap.md`.

## Development Methodology

The project follows a **specification-driven development methodology using GitHub Spec Kit v1.0.4**.

Each feature progresses through the Spec Kit workflow:

1. **Specify** — Define feature requirements and acceptance criteria.
2. **Clarify** — Resolve ambiguities in the specification.
3. **Plan** — Establish the technical implementation approach.
4. **Tasks** — Generate implementation and verification tasks.
5. **Analyze** — Validate consistency and requirements coverage.
6. **Implement** — Develop and test the feature.

Features are developed incrementally, with review checkpoints before implementation.

## Customized Spec Kit Workflow

The standard Spec Kit workflow has been extended with project-specific requirements governance to maintain alignment with the Quantic assignment.

Three documents provide project-wide guidance:

| Document | Purpose |
|---|---|
| `.specify/memory/constitution.md` | Defines architectural principles, development constraints, and quality standards |
| `docs/feature-roadmap.md` | Defines feature scope, dependencies, and implementation sequence |
| `docs/requirements/traceability.md` | Maps assignment requirements (`QR-###`) to features and tracks implementation and verification |

A shared integration document, `.specify/memory/requirements-integration.md`, defines how these references are used throughout development.

Five Spec Kit skills in `.github/skills/` have been targeted for customization:

- **speckit-specify:** Incorporates roadmap scope and assigned requirements into feature specifications.
- **speckit-plan:** Maps requirements to technical design decisions.
- **speckit-tasks:** Ensures requirements have corresponding implementation and verification tasks.
- **speckit-analyze:** Validates coverage against the roadmap and traceability matrix.
- **speckit-implement:** Checks completed work against requirements and reports verification evidence.

These customizations are intended to preserve requirements traceability from the original assignment through specification, implementation, and testing.

The coding agent follows the shared integration instructions, while requirements coverage and changes to project-level governance documents remain subject to review and approval.

## Requirements Traceability

Assignment requirements are assigned unique `QR-###` identifiers and mapped to their corresponding features.

Each requirement is tracked through four statuses:

**Not Started → In Progress → Implemented → Verified**

A requirement is considered Verified only when supporting test results or other verification evidence are available.

The original Quantic assignment document remains the authoritative source for mandatory project requirements.

## Development Principles

- Prioritize fulfillment of the Quantic assignment requirements.
- Use a Python-first, modular architecture.
- Minimize unnecessary frameworks, infrastructure, and dependencies.
- Ground HR policy answers in retrieved documents with citations.
- Use MCP-compliant tool interactions and synthetic employee data.
- Include automated testing, evaluation, and reproducible deployment.
- Maintain human review checkpoints throughout development.
- Preserve requirements traceability across all six features.

This approach combines Spec Kit's structured feature development process with project-level planning and requirements verification, providing a controlled path from assignment requirements to a tested, deployable AI application.

## Local configuration and tests

From the project root, install Python 3.11 dependencies and create a local configuration:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in `.env` only when using the Groq provider. Never commit `.env` or
share the key. Feature 003 reads `.env` from the current working directory without modifying
process variables; explicitly set environment variables take precedence, including `GROQ_MODEL`
over a model set only in `.env`. The model is selected by `AGENT_MODEL_NAME`, then `GROQ_MODEL`,
and defaults to `openai/gpt-oss-20b` when neither is set. The `.env` configuration applies to
Feature 003; Feature 001 and Feature 002 retain their existing environment-variable behavior.

Run routine tests and linting without Groq credentials or network calls to the provider:

```powershell
$env:AGENT_RUN_PROVIDER_SMOKE = "0"
$env:AGENT_RUN_F004_LIVE = "0"
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python evaluation\run_evaluation.py --validate-only
```

Live checks are opt-in. Keep both switches at `0` in the environment and `.env` for routine
tests and CI; the process values above override local `.env` opt-ins. Five skipped live tests
are not five successful live scenarios. Do not opt in or dispatch evaluation while the
current owner-directed pause is in effect.

Latest local verification: **527 passed, 5 skipped**, repository-wide Ruff passed.
The suite includes 16 AppTest and 3 agent/MCP integration tests. These provider-free results
do not establish live answer correctness. Existing hosted Windows/Ubuntu checks passed at
the code baseline; final documentation/evidence changes require their own protected-main
review and CI. See the [final report](evaluation/final-report.md) for precise evidence scope.

Feature 003 returns an unsent email proposal with an `action_id` and `pending_action`. Pass both
back to `confirm_action` on the same `HRAgent` instance with an explicit boolean confirmation.
The proposal is not stored; restarting or replacing the agent requires a new proposal. Set
`AGENT_TRACE_PATH` to persist sanitized agent traces locally; trace write failures are errors.

### Feature 005: Local Streamlit chat

From the project root, start the browser interface:

```powershell
.\.venv\Scripts\python -m streamlit run src\hr_app\app.py
```

Ask a policy question or select the PTO or remote-work sample prompt. Provide a synthetic
employee ID in the sidebar for employee-specific requests; IDs in message text are not treated
as authoritative context. Use **Check MCP health** to render JSON app/MCP status; the probe
performs MCP discovery only. Draft confirmation and cancellation reuse the session's agent and
never send email. See [the F005 quickstart](specs/005-chat-interface/quickstart.md) for
validation evidence and limitations.

For real synthetic data use sidebar ID **SYN-001** (80 PTO hours as of 2026-01-01);
older `TEST-*` IDs belong to isolated tests, not the deployed dataset. The tracked app
entry point is `src/hr_app/app.py`; no root-level `app.py` wrapper exists.

### F006 deployment and evaluation

Community Cloud uses Python 3.11, protected `main`, the app path above, the checked-in
`.hr_rag_index` generation and `GROQ_API_KEY` in host Secrets. The UI bridges that secret
to the existing environment-backed provider without overwriting an explicit process value.
No separately hosted MCP URL or database is needed. An idle/restarted service and first
embedding-model load may delay the first request; no hosted cold-start duration was measured.

Use the [deployment record](docs/deployed.md) for configuration, the health-equivalent JSON
and known limitations. The [F006 runbook](specs/006-deployment-ci-cd-evaluation/quickstart.md)
retains historical evaluation commands for reproducibility, not authorization to rerun them.
Original partial results and separate per-run evidence remain in `evaluation/`; never
overwrite them or pool diagnostics into suite metrics. The latest hosted EVAL-003 diagnostic
returned an employee-ID clarification without executing a tool: an operational completion,
not a passing policy answer. No extra Groq requests are needed to inspect these artifacts.

## Feature 001: Local HR Policy RAG

F001 provides a synchronous Python interface over the fictional Markdown and TXT policies in
`corpus/`. It builds a versioned local FAISS index, retrieves top-k passages, and returns
claim-level citations and exact source snippets. MCP, employee records, web UI, and deployment
are outside this feature.

### Setup and configuration

Use Python 3.11. From the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m pytest
```

The embedding model `sentence-transformers/all-MiniLM-L6-v2` is downloaded on first use and
requires network access unless already cached. Embedding runs locally on CPU. Live answer
generation uses Groq and requires network access, quota, and `GROQ_API_KEY`; routine tests use
deterministic doubles and require no provider key.

Optional environment settings:

| Variable | Default | Purpose |
|---|---|---|
| `HR_RAG_CORPUS_DIR` | `corpus` | Supported Markdown/TXT source directory |
| `HR_RAG_INDEX_DIR` | `.hr_rag_index` | Local versioned FAISS snapshots |
| `HR_RAG_EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding model |
| `HR_RAG_EMBEDDING_REVISION` | model default | Optional model revision |
| `HR_RAG_TOKENIZER_ID` | `sentence-transformers/all-MiniLM-L6-v2` | Chunk tokenizer identity |
| `HR_RAG_CHUNK_TOKENS` | `200` | Maximum tokens per chunk |
| `HR_RAG_CHUNK_OVERLAP` | `30` | Overlap tokens |
| `HR_RAG_TOP_K` | `5` | Default retrieval count |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Standalone F001 generator default; the deployed agent defaults to `openai/gpt-oss-20b` |
| `GROQ_API_KEY` | unset | Required only for live Groq generation |

### Build and ask a policy question

```python
from hr_rag import (
    ChunkingConfig,
    GroqGenerator,
    SentenceTransformerEmbedder,
    answer_question,
    build_index,
)

embedder = SentenceTransformerEmbedder("sentence-transformers/all-MiniLM-L6-v2")
settings = ChunkingConfig(max_tokens=200, overlap_tokens=30)
build_index(
    ".hr_rag_index",
    corpus_dir="corpus",
    embedder=embedder,
    chunking_config=settings,
)
result = answer_question(
    "How many floating holidays does an eligible full-time employee receive?",
    ".hr_rag_index",
    embedder=embedder,
    generator=GroqGenerator(),
    k=5,
)
for claim in result.claims:
    print(claim.text)
    for citation_id in claim.citation_ids:
        citation = next(item for item in result.citations if item.chunk_id == citation_id)
        print(citation.document_id, citation.section, citation.snippet)
```

`build_index` creates a complete generation and atomically activates it only after successful
validation. Rebuilds fully replace the active corpus view, so removed sources are not retrievable;
failed builds leave the previous generation active. Operational failures raise typed exceptions
instead of being returned as unsupported answers. See
`specs/001-HR_Policy_RAG/contracts/python-interface.md` for the public contracts and
`specs/001-HR_Policy_RAG/quickstart.md` for acceptance checks.

### F001 validation status

At the earlier F001 checkpoint, a clean Windows Python 3.11 virtual environment installed the pinned dependencies from
`requirements.txt` and the project in editable mode; `python -m pytest -q` completed with
**48 passed in 1.75s** using FAISS 1.10.0, NumPy 1.26.4, and pytest 8.3.4. Linux installation/tests were unverified at that checkpoint; subsequent F006 hosted CI
passed on Ubuntu and Windows. This historical F001 validation record did not
include live Sentence Transformers/Groq inference. Deterministic tests verify structure, provenance, rebuild
behavior, and error handling; semantic support must still be checked in the documented
acceptance review or an opt-in provider smoke test.

## Feature 002: MCP tools

The implemented developer client starts one FastMCP server as a subprocess over MCP stdio.
Discovery and calls cross that protocol boundary; the implemented F003 agent uses the same
client via `AgentSession`. Stdio keeps the integration within a single service without a separate
network listener. The server delegates search and section lookup to F001's active index, employee
and PTO lookup to fictional `data/employees.json` and `data/pto.json`, bounded compliance to
the evidence verifier, and email drafting to a deterministic template. Drafts are not sent or
stored. The six names, descriptions, input schemas and result envelopes are in the
[MCP contract](specs/002-mcp-tool-integration/contracts/mcp-tools.md).

Search results are ranked **candidate** evidence, not proof that a passage answers a question.
Results include source IDs, excerpts and generation metadata. Missing records or sections return
`not_found`; insufficient compliance facts or verified evidence return `indeterminate`.

### Local discovery and invocation

From the project root, install Python 3.11 and `.[dev]` as in the
[quickstart](specs/002-mcp-tool-integration/quickstart.md). For policy calls, build the F001
index with the setup above and use the same embedding configuration. Initial model download
may require network access; the employee example below does not require the index or model.
The client launches `python -m hr_mcp.server`; to run the server directly for an MCP client,
use that module as a stdio subprocess, not as an HTTP service.

```powershell
.\.venv\Scripts\python -m hr_mcp.client --discover
.\.venv\Scripts\python -m hr_mcp.client --example lookup_employee_profile
```

The example sends `{"employee_id": "SYN-001"}` and its `structuredContent` contains
`status: "found"` and the fictional Alex Example employee profile. The quickstart lists
examples for all six tools, Linux equivalents, and a separate deterministic credential-free
test setup. The client forwards the nonsecret `HR_RAG_*` settings listed above and defaults
to a five-minute call timeout (`MCPClient(call_timeout=...)` configures it).

### Safety, traces and compliance

The server returns structured `INVALID_ARGUMENT`, `OPERATIONAL_ERROR`, or `UNKNOWN_ERROR`
for classified tool failures. The client uses `UNCLASSIFIED_ERROR` with no asserted origin
when reliable classification is unavailable; valid `not_found` and `indeterminate` results
are not failures. SDK-rejected malformed protocol requests may never reach server dispatch.
See the contract for details.

Client and server append allowlisted JSONL events to `HR_MCP_TRACE_PATH`, defaulting to
`.hr_mcp/traces.jsonl`. Events include invocation IDs, timestamps, outcomes, classifications,
argument names and safe source IDs where applicable, not argument values, questions, employee
records, email drafts, credentials or full responses. Trace persistence is fail-closed: a
failed write returns an operational error instead of success and need not itself be recorded.
Inspect local events with `Get-Content .\.hr_mcp\traces.jsonl` on Windows or
`cat .hr_mcp/traces.jsonl` on Linux.

Compliance checks only whether written People Operations approval was granted strictly before
out-of-state travel, using unauthenticated caller assertions; it does not determine overall
eligibility. Definitive results require matching full-document v2 records and separately pinned
approval metadata for HR-004 and HR-001, verified source/index integrity and exact citations.
The production pin is inactive; missing or unreviewed evidence yields `indeterminate`. An
authorized maintainer must independently verify each exact full-document review and approval
before activating the pin. The old section-only baseline and test-only synthetic baseline do
not qualify. The [baseline procedure](specs/002-mcp-tool-integration/research.md) describes
canonicalization, review, activation and subsequent policy changes.

The [verification record](specs/002-mcp-tool-integration/quickstart.md) distinguishes local
synthetic evidence from clean-install, Linux, production approval and deployment acceptance.
F006 owns deployment, costs, quotas and final project-wide submission checks.

### F002 historical validation status

On Windows 11, a clean Python 3.11.9 environment installed a project snapshot and passed
306 tests with no skips and Ruff. The isolated synthetic MCP check passed. A cached real model
built the standard index, but the live policy-search example timed out; see the
[detailed results](specs/002-mcp-tool-integration/quickstart.md). Subsequent F006 hosted
Windows/Ubuntu matrix checks passed. The local production-index policy-search timeout
remains unresolved; successful hosted policy-search evidence and its limits are in the
[final report](evaluation/final-report.md).