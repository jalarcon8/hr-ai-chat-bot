# Research: HR Policy RAG

**Refreshed**: 2026-11-12

F001 now uses the checked-in fictional policy corpus at the project-root `corpus/` directory.
The inventory contains 12 fictional policy documents across the HR topics listed in the
specification: nine Markdown and three TXT. Their combined size is 12,528 words under the
project's regex-based counting convention, or approximately 32 page equivalents at 400 words
per page. The TXT sources are the holiday, remote-work, and expense reimbursement policies;
each includes a key-value metadata header and numbered section labels. Test those real
structures and retain small isolated fixtures for malformed headers and headingless content.
The assignment's 30-120 page and 5-20 document scope applies to the final coherent corpus;
document shortness and the page-equivalent convention must be reviewed as the corpus evolves.

## Decisions

### Embeddings and similarity

**Decision:** Use the CPU Sentence Transformers model
`sentence-transformers/all-MiniLM-L6-v2`, normalized query and document embeddings, and a
FAISS `IndexFlatIP` for exact cosine-ranked retrieval. Start with configurable `k=5`,
capped at the number of indexed chunks; treat all defaults as evaluation candidates. Make
normalization explicit for both corpus and query vectors and verify that the FAISS dimension
matches the embedding model output.

**Rationale:** Local embeddings avoid per-query embedding costs, and an exact flat index is
simple for a small synthetic corpus. FAISS inner product represents cosine similarity only
when both sets of vectors are normalized. The model requires a one-time download unless
pre-cached; measure package, model, memory, and cold-start costs on the eventual host.

**Alternatives considered:** Hosted embeddings add an external dependency and recurring
limits; approximate indexes add complexity at this scale. Larger or multilingual models may
be evaluated later if the corpus and measured retrieval quality require them.

**Sources:** [Sentence Transformers similarity documentation](https://www.sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html);
[FAISS metric documentation](https://github.com/facebookresearch/faiss/wiki/MetricType-and-distances).

### Documents, chunking, and metadata

**Decision:** Read UTF-8 Markdown and TXT, use a stable corpus-relative document ID and
Markdown heading path where present, and split sections into overlapping token-bounded
chunks using the selected embedding tokenizer. Set an initial maximum of 200 embedding
tokens per chunk and 30 tokens overlap, accounting for special tokens, with deterministic
splitting and a source character span for each chunk. Plain text and sources without detectable sections use document-level references. For the
current TXT policies, parse the leading metadata block through the first blank line and extract
the recognized `document_id` and `title` scalar fields. A valid `document_id` takes precedence;
if absent, derive the ID from the normalized corpus-relative filename stem. A malformed or
empty provided `document_id`, invalid provided `title`, or failed filename derivation raises
a metadata validation error. Reject duplicate IDs before embedding or indexing, and never
index identity-invalid documents. Ignore other header fields (including nested related-document
lists) for retrieval metadata. Recognize numbered body lines such as `2.1 Eligibility` as
section labels. Preserve original text and exact source offsets for citations; never synthesize
policy text from parsed metadata. Enumerate
`corpus/**/*.md` and `corpus/**/*.txt` deterministically; retain separate small fixtures for
malformed headers, headingless documents, and failures.

**Rationale:** Section-aware bounded chunks improve traceability and avoid silent embedding
truncation. Deterministic chunking supports reproducible rebuilds. Extracting only the
recognized TXT identity fields and numbered section conventions retains stable source IDs and
useful citation locations without introducing a general YAML/document-conversion framework.

**Alternatives considered:** Whole-document embeddings lose precision; fixed character-only
windows can exceed the model's token limit. Chunk size and overlap should be compared during
evaluation rather than treated as proven optimal.

### Index lifecycle

**Decision:** Build a complete FAISS index and JSON metadata snapshot in a new local
generation directory, validate index count/dimension/model identity and metadata mappings,
then atomically replace a small active-generation pointer. Query only the active generation.
Rebuild from the complete corpus; never merge old entries into the new generation.

**Rationale:** A consistent snapshot avoids mixed metadata/index state and ensures removed
documents do not survive a successful rebuild. Failed rebuilds must return errors and leave
the previous snapshot intact; callers must be told the active index is not the requested new
corpus. Persist a model revision and configuration fingerprint to reject incompatible reloads.

**Alternatives considered:** Incremental updates need deletion and synchronization logic;
an in-memory-only index requires repeated embedding on restart.

### Generation and grounding

**Decision:** Use a configurable Groq model through its Python SDK, with a structured
claim-and-evidence response. Supply only retrieved evidence plus metadata, mark policy
content as untrusted data, require support for each policy claim, and separately represent
missing/conflicting information. Validate response shape, evidence IDs, and exact citation
snippets against the active retrieval result. Reject invalid or unsupported-looking outputs
as an explicit grounding error or an insufficient-evidence response; never invent citations.

**Rationale:** Groq matches the proposed roadmap and its documentation describes its Python
SDK and API configuration. Structural citation checks alone do not prove semantic entailment:
the model must assess support, and acceptance evaluation must manually or independently
check claims against evidence. No similarity threshold alone establishes truth, absence, or
completeness. Evaluation must cover unsupported, partial, conflicting, and multi-document
cases and adjust prompts/retrieval before claiming success.

**Alternatives considered:** Directly returning retrieved snippets cannot answer synthesis
questions; a second verifier model or reranker adds cost and infrastructure before evidence
shows it is necessary. A configurable model permits replacement if the chosen free tier,
model access, or rate limits change.

**Source:** [Groq API compatibility documentation](https://console.groq.com/docs/openai).

### Interface and errors

**Decision:** Expose separate Python `build_index`, `retrieve`, and `answer_question`
operations, with explicit typed results and errors; define exact shapes in
[the interface contract](contracts/python-interface.md). Allow injected embedding and
generator implementations in tests; no MCP, HTTP, or CLI is needed in F001.

**Rationale:** Later MCP tools can reuse retrieval directly without generating an answer or
creating an additional index. Deterministic test doubles avoid external calls in CI.

**Alternatives considered:** One opaque answer-only function prevents evidence reuse;
building an MCP server now violates the specified feature boundary.

### Supported environment and verification

**Decision:** Target Python 3.11 on Windows locally and Linux for eventual deployment.
Pin compatible dependencies in the implementation manifest and validate installations on
both targets; use a configured Groq key only in the opt-in end-to-end smoke test.

**Rationale:** A shared baseline is simpler to reproduce; FAISS native wheel support,
provider limits, and host memory are deployment risks, not assumptions of success.

**Alternatives considered:** Broad untested Python support would increase validation effort.
The assignment-level CI pipeline and live deployment remain later work, but F001 tests and
setup documentation start here.
