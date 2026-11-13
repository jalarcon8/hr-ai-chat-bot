# Tasks: HR Policy RAG

**Input**: Design documents from `specs/001-HR_Policy_RAG/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/python-interface.md`, and `quickstart.md`

**Tests**: Included because F001 FR-013 and SC-007 require automated tests. Routine tests use
synthetic fixtures and deterministic doubles; no provider credentials are needed.

**Organization**: Tasks are grouped by the three independently testable user stories.

## Phase 1: Setup

**Purpose**: Establish the minimal Python package, dependencies, and test structure.

- [X] T001 [P] Create a Python 3.11 dependency manifest in `requirements.txt` for the selected Sentence Transformers, CPU FAISS, Groq SDK, and pytest dependencies; pin compatible versions and verify availability on Windows and Linux (QR-003, QR-004).
- [X] T002 [P] Create the planned package and test directories with package initializers in `src/hr_rag/__init__.py`, `tests/fixtures/policies/`, and `tests/fixtures/doubles.py`; keep test fixtures separate from `corpus/`.

## Phase 2: Foundational

**Purpose**: Provide shared configuration and typed contracts before story implementation.

- [X] T003 Add validated configuration for corpus and index paths, embedding model identity, top-k default, chunk size and overlap, and provider model/environment settings in `src/hr_rag/config.py`; never embed secrets in code (QR-003, QR-010).
- [X] T004 Define typed document, chunk, evidence, claim, citation, answer, build result, and operational error models in `src/hr_rag/models.py` according to `specs/001-HR_Policy_RAG/data-model.md` and `specs/001-HR_Policy_RAG/contracts/python-interface.md`.

**Checkpoint**: Setup and common configuration/contracts are ready for story work.

## Phase 3: User Story 1 - Get a cited policy answer (Priority: P1) 🎯 MVP

**Goal**: Index the current Markdown/TXT corpus and return a covered policy answer with source
identity, section when present, and traceable evidence through a Python interface.

**Independent Test**: Build the index from `corpus/`, submit a covered question using the Python
interface and deterministic generator, and verify the factual claim and citation against the
original policy text.

### Tests for User Story 1

- [X] T005 [P] [US1] Add parser tests for Markdown headings, TXT `document_id`/`title` metadata, numbered TXT sections, headingless sources, valid-ID precedence, absent-ID filename fallback, malformed/empty identity metadata without fallback, failed filename derivation, duplicate IDs rejected before embedding/indexing, decoding errors, and unsupported extensions in `tests/test_documents.py` (QR-008, QR-012).
- [X] T006 [P] [US1] Add FAISS index and retrieval tests for normalized vectors, dimension/count alignment, persistence and reload, descending top-k order, `k` validation, fewer chunks than k, and missing or incompatible snapshots in `tests/test_index.py` (QR-010, QR-011, QR-013).
- [X] T007 [P] [US1] Add Python-interface contract tests for `build_index`, `retrieve`, and `answer_question`, including returned source metadata, exact snippets, and claim-to-citation links, in `tests/test_api.py` (QR-012, QR-013, QR-015).
- [X] T008 [P] [US1] Add an acceptance question set with at least five covered questions across Markdown and TXT, expected source IDs/sections, and evidence-check rubrics in `tests/fixtures/acceptance_questions.json` (QR-001, QR-015).

### Implementation for User Story 1

- [X] T009 [US1] Implement deterministic UTF-8 ingestion for `.md` and `.txt` files under the configured corpus root in `src/hr_rag/documents.py`; extract Markdown heading paths and only recognized TXT `document_id`/`title` metadata and numbered body sections, use a valid `document_id` or derive an ID from the normalized corpus-relative filename stem only when that field is absent, raise metadata validation errors for malformed present fields or failed derivation, and reject duplicate IDs before indexing; preserve original text and exclude fixtures from the default corpus (QR-008, QR-012).
- [X] T010 [US1] Implement reproducible section-aware token-bounded chunking with configured overlap and exact source offsets/snippets in `src/hr_rag/documents.py`; validate chunk limits and ensure each chunk maps to one source section or document fallback (QR-009, QR-012).
- [X] T011 [US1] Implement local Sentence Transformers embedding with normalized vectors and explicit model/dimension identity in `src/hr_rag/index.py`; support injected deterministic embedders for tests (QR-003, QR-010).
- [X] T012 [US1] Implement FAISS flat-index construction, aligned JSON source metadata, snapshot validation, and atomic activation of a successful generation in `src/hr_rag/index.py`; failed builds must not activate partial state (QR-011, QR-012).
- [X] T013 [US1] Implement `retrieve` in `src/hr_rag/index.py` to validate inputs/index compatibility and return up to `min(k, chunk_count)` evidence records with descending scores and traceable source metadata (QR-013).
- [X] T014 [US1] Implement structured evidence-context construction and Groq-backed claim/citation generation in `src/hr_rag/answers.py`; pass retrieved policy text as untrusted evidence and keep the generator replaceable in tests (QR-014, QR-015).
- [X] T015 [US1] Implement `answer_question` and public exports in `src/hr_rag/answers.py` and `src/hr_rag/__init__.py`; return inspectable claims, limitations, citations, snippets, and explicit answer status, and validate every citation ID/snippet against retrieved evidence (QR-012, QR-015).
- [X] T016 [US1] Add corpus integration tests in `tests/test_acceptance.py` that index the current 12 fictional source files (nine Markdown, three TXT), verify parsed source identity/sections and citation traceability, and confirm the documented 5-20 document and 30-120 page-equivalent target using the 400-words-per-page convention (QR-001, QR-008, QR-012).

