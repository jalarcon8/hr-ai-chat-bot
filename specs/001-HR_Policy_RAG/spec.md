# Feature Specification: HR Policy RAG

**Feature ID**: F001

**Feature Branch**: Not created

**Created**: 2026-11-11

**Status**: Draft

**Input**: Update Feature 001 using the project roadmap, Quantic requirement traceability,
and current policy corpus. Provide a Python interface for grounded, cited HR-policy answers
using Markdown and TXT source ingestion, embeddings, FAISS, and top-k retrieval. No MCP or
web UI is included in this feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Get a cited policy answer (Priority: P1)

As an employee, I want an answer to a policy question with references and supporting excerpts
so that I can verify the response against the fictional company policy.

**Why this priority**: Reliable, verifiable policy answers are the feature's core capability.

**Independent Test**: Build an index from the provided synthetic Markdown and TXT corpus,
submit a covered question through the Python interface, and verify the answer and citation
against the source.

**Acceptance Scenarios**:

1. **Given** a policy corpus containing the answer, **When** a developer submits a covered
   question through the Python interface, **Then** the result includes a supported answer,
   source identifier, section when present, and an exact supporting excerpt.
2. **Given** Markdown and TXT policy sources, **When** a developer asks a question answered
   by a source in each format, **Then** the result cites the correct document and supporting
   evidence for both.
3. **Given** the supplied corpus, **When** a developer rebuilds the index, **Then** each
   included source is discoverable and its citations can be traced to the original document.

---

### User Story 2 - Recognize unsupported questions (Priority: P1)

As an employee, I want the system to identify when policy evidence does not support an answer
so that I do not mistake a guess for company policy.

**Why this priority**: An unsupported answer could mislead employees and undermine trust.

**Independent Test**: Submit out-of-corpus and partially supported questions; verify that the
system identifies evidence limits without inventing policy facts or citations.

**Acceptance Scenarios**:

1. **Given** no retrieved policy evidence supports a question, **When** the question is
   submitted, **Then** the response states that available policies do not support an answer
   and includes no fabricated citation.
2. **Given** retrieved evidence supports only part of a question, **When** the question is
   submitted, **Then** supported claims are cited and the missing information is identified.
3. **Given** relevant policy sources conflict, **When** the question is submitted, **Then**
   the response identifies the conflict and cites the evidence instead of presenting one claim
   as certain.

---

### User Story 3 - Combine multiple policies (Priority: P2)

As an employee, I want answers that combine relevant policies when needed so that I can
understand how different policy requirements apply to my question.

**Why this priority**: Realistic HR questions can require evidence from more than one document.

**Independent Test**: Ask a question whose complete answer depends on two synthetic policy
documents and verify the supported claims and citations from both.

**Acceptance Scenarios**:

1. **Given** two policy documents contain complementary evidence, **When** a question requires
   both, **Then** the answer covers the supported aspects and cites each source with a relevant
   excerpt.
2. **Given** one necessary source is absent or not retrieved, **When** the question is
   submitted, **Then** the answer cites what is supported and identifies what remains unknown.

### Edge Cases

- An empty or whitespace-only question returns a clear input-validation error.
- An empty corpus, empty document, or missing index is reported explicitly; valid files are not
  silently skipped after ingestion errors.
- Unsupported file types, malformed or unreadable files, embedding failures, index failures,
  retrieval failures, and answer-generation failures are surfaced as operational errors rather
  than unsupported-policy answers.
- If fewer than k chunks exist, retrieval returns only available chunks without failing.
- Markdown and TXT documents without detectable sections can be cited at the document level.
- For TXT identity resolution, use a valid recognized `document_id` when present; if it is
  absent, derive a deterministic ID from the corpus-relative source filename. A present but
  malformed or empty `document_id`, an invalid provided `title`, or a filename from which an
  ID cannot be derived causes a metadata validation error; do not fall back after invalid
  metadata. Reject duplicate document IDs before indexing. Missing or malformed section labels
  use document-level citations when no section can be parsed.
