# Implementation Plan: HR Policy RAG

**Branch**: None (the project directory is not a Git repository; feature directory:
`001-HR_Policy_RAG`) | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: F001 specification, project roadmap, Quantic requirements traceability matrix,
constitution, and the current synthetic policy corpus under `corpus/`.

## Summary

Deliver a Python policy RAG library over the current 12 fictional policy documents (nine
Markdown and three TXT). Parse and clean documents, extract Markdown headings or TXT metadata
and numbered sections, make reproducible section-aware chunks, embed them with a free/local
model, index with FAISS, retrieve top-k evidence, and answer through an inspectable Python
interface with claim-level source citations and exact snippets. Rebuilds must reflect additions,
edits, and removals consistently. Unsupported and conflicting evidence must be distinct from
operational errors.

Expose retrieval as an independent reusable operation for F002's MCP wrapper. Do not implement
MCP, orchestration, employee data, web UI, deployment, or assignment-wide evaluation in F001.

## Technical Context

**Language/Version**: Python 3.11; record and validate exact dependency versions when creating
the implementation manifest.

**Primary Dependencies**: Sentence Transformers with
`sentence-transformers/all-MiniLM-L6-v2`; CPU FAISS; Groq Python SDK for answer generation;
pytest. Keep model/provider configuration external and provide injected deterministic doubles
for tests. Validate compatible package builds on the actual Windows development and Linux
deployment targets before locking versions.

**Storage**: Source of truth is the checked-in fictional Markdown and TXT corpus at `corpus/`.
Persist a local FAISS flat index and associated JSON metadata as one versioned snapshot; do
not index test fixtures into the production corpus.

**Testing**: pytest unit, interface/contract, FAISS integration, and acceptance tests.
Routine tests use synthetic Markdown and TXT fixtures plus deterministic embedding and answer
doubles; a separately configured live provider smoke test is optional and is never represented
by mock test results.

**Target Platform**: Local Windows development; CPU Linux is the target for eventual
single-service deployment. F001 itself has no deployment deliverable. Validate the selected
FAISS distribution, model download and memory requirements on both supported environments.

**Project Type**: Python library/module with an inspectable developer-facing Python interface.

**Performance Goals**: F001 has no numeric latency SLO. Record query latency for the broader
evaluation; assignment evaluation later reports p50/p95 for 10-20 representative tasks.
No retrieval-accuracy or latency target is claimed without measurement.

**Constraints**: Synthetic policy content only; no real HR data or integrations; free/local
embedding choice; environment-based secrets; explicit errors; single-service-compatible local
storage. Model downloads and Groq inference require network access; live inference additionally
requires valid provider access and quota.

**Scale/Scope**: `corpus/` currently contains 12 policy files (nine Markdown and three TXT)
and 12,528 words counted by the project's regex-based word-count convention (about 32 page
equivalents at 400 words/page). The 400-word equivalence is a project measurement convention,
not PDF layout. The three TXT files are holiday, remote-work, and expense policies; their
headers include document metadata and their body sections use numbered labels. F001 also
requires at least five covered questions, three unsupported/partial cases, and one
multi-document question; final Quantic evaluation has broader scope and is owned by F006.

## Requirement Mapping

| Quantic requirement | Design element | Verification |
|---|---|---|
| QR-001 | Ingest current 12-document fictional HR corpus; report count, topic coverage, source provenance, and 400-word page equivalents. | Corpus audit and reproducible word/page-equivalent calculation. |
| QR-003 | Local sentence embeddings, CPU flat index, small corpus; record model download, runtime memory, and provider limits. | Clean setup and resource/provider assumptions documented; evaluate actual constraints before deployment. |
| QR-008 | Deterministic UTF-8 ingestion for Markdown and TXT, including the three corpus TXT files' metadata and numbered sections. | Unit/acceptance checks for each format, metadata, numbered sections, and sources without sections. |
| QR-009 | Heading-aware, tokenizer-bounded chunks with documented overlap and source spans. | Check boundaries, repeatability, and source reconstruction. |
| QR-010 | Free/local Sentence Transformers embedding baseline. | Build/query with local model; document model and configuration. |
| QR-011 | Exact local FAISS flat index. | Vector count, dimension, save/load, and top-k integration checks. |
| QR-012 | Persist source ID/title, Markdown heading path or TXT numbered section, and exact snippet/span alongside each vector. | Resolve every retrieved citation to original source text. |
| QR-013 | Configurable top-k; no unnecessary reranker in baseline. | Check ordering, k bound, and fewer-than-k corpus. |
| QR-014 | Pass retrieved passages plus source metadata to generation as untrusted evidence. | Test generation input construction. |
| QR-015 | Structured claim-to-citation answers with source title/section/snippet. | Acceptance evaluation manually or independently checks semantic support. |
| QR-016 | Explicit unsupported/partial status and out-of-scope redirection; distinguish recommendations. | At least three unsupported/partial cases and out-of-corpus case. |
| QR-017 | Multi-document retrieval and answer with evidence for each necessary source. | At least one two-document acceptance case and missing-source variant. |
| QR-004-QR-007 (F006-owned) | F001 documents Python setup, dependencies, tests, applicable deterministic behavior, and environment-based secrets. | Clean local setup; inspect manifest/configuration; project-wide requirements remain owned by F006. |