**Checkpoint**: A developer can build the index and obtain supported, cited answers across
both source formats using the public Python interface.

## Phase 4: User Story 2 - Recognize unsupported questions (Priority: P1)

**Goal**: Identify unsupported, partial, conflicting, and out-of-corpus policy questions
without presenting guesses as policy.

**Independent Test**: Use deterministic generator responses for unsupported, partial, and
conflicting evidence, plus an out-of-corpus question; verify each result identifies its
limitation and does not return unsupported claims or fabricated citations.

### Tests for User Story 2

- [X] T017 [P] [US2] Add deterministic answer tests for no evidence, partial evidence, conflicting policies, out-of-corpus questions, recommendation labeling, and source-injected instructions in `tests/test_answers.py` (QR-016).
- [X] T018 [P] [US2] Add error-path tests for blank questions, empty/malformed corpus, embedding/index/retrieval/provider failures, and invalid generated citation IDs/snippets in `tests/test_errors.py`; assert operational errors are distinguishable from unsupported results (QR-016).

### Implementation for User Story 2

- [X] T019 [US2] Implement unsupported/partial/conflicting outcomes and explicit evidence limitations in `src/hr_rag/answers.py`; require citations for supported factual claims, distinguish recommendations, refuse or redirect out-of-corpus questions, and treat retrieved instructions as data (QR-014, QR-016).
- [X] T020 [US2] Implement clear typed validation, ingestion, embedding, index, retrieval, generation, and grounding-validation errors in `src/hr_rag/models.py`, `src/hr_rag/documents.py`, `src/hr_rag/index.py`, and `src/hr_rag/answers.py`; do not convert failures into empty or unsupported success-shaped results (QR-016).
- [X] T021 [US2] Add at least three documented unsupported or partially supported acceptance cases and expected limitation checks in `tests/fixtures/acceptance_questions.json` and `tests/test_acceptance.py` (QR-016).

**Checkpoint**: Unsupported evidence and operational failure are distinguishable; no fabricated
policy fact or citation is returned for unsupported cases.

## Phase 5: User Story 3 - Combine multiple policies (Priority: P2)

**Goal**: Answer a question requiring evidence from multiple policy documents and report
incomplete evidence when a necessary source is missing.

**Independent Test**: Ask a documented question whose complete answer requires two distinct
policies; verify claims cite evidence from both. Repeat with one required source unavailable
and verify the missing portion is identified.

### Tests for User Story 3

- [X] T022 [P] [US3] Add a deterministic multi-document answer test and a missing-source variant in `tests/test_multidocument.py`, asserting each supported claim links to evidence from its required policy (QR-017).

### Implementation for User Story 3

- [X] T023 [US3] Ensure `retrieve` in `src/hr_rag/index.py` can return relevant chunks from multiple source documents when they rank in top-k, without duplicate/stale source metadata (QR-013, QR-017).
- [X] T024 [US3] Implement multi-source synthesis and missing-evidence reporting in `src/hr_rag/answers.py`; preserve per-claim citations to every supporting document and avoid filling gaps with assumptions (QR-015, QR-016, QR-017).
- [X] T025 [US3] Add at least one complex two-document question, expected claims, source IDs, and missing-evidence rubric to `tests/fixtures/acceptance_questions.json` and verify it through `tests/test_acceptance.py` (QR-017).

**Checkpoint**: A complete multi-document answer cites both sources; when evidence is missing,
the response identifies the unsupported portion.

## Phase 6: Polish and Cross-Cutting Concerns

**Purpose**: Make corpus rebuild, setup, and acceptance verification reproducible.