- A source excerpt containing instructions to the model is treated as untrusted policy content,
  not as an instruction that changes system behavior.
- Policy facts are distinguished from recommendations; conflicting evidence is reported with
  citations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST ingest Markdown and TXT files from the current clearly fictional
  policy corpus in `corpus/`. The baseline contains 12 documents: nine Markdown files and
  three TXT files covering employee handbook, PTO, holidays, remote work, expenses, data
  security, benefits, onboarding, equipment, leave, workplace conduct, and IT support.
  Unsupported formats MUST be rejected or explicitly excluded from indexing. For TXT
  documents, a valid recognized `document_id` MUST take precedence; if it is absent, the
  system MUST derive a deterministic ID from the source filename. A present but malformed,
  empty, or otherwise invalid `document_id`, an invalid provided `title`, or a filename that
  cannot yield an ID MUST cause a metadata validation error; malformed metadata MUST NOT
  trigger filename fallback. Duplicate document IDs MUST be rejected before indexing, and
  documents failing identity validation MUST NOT be indexed.
- **FR-002**: The F001 corpus MUST contain approximately 5-20 short documents totaling
  30-120 pages, as required by the assignment. Because Markdown has no fixed page layout,
  corpus size MUST be reported using the documented project page-equivalent convention.
  At specification update, the 12 Markdown and TXT files total about 12,500 words, or
  approximately 32 equivalent pages using 400 words per page.
- **FR-003**: The system MUST parse and clean supported source text, split documents into
  retrievable chunks using a justified deterministic strategy, and preserve each chunk's
  source document, section when present, and traceable source snippet.
- **FR-004**: The system MUST generate embeddings with a free, local, or free-tier model/API
  and document the model and configuration. It MUST NOT require a paid embedding service.
- **FR-005**: The system MUST store embedded chunks in a local or lightweight FAISS index and
  retrieve up to a configurable top-k relevant chunks for a question. Optional query rewriting,
  filtering, and reranking are not required.
- **FR-006**: Each indexed chunk MUST retain document title or stable ID, section when present,
  and a snippet traceable to the original source. Retrieval results MUST preserve this metadata.
- **FR-007**: A developer MUST be able to build and rebuild an index from the current corpus.
  A successful rebuild MUST reflect source additions and edits and MUST NOT return content from
  removed documents.
- **FR-008**: The Python question interface MUST place retrieved policy chunks and their source
  metadata into the answer-generation context.
- **FR-009**: Factual policy claims MUST be grounded in the retrieved source evidence. Each
  claim MUST include a source ID or title, section when available, and a supporting snippet
  traceable to the cited source. An excerpt's presence alone MUST NOT be treated as proof that
  it semantically supports the associated claim.
- **FR-010**: The system MUST refuse or redirect out-of-corpus questions, identify insufficient
  evidence, limit unsupported claims, and distinguish policy facts from recommendations. It
  MUST NOT invent source references or snippets.
- **FR-011**: The system MUST support at least one documented complex question requiring
  evidence from two or more policy documents and cite each source used. It MUST identify
  missing or conflicting evidence when a complete answer cannot be supported.
- **FR-012**: The Python interface MUST return an inspectable answer, citations, snippets, and
  evidence limitations. Invalid input and ingestion, model, retrieval, index, or validation
  failures MUST be clearly distinguishable from a valid unsupported answer.
- **FR-013**: Ingestion, retrieval, and response generation MUST have separable responsibilities
  and be independently testable. Routine tests MUST use synthetic fixtures and deterministic
  substitutes for external model services.
- **FR-014**: Setup, dependencies, configuration, local indexing and question use, and tests
  MUST be documented for reproducibility. Applicable chunking and evaluation seeds MUST be
  fixed; credentials MUST be read from environment configuration and not committed.
- **FR-015**: Retrieved policy text MUST be treated as source data, not instructions that
  override application rules. Corpus and test data MUST be fictional; no real employee data or
  HR integrations are in scope.

### Quantic Requirement Traceability

