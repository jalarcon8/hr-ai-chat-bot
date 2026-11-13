# Quickstart and Validation: HR Policy RAG

This workflow describes the implemented F001 package and its acceptance checks.

## Prerequisites and setup

- Python 3.11 and a compatible CPU FAISS distribution for the local operating system.
- The fictional Markdown and TXT policy corpus in project-root `corpus/`.
- Internet for initial dependencies/model downloads and, for the optional live generation
  smoke test, a provider API key and quota. Supply secrets via environment variables and never
  commit them.
- From the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python -m pytest
```

On Linux, use `python3.11 -m venv .venv` and `.venv/bin/python` for the corresponding commands.
The pinned dependencies, model identifiers, configuration variables, network requirements, and
local index path are documented in the root README. Routine tests do not need provider credentials.

## Acceptance scenarios

1. Build an index from `corpus/` and verify all 12 current fictional policy documents are
   included: nine Markdown and three TXT. Confirm Markdown headings, TXT `document_id` and
   `title` extraction, numbered TXT section labels, and source-traceable snippets. Verify that
   a valid TXT `document_id` is used, an absent one falls back to a deterministic filename
   identity, malformed identity metadata fails without fallback, and duplicate IDs fail before
   indexing. Other TXT header values are preserved but not interpreted. Use isolated synthetic
   fixtures for malformed identity fields, headingless sources, and failures; keep fixtures out
   of the default corpus.
2. Submit a covered policy question through the Python interface. Inspect claim-to-citation
   links, document identifiers, optional sections, and exact excerpts. See the
   [Python interface contract](contracts/python-interface.md).
3. Use a documented acceptance set with **at least five** covered questions across Markdown and
   TXT sources and verify each factual claim against its cited evidence. Include **at least three**
   unsupported or partially supported questions and **at least one** question that requires two
   policy documents; verify unsupported, partial, missing-source, and conflicting evidence
   behavior.
4. Add, edit, and remove temporary synthetic policies, rebuild, and confirm the new/changed
   evidence is available and removed content is no longer returned. Induce a rebuild failure
   and confirm the prior active snapshot remains intact and the failed rebuild is explicit.
5. Test blank input, empty corpus, empty/unreadable/malformed files, unsupported extensions,
   missing/corrupt/incompatible index, fewer chunks than k, embedding/generator failure,
   malformed citations, and prompt-injection-like text in a source. Operational failures must
   not be returned as unsupported policy answers.
6. Run unit and acceptance tests using deterministic embedder and generator doubles. If provider
   access is configured, run the opt-in live generation smoke test separately and record its
   model, configuration, and outcome; a mocked pass does not verify live provider behavior.

The corpus currently has 12 files (nine Markdown and three TXT), 12,528 words counted by the
project's regex-based word-count convention, and about 32 page equivalents using the
convention of 400 words per page. Report this convention and recalculate after corpus changes.
The final assignment's 20-30 case evaluation, MCP workflows, deployment, and demonstration
are not completed by F001 validation.