- [X] T026 [P] Document Python 3.11 setup, dependencies, environment configuration, model download/provider limits, index build/rebuild, Python question interface, errors, and tests in `README.md`; align commands with `specs/001-HR_Policy_RAG/quickstart.md` (QR-003, QR-004, QR-005, QR-007).
- [X] T027 [P] Add reproducibility checks for deterministic file ordering/chunking and verify no credentials are required by routine tests in `tests/test_reproducibility.py` (QR-006, QR-007).
- [ ] T028 Run the clean-install and complete F001 test/acceptance scenarios from `specs/001-HR_Policy_RAG/quickstart.md` on supported Windows Python 3.11 and Linux environments; record actual results and any native FAISS/model-resource limitations in `README.md` (QR-003, QR-004, QR-005, QR-008-QR-017).
- [X] T029 Confirm F001 scope and requirement coverage against `specs/001-HR_Policy_RAG/spec.md`, `specs/001-HR_Policy_RAG/plan.md`, and `docs/requirements/traceability.md`; document any unverified requirement evidence in `README.md` without changing project-level requirement statuses (QR-001, QR-003, QR-008-QR-017).
- [X] T030 Add a dedicated automated rebuild lifecycle test in `tests/test_rebuild.py` using an isolated temporary corpus and deterministic embedder; verify additions and edits appear after a successful rebuild, removed-source content is no longer retrievable, and a failed rebuild leaves the prior active snapshot unchanged and queryable (FR-007, SC-006).

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001 and T002 can run in parallel.
- **Foundational (Phase 2)**: Depends on setup; T003 and T004 can run in parallel after the package structure exists. Both block story implementation.
- **User stories (Phases 3-5)**: Depend on foundational tasks. US1 establishes the Python RAG path; US2 and US3 build on the answer and evidence behavior introduced in US1 and may proceed independently after US1's API stabilizes.
- **Polish (Phase 6)**: Depends on all selected stories.
- T030 specifically depends on the successful build, active-generation, and retrieval behavior from T012-T013; use an isolated temporary corpus so it does not modify the checked-in policies or index.

### User Story Dependencies

- **US1 (P1)**: Starts after Phase 2; no dependency on another story.
- **US2 (P1)**: Uses the shared answer API from US1; its validation/error tests can be drafted in parallel, but integration is completed after US1's result contract exists.
- **US3 (P2)**: Uses US1 retrieval and answer APIs; multi-document tests can be drafted in parallel, while implementation depends on the stable US1 contract.

### Parallel Opportunities

- T001 and T002 are independent setup changes.
- T003 and T004 touch separate files.
- US1 parser, index, answer-contract, and acceptance fixture tests (T005-T008) can be drafted in parallel before implementation.
- US1 document parsing/chunking and FAISS implementation require a stable shared chunk model; do not parallelize edits to `documents.py`.
- US2 failure tests and unsupported-answer tests (T017-T018) can be drafted in parallel; answer-path changes should be coordinated with US1.
- US3 multi-document tests (T022) can be drafted while US1 integration proceeds; retrieval and synthesis changes (T023-T024) depend on the US1 interface.
- README/quickstart updates and reproducibility test development (T026-T027) can be performed in parallel after interfaces and commands stabilize.
- T030 must verify the exact source-add/edit/removal and failed-activation behavior in FR-007 and SC-006; the broad T028 acceptance run does not replace this regression test.

### Parallel Example: Setup

```text
T001 -> requirements.txt and dependency compatibility
T002 -> src/hr_rag/ and tests/ structure
```

### Parallel Example: US1 test preparation

```text
T005 -> tests/test_documents.py
T006 -> tests/test_index.py
T007 -> tests/test_api.py
T008 -> tests/fixtures/acceptance_questions.json
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete setup and foundational tasks.
2. Implement and verify Markdown/TXT parsing, chunking, local indexing, retrieval, and the
   Python answer interface for covered questions.
3. Validate US1 independently against both formats and the current `corpus/`.
4. Continue with US2 unsupported/failure behavior and US3 multi-document synthesis before
   treating F001 as complete.

### Incremental Delivery

- Establish the covered-answer path first, then add unsupported/conflicting behavior, then
  multi-document synthesis.
- Run focused tests after each story and the complete acceptance suite before sign-off.
- F001 tasks do not implement MCP, agent workflows, a web interface, deployment, or the
  assignment-wide F006 evaluation.

## Requirement Coverage

| Requirement | Tasks |
|---|---|
| QR-001 | T008, T016 |
| QR-003 | T001, T003, T011, T026, T028 |
| QR-008 | T005, T009, T016 |
| QR-009 | T010 |
| QR-010 | T003, T006, T011 |
| QR-011 | T006, T012 |
| QR-012 | T005, T007, T009, T010, T012, T015, T016 |
| QR-013 | T006, T007, T013, T023 |
| QR-014 | T014, T019 |
| QR-015 | T007, T014, T015, T024 |
| QR-016 | T017, T018, T019, T020, T021, T024 |
| QR-017 | T022, T023, T024, T025 |
| QR-004-QR-007 (F006-owned; F001 contribution) | T001, T003, T026, T027, T028 |
| FR-007 / SC-006 (index rebuild lifecycle) | T012, T013, T030 |

Requirements outside F001, including QR-002 and QR-018 onward, remain assigned to later
features. Clean deployment, project-wide CI, and full 20-30-case evaluation remain F006
deliverables.