| Requirement | F001 specification coverage |
|---|---|
| QR-001 | FR-001, FR-002; baseline and page-equivalent reporting |
| QR-003 | FR-004, FR-014; free/local model and modest local corpus |
| QR-008 | FR-001, FR-003; Markdown and TXT parsing and cleaning. |
| QR-009 | FR-003; justified deterministic chunking |
| QR-010 | FR-004; free/local/free-tier embeddings |
| QR-011 | FR-005; local FAISS vector index |
| QR-012 | FR-003, FR-006, FR-009; source metadata and traceable citations |
| QR-013 | FR-005; configurable top-k retrieval |
| QR-014 | FR-008; retrieved context and metadata |
| QR-015 | FR-009, FR-012; cited claims and snippets |
| QR-016 | FR-010, FR-015; unsupported questions and untrusted source content |
| QR-017 | FR-011; multi-document question and citations |
| QR-004-QR-007 (F006-owned, F001-supported) | FR-014; environment, dependencies, reproducibility, and secret handling contribution |

### Key Entities

- **Policy document**: Fictional Markdown or TXT source with a title or ID, original text,
  format, and optional section headings or numbered section labels.
- **Policy chunk**: A retrievable source passage with document metadata, optional section,
  exact source offsets or equivalent traceability, snippet, and embedding.
- **Question**: A nonempty policy question submitted through the developer-facing Python
  interface.
- **Answer**: A response with factual claims, any clearly distinguished recommendations,
  evidence limitations, and an explicit supported/partial/unsupported/conflicting outcome.
- **Citation**: A reference to a retrieved source and optional section with an exact supporting
  excerpt associated with one or more claims.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer following the documented setup can index the supplied 12-document
  corpus, including Markdown and TXT sources, and submit a covered question through the Python
  interface.
- **SC-002**: The corpus contains 5-20 short synthetic policy documents covering the listed HR
  topics and totals 30-120 pages or documented page equivalents; at this update it contains
  nine Markdown and three TXT documents, about 12,500 words, and about 32 pages at 400 words
  per page.
- **SC-003**: In an acceptance set of at least five covered questions across Markdown and TXT
  sources, every factual policy claim has a citation and snippet that supports it.
- **SC-004**: In an acceptance set of at least three unsupported or partially supported
  questions, every response identifies its evidence limitation and contains no invented
  citation or unsupported policy claim.
- **SC-005**: At least one acceptance question requiring evidence from two or more documents
  receives a complete supported answer with traceable citations to both documents; missing
  evidence is identified when the complete answer cannot be supported.
- **SC-006**: After a documented rebuild following a source addition, edit, and removal,
  acceptance checks show added and updated evidence and do not cite removed content.
- **SC-007**: Automated tests cover Markdown and TXT ingestion, retrieval, citations,
  unsupported and multi-document answers, input validation, index refresh, and operational
  failures without real HR systems.

## Assumptions

- F001 is the first increment of the wider assignment. MCP integration, agent orchestration,
  structured employee data, web UI, deployment, final project evaluation, and submission
  deliverables remain assigned to later features.
- The 12 files currently under `corpus/` are fictional Northstar training policies and are
  clearly labeled as fictional; do not treat them as real HR policy or legal advice.
- Markdown and TXT are the supported source formats for F001, matching the three TXT policies
  now present in the corpus. TXT documents contain key-value metadata headers and numbered
  section labels that should be used for source identity and section citations when valid.
- For reporting the assignment's page target, this feature uses 400 words per page equivalent.
  This is a transparent project convention, not pagination defined by the assignment.
- Section labels are used when present; document-level citations are acceptable without
  headings. Excerpts are exact, traceable source passages.
- The embedding and answer-generation model choice remains subject to planning validation of
  free-tier availability, licensing, model limits, and host resource requirements.
- The assignment PDF is available as `docs/requirements/Quantic AI Agent project.pdf`. The
  requirements-integration guide names a different PDF path that is currently absent; the
  project owner confirmed use of the available PDF for this update.
- The assignment says to handle at least two source formats "where feasible" (QR-008), while
  the current corpus supplies Markdown and TXT sources. F001 supports both; no additional
  source formats are required by this feature.