QR-002 and QR-018 onward are not F001 requirements and are not implemented here. F002 consumes
the retrieval contract; it MUST NOT create another corpus index or embedding pipeline.

## Constitution Check

| Gate | Before design | After design |
|---|---|---|
| Simplicity, Python, modularity | Pass: one Python library; no extra framework or service. | Pass: ingestion, retrieval, generation, and result types have narrow contracts. |
| Grounded answers and citations | Pass: sourced answers and unsupported handling are F001 goals. | Pass with known limitation: IDs/snippet checks validate provenance, not semantic entailment; acceptance review must verify support. |
| MCP integration | Deferred to F002 by roadmap, not waived for assignment completion. | Pass: reusable `retrieve` operation is the sole evidence interface; no MCP bypass is claimed. |
| Synthetic data, safe operations, secrets | Pass: fictional corpus and read-only questions; local derived-index rebuild only. | Pass: no employee record or HR mutation; credentials externalized; logs omit secrets and raw prompts unless explicitly needed. |
| Automated testing and reproducibility | Pass: synthetic fixtures and deterministic doubles. | Pass for feature scope; live provider, OS package compatibility, and model resources need explicit validation. |
| Single-service/free-tier/project scope | Pass: local FAISS and a small current corpus. | Pass provisionally: model cold-start, host memory, free-tier quota and local persistence require measurement later. |
| Assignment completeness | F001 owns QR-001, QR-003, QR-008-QR-017; F006 owns project-wide CI, deployment, full evaluation, and submission. | F001 contributes only its mapped behavior; no later-feature obligation is silently marked complete. |

## Project Structure

### Documentation (this feature)

```text
specs/001-HR_Policy_RAG/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── python-interface.md
└── quickstart.md
```

### Source Code (planned; not yet present)

```text
src/hr_rag/
├── __init__.py
├── config.py          # model and index settings
├── documents.py       # Markdown/TXT ingestion, metadata, and section-aware chunks
├── index.py           # embedding, FAISS snapshot, and retrieval
├── answers.py         # evidence-based response generation
└── models.py          # typed question, evidence, citation, and result values
corpus/                 # existing fictional Markdown policy corpus
tests/
├── fixtures/
│   ├── policies/       # small synthetic format and error-case test files
│   └── doubles.py      # deterministic embedder and generator
├── test_documents.py
├── test_index.py
├── test_answers.py
└── test_acceptance.py
```

**Structure Decision**: Keep one Python package and use the existing root `corpus/` as source
content, including all nine Markdown and three TXT files. For TXT, extract `document_id` and
`title` from recognized leading metadata fields and numbered section labels from body text.
Use a valid `document_id` when present; otherwise derive a deterministic ID from the
corpus-relative filename stem. Invalid present identity metadata must fail rather than fall
back, and duplicate IDs are rejected before indexing. Ignore other header fields for retrieval
metadata and preserve the original document unchanged for citations. Unit fixtures remain
separate from that corpus. Persist index generations
locally with metadata aligned to vector IDs. Feature 002 calls the public retrieval contract
and shares the same index. Layout is proposed; it does not assert source code exists.

## Complexity Tracking

No constitution violations are proposed. A FAISS index plus aligned metadata is required by
scope. Exact flat search is sufficient for the currently small corpus; no hosted vector store,
reranker, query rewriting service, web framework, or MCP server is added to F001.
