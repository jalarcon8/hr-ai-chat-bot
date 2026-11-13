# AI-Powered HR Chatbot

## Project Overview

This project develops an AI-powered HR chatbot as part of the Quantic AI Engineering curriculum. The chatbot is designed to answer employee questions about company policies and support multi-step HR workflows using **Retrieval-Augmented Generation (RAG)**, **Model Context Protocol (MCP)**, and AI agent orchestration.

The application uses a fictional company's HR policies and synthetic employee data to demonstrate grounded question answering, tool integration, and automated workflows.

The project prioritizes a lightweight, modular architecture that satisfies the assignment requirements without unnecessary complexity.

## Planned Technology Stack

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
| Deployment | Free-tier-compatible cloud hosting |

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
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Answer generation model |
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

A clean Windows Python 3.11 virtual environment installed the pinned dependencies from
`requirements.txt` and the project in editable mode; `python -m pytest -q` completed with
**48 passed in 1.75s** using FAISS 1.10.0, NumPy 1.26.4, and pytest 8.3.4. Linux runtime
installation and tests were not run because this environment has no Linux host or WSL; T028
remains incomplete until Linux validation is performed. Live Sentence Transformers/Groq
inference has also not been run. Deterministic tests verify structure, provenance, rebuild
behavior, and error handling; semantic support must still be checked in the documented
acceptance review or an opt-in provider smoke test.