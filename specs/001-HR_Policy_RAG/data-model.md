# Data Model: HR Policy RAG

These are logical Python data structures, not database tables. The current checked-in source
corpus is the root `corpus/` directory: 12 fictional policy documents, comprising nine Markdown
and three TXT files. The TXT sources have leading key-value metadata and numbered section
labels. Public operations and errors are defined in
[the contract](contracts/python-interface.md).

## PolicyDocument

| Field | Meaning and validation |
|---|---|
| `document_id` | Nonempty, unique ID: a valid TXT `document_id` metadata value when present, otherwise a deterministic normalized corpus-relative filename stem. Reject traversal, invalid metadata, failed filename derivation, and duplicates before indexing. |
| `title` | Nonempty Markdown title, valid TXT metadata title when present, or filename fallback. |
| `format` | Markdown or TXT, inferred from supported extension. |
| `text` | Original decoded UTF-8 text; empty or unreadable documents cause explicit ingestion failure. |
| `content_hash` | Hash of original bytes for snapshot provenance. |

All policy sources and fixtures are synthetic and identified as such. Production indexing
reads the configured policy corpus; test fixtures MUST NOT be included unless explicitly
selected by a test. TXT recognized fields `document_id` and `title` are extracted from the
leading metadata block, which ends at the first blank line. `document_id` is the identity
field: use it when valid; if absent, derive the ID deterministically from the normalized
corpus-relative filename stem. A present but malformed, empty, or otherwise invalid
`document_id` MUST raise a metadata validation error and MUST NOT trigger filename fallback.
If filename derivation fails, raise the same error. A provided `title` must be nonempty and
valid; it is descriptive metadata and does not replace the document ID. Retain but do not
interpret other header fields, including nested related-document lists. Reject duplicate
document IDs before embedding or index construction, and never index a document that fails
identity validation. Numbered body labels are used as sections. Source text remains unchanged
for citation offsets and snippets.

## PolicyChunk and Evidence

| Field | Meaning and validation |
|---|---|
| `chunk_id` | Unique within the index generation and mapped to one vector. |
| `document_id`, `title` | Parent document identity and display title. |
| `section` | Markdown heading path or TXT numbered section label when available; otherwise `None`. |
| `start`, `end` | Character offsets into original text; `0 <= start < end <= len(text)`. |
| `snippet` | Exact original substring at those offsets, not fabricated or rewritten. |
| `score` | Retrieval cosine similarity, present on retrieved evidence only. |

Overlapping chunks are permitted. Metadata must align exactly with vector IDs and generation.
A source's text and snippet are untrusted data, not application instructions.

## IndexSnapshot

| Field | Meaning and validation |
|---|---|
| `generation_id` | Unique identity for one complete build. |
| `embedding_model`, `revision`, `dimension` | Embedder identity and vector dimension; must match query configuration. |
| `chunking_config` | Token maximum, overlap, and tokenizer identity. |
| `documents`, `chunks` | Document hashes and ordered metadata used to interpret vectors. |
| `vector_count` | Equals number of metadata chunks and FAISS vectors. |

A build transitions from **building** to **validated** to **active** by pointer replacement.
On failure the candidate is not activated and the previous active generation remains
available. A query against a missing, invalid, or incompatible snapshot returns an explicit
error. Successful rebuilds contain only current source documents.

## Answer and Citation

- **Question**: nonblank user text; input is validated before retrieval.
- **Citation**: retrieved `chunk_id`, source ID/title, optional section, and exact snippet.
  Citation IDs must exist in the evidence supplied to the model.
- **Claim**: answer text and one or more citations for factual policy claims. Recommendations
  are labeled separately from policy facts.
- **AnswerResult**: status `answered`, `partial`, `unsupported`, or `conflicting`; claims,
  limitations, and citations. `unsupported` has no unsupported factual claims or fabricated
  citations. Partial/conflicting results explicitly describe what is missing or conflicts.
- **Operational error**: invalid input, ingestion, index, embedding, retrieval, generation,
  or grounding validation failure; never encoded as an `unsupported` answer.

Checking IDs and exact snippets proves source correspondence, not semantic entailment. Tests
and evaluation must separately verify that each cited passage actually supports its claim.
