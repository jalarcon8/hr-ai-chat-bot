from pathlib import Path

import pytest

from hr_rag.config import ChunkingConfig
from hr_rag.documents import chunk_documents, ingest_corpus, parse_document
from hr_rag.index import build_index
from hr_rag.models import DocumentValidationError, MetadataValidationError
from tests.fixtures.doubles import DeterministicEmbedder


def write_source(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_markdown_metadata_and_heading_path(tmp_path):
    path = write_source(
        tmp_path,
        "policy.md",
        "document_id: HR-100\ntitle: Policy title\n\n# Main\n\nBody with evidence.",
    )
    document = parse_document(path, tmp_path)
    chunks = chunk_documents([document], ChunkingConfig(max_tokens=10, overlap_tokens=2))
    assert document.document_id == "HR-100"
    assert document.title == "Policy title"
    assert chunks[0].section == "Main"
    assert chunks[0].snippet.endswith("Body with evidence.")
    assert document.text[chunks[0].start : chunks[0].end] == chunks[0].snippet


def test_txt_metadata_numbered_section_and_nonrecognized_nested_values(tmp_path):
    path = write_source(
        tmp_path,
        "policy.txt",
        "document_id: HR-101\ntitle: TXT policy\nrelated_documents:\n  - HR-001\n\n"
        "1.1 Eligibility\nEmployees are eligible for the benefit.",
    )
    document = parse_document(path, tmp_path)
    chunks = chunk_documents([document], ChunkingConfig(max_tokens=20, overlap_tokens=2))
    assert document.document_id == "HR-101"
    assert chunks[0].section == "1.1 Eligibility"
    assert "Employees are eligible" in chunks[0].snippet
    assert "related_documents" not in chunks[0].snippet


def test_missing_identity_uses_deterministic_relative_filename(tmp_path):
    path = write_source(tmp_path, "Sub Folder\\No ID.txt", "Plain policy text.")
    document = parse_document(path, tmp_path)
    assert document.document_id == "sub folder/no id"


@pytest.mark.parametrize(
    "metadata",
    [
        "document_id:\ntitle: Valid title\n\nPolicy text.",
        "document_id: ../outside\ntitle: Valid title\n\nPolicy text.",
        "document_id HR-1\ntitle: Valid title\n\nPolicy text.",
        "document_id: HR-1\ndocument_id: HR-2\n\nPolicy text.",
        "document_id: HR-1\ntitle:\n\nPolicy text.",
    ],
)
def test_invalid_recognized_identity_metadata_does_not_fall_back(tmp_path, metadata):
    path = write_source(tmp_path, "fallback-name.txt", metadata)
    with pytest.raises(MetadataValidationError):
        parse_document(path, tmp_path)


def test_duplicate_ids_rejected_before_embedding_or_indexing(tmp_path):
    write_source(tmp_path, "first.txt", "document_id: SHARED\n\n1. One\nfirst")
    write_source(tmp_path, "second.txt", "document_id: shared\n\n1. One\nsecond")
    with pytest.raises(MetadataValidationError, match="Duplicate document identity"):
        ingest_corpus(tmp_path)

    class EmbedderMustNotRun:
        model_id = "unused"

        def encode(self, texts):
            raise AssertionError("embedding must not start when document identities are duplicated")

        def tokenize_with_offsets(self, text):
            return []

    with pytest.raises(MetadataValidationError, match="Duplicate document identity"):
        build_index(
            tmp_path / "index",
            corpus_dir=tmp_path,
            embedder=EmbedderMustNotRun(),
            chunking_config=ChunkingConfig(),
        )


def test_empty_and_invalid_utf8_documents_fail(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("   ", encoding="utf-8")
    with pytest.raises(DocumentValidationError):
        parse_document(empty, tmp_path)
    invalid = tmp_path / "invalid.txt"
    invalid.write_bytes(b"\xff")
    with pytest.raises(DocumentValidationError):
        parse_document(invalid, tmp_path)


def test_headingless_source_uses_document_level_reference(tmp_path):
    path = write_source(tmp_path, "plain.md", "A paragraph without headings.")
    document = parse_document(path, tmp_path)
    chunks = chunk_documents([document], ChunkingConfig(max_tokens=20, overlap_tokens=0))
    assert chunks[0].section is None


def test_unsupported_format_is_explicit(tmp_path):
    path = write_source(tmp_path, "policy.pdf", "not a supported format")
    with pytest.raises(DocumentValidationError, match="Unsupported"):
        parse_document(path, tmp_path)


def test_chunk_token_limit_and_overlap_are_respected(tmp_path):
    path = write_source(tmp_path, "chunks.md", "# Heading\n" + " ".join(f"token{i}" for i in range(12)))
    doc = parse_document(path, tmp_path)
    tokenizer = DeterministicEmbedder()
    chunks = chunk_documents([doc], ChunkingConfig(max_tokens=5, overlap_tokens=2), tokenizer)
    token_sets = [tokenizer.tokenize_with_offsets(chunk.snippet) for chunk in chunks]
    assert all(len(offsets) <= 5 for offsets in token_sets)
    assert len(chunks) > 1
    assert chunks[0].end > chunks[1].start
