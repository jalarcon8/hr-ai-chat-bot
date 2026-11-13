# Contract: Python Policy RAG Interface

This is the planned public interface, not existing code. Importable symbols and exact return
types must be implemented and documented consistently; all operations are synchronous for
this increment. The later MCP server calls `retrieve` rather than implementing retrieval again.

## Operations

### `build_index(index_dir, *, corpus_dir="corpus", embedder, chunking_config) -> BuildResult`

- Ingest all supported Markdown and TXT files beneath the configured corpus root in a
  deterministic order. The repository default source corpus is the project-root `corpus/`
  directory, currently 12 fictional policy documents (nine Markdown and three TXT). The
  current TXT documents contain a leading metadata block through the first blank line and
  numbered section labels such as `2.1 Eligibility`. Extract recognized `document_id` and
  `title` scalar fields and body section labels; retain but do not interpret other metadata,
  including nested related-document lists. A valid `document_id` takes precedence; when that
  field is absent, derive the ID deterministically from the normalized corpus-relative filename
  stem. If `document_id` is present but malformed, empty, or invalid, or filename derivation
  fails, raise `MetadataValidationError` without falling back from invalid metadata. A provided
  `title` must also be valid and nonempty but does not determine the ID. Preserve original text
  for snippets. Test fixtures MUST NOT be included in the default corpus. Reject missing/empty
  corpus, empty/unreadable supported documents, duplicate document IDs before embedding or
  index construction, decoding errors, malformed recognized metadata, and invalid chunk
  configuration explicitly. Documents failing identity validation MUST NOT be indexed.
- Build and validate a complete new generation before replacing the active pointer.
  Successful rebuilds incorporate additions and edits and exclude removals.
- Return generation ID, document and chunk counts, model identity and index location.
  On failure raise a typed ingestion, embedding, or index error; do not activate partial
  data. A prior active generation remains unchanged and is not reported as the new build.

### `retrieve(question, index_dir, *, embedder, k=5) -> RetrievalResult`

- Reject blank questions and `k < 1` as `InvalidInputError`; validate index/model
  compatibility before querying.
- Return up to `min(k, chunk_count)` scored evidence records in descending similarity
  order, including chunk ID, document ID, title, optional Markdown heading path or TXT
  numbered section, and exact source snippet.
  An empty result is a valid no-evidence outcome only when retrieval completed successfully.
- A score is a ranking signal, not proof of relevance, sufficiency, or correctness.
  Missing, corrupt, or mismatched index and embedding failures raise typed operational errors.

### `answer_question(question, index_dir, *, embedder, generator, k=5) -> AnswerResult`

- Validate input; retrieve evidence through the same public retrieval component; provide
  retrieved text and metadata to the generator as untrusted data.
- Return `status`, `claims`, `limitations`, and `citations`. Allowed statuses are `answered`,
  `partial`, `unsupported`, and `conflicting`; each policy claim references at least one
  citation, and citations resolve to the evidence used with exact traceable snippets.
- For no or insufficient evidence, return an explicit `unsupported` or `partial` result
  without invented facts. For conflicts, identify the disagreement and cite the evidence.
  Distinguish recommendations from policy facts.
- Validate the generation schema, referenced IDs and exact evidence snippets before returning.
  Unknown source IDs, invalid response formats or unsupported output are rejected rather than
  presented as grounded. Semantic support is assessed by the model and acceptance evaluation;
  structural validation is not a guarantee of truth.
- Invalid input and provider, index, retrieval, or grounding-validation failures raise typed
  exceptions rather than returning an unsupported answer. Exclude secrets from errors and logs.

## Evidence and testing contract

Callers can inspect document identifiers, optional sections, snippets, scores, claim-to-citation
links, and limitations without parsing prose. Routine tests inject deterministic embedding and
generation doubles, test the real FAISS wrapper where available, and never require a provider
key. They cover the root Markdown/TXT corpus in integration checks and use separate minimal
synthetic Markdown/TXT fixtures for fast format and failure checks. An opt-in live smoke test
validates the real model path separately; its success is not inferred from doubles.
