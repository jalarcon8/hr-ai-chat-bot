import hashlib
import json
from dataclasses import replace

import faiss
import pytest
from pydantic import ValidationError

from hr_mcp import policy
from hr_rag import ChunkingConfig, build_index, retrieve
from hr_rag.models import EmbeddingError, IndexError, RetrievalResult
from tests.fixtures.doubles import DeterministicEmbedder


@pytest.fixture
def snapshot(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    text = (
        "document_id: DOC-1\r\ntitle: Synthetic Policy\r\n\r\n"
        "# Travel\r\n\r\n"
        "Cafe\u0301 \U0001f600 alpha beta gamma delta epsilon zeta eta theta iota kappa.\r\n"
        "# Other\r\n\r\nOther policy content remains separate.\r\n"
    )
    (corpus / "policy.md").write_bytes(text.encode("utf-8"))
    index = tmp_path / "index"
    embedder = DeterministicEmbedder()
    config = ChunkingConfig(max_tokens=5, overlap_tokens=2)
    built = build_index(index, corpus_dir=corpus, embedder=embedder, chunking_config=config)
    return corpus, index, embedder, config, built


def load_metadata(index, generation):
    return json.loads(
        (index / "generations" / generation / "metadata.json").read_text(encoding="utf-8")
    )


def update_metadata(index, generation, metadata):
    metadata_file = index / "generations" / generation / "metadata.json"
    raw = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    metadata_file.write_bytes(raw)
    pointer_file = index / "active.json"
    pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
    pointer["metadata_sha256"] = hashlib.sha256(raw).hexdigest()
    pointer_file.write_text(json.dumps(pointer), encoding="utf-8")


def test_search_preserves_f001_candidates_order_scores_and_default_k(snapshot):
    _, index, embedder, _, built = snapshot
    expected = retrieve("alpha travel", index, embedder=embedder, k=5)
    result = policy.search_policy_documents("alpha travel", index, embedder=embedder)
    assert result.status == "found"
    assert result.evidence_kind == "candidate"
    assert result.generation_id == built.generation_id
    assert len(result.evidence) == len(expected.evidence) == 5
    for actual, source in zip(result.evidence, expected.evidence, strict=True):
        assert actual.model_dump() == {
            "document_id": source.document_id,
            "title": source.title,
            "section": source.section,
            "snippet": source.snippet,
            "chunk_id": source.chunk_id,
            "generation_id": built.generation_id,
            "score": source.score,
        }
    assert len(policy.search_policy_documents("alpha", index, embedder=embedder, k=1).evidence) == 1


def test_unrelated_nonempty_retrieval_remains_candidates(snapshot):
    _, index, embedder, _, _ = snapshot
    result = policy.search_policy_documents("xylophone", index, embedder=embedder)
    assert result.status == "found"
    assert result.evidence_kind == "candidate"
    assert result.evidence


def test_empty_retrieval_is_not_found(monkeypatch, snapshot):
    _, index, embedder, _, built = snapshot

    def empty_retrieve(question, index_dir, *, embedder, k):
        return RetrievalResult(question=question, generation_id=built.generation_id)

    monkeypatch.setattr(policy, "retrieve", empty_retrieve)
    result = policy.search_policy_documents("question", index, embedder=embedder)
    assert result.model_dump() == {
        "status": "not_found",
        "evidence": [],
        "generation_id": built.generation_id,
    }


@pytest.mark.parametrize(
    ("question", "k"),
    [("", 1), ("  ", 1), (12, 1), ("question", 0), ("question", -1), ("question", True),
     ("question", 1.5)],
)
def test_search_rejects_invalid_input_before_retrieval(snapshot, tmp_path, question, k):
    _, _, embedder, _, _ = snapshot
    with pytest.raises(ValidationError):
        policy.search_policy_documents(question, tmp_path / "missing", embedder=embedder, k=k)


def test_section_matches_exact_labels_orders_chunks_and_uses_character_offsets(snapshot):
    corpus, index, _, _, built = snapshot
    raw = (corpus / "policy.md").read_bytes()
    text = raw.decode("utf-8")
    metadata = load_metadata(index, built.generation_id)
    chunks = sorted(
        (chunk for chunk in metadata["chunks"] if chunk["section"] == "Travel"),
        key=lambda chunk: chunk["start"],
    )
    assert len(chunks) > 1
    metadata["chunks"].reverse()
    update_metadata(index, built.generation_id, metadata)
    result = policy.get_policy_section("DOC-1", "Travel", index)
    assert result.status == "found"
    assert result.generation_id == built.generation_id
    assert [item.chunk_id for item in result.evidence] == [chunk["chunk_id"] for chunk in chunks]
    for item, chunk in zip(result.evidence, chunks, strict=True):
        assert item.model_dump() == {
            "document_id": "DOC-1",
            "title": "Synthetic Policy",
            "section": "Travel",
            "snippet": chunk["snippet"],
            "chunk_id": chunk["chunk_id"],
            "generation_id": built.generation_id,
        }
        assert text[chunk["start"] : chunk["end"]] == item.snippet
    assert any(
        raw[chunk["start"] : chunk["end"]].decode("utf-8", errors="replace") != chunk["snippet"]
        for chunk in chunks
    )
    assert chunks[0]["end"] > chunks[1]["start"]
    for document_id, section in [
        ("doc-1", "Travel"), ("DOC-1", "travel"), ("DOC-1", "Trav"), ("MISSING", "Travel")
    ]:
        missing = policy.get_policy_section(document_id, section, index)
        assert missing.model_dump() == {
            "status": "not_found", "evidence": [], "generation_id": built.generation_id
        }


@pytest.mark.parametrize(("document_id", "section"), [("", "Travel"), ("DOC-1", " "), (1, "X")])
def test_section_rejects_invalid_input(snapshot, document_id, section):
    _, index, _, _, _ = snapshot
    with pytest.raises(ValidationError):
        policy.get_policy_section(document_id, section, index)


def test_section_matches_only_the_requested_document(snapshot):
    corpus, index, embedder, config, _ = snapshot
    (corpus / "second.md").write_text(
        "document_id: DOC-10\ntitle: Another Policy\n\n# Travel\n\nDifferent travel rules.",
        encoding="utf-8",
    )
    build_index(index, corpus_dir=corpus, embedder=embedder, chunking_config=config)
    first = policy.get_policy_section("DOC-1", "Travel", index)
    second = policy.get_policy_section("DOC-10", "Travel", index)
    assert first.status == second.status == "found"
    assert {item.document_id for item in first.evidence} == {"DOC-1"}
    assert {item.document_id for item in second.evidence} == {"DOC-10"}


def test_section_uses_one_active_snapshot(monkeypatch, snapshot):
    _, index, _, _, built = snapshot
    active_metadata = policy._active_metadata
    calls = []

    def counted_metadata(index_dir):
        calls.append(index_dir)
        return active_metadata(index_dir)

    monkeypatch.setattr(policy, "_active_metadata", counted_metadata)
    result = policy.get_policy_section("DOC-1", "Travel", index)
    assert result.generation_id == built.generation_id
    assert calls == [index]


def test_section_reads_index_not_live_corpus_and_tracks_generation_changes(snapshot):
    corpus, index, embedder, config, first = snapshot
    before = policy.get_policy_section("DOC-1", "Travel", index)
    (corpus / "policy.md").write_text(
        "document_id: DOC-1\ntitle: New Policy\n\n# Travel\n\nNew policy content.",
        encoding="utf-8",
    )
    assert policy.get_policy_section("DOC-1", "Travel", index) == before
    second = build_index(index, corpus_dir=corpus, embedder=embedder, chunking_config=config)
    after = policy.get_policy_section("DOC-1", "Travel", index)
    search = policy.search_policy_documents("new policy", index, embedder=embedder)
    assert second.generation_id != first.generation_id
    assert after.generation_id == search.generation_id == second.generation_id
    assert all(item.generation_id == second.generation_id for item in after.evidence)
    assert after.evidence[0].title == "New Policy"


@pytest.mark.parametrize(
    ("field", "value"),
    [("chunk_id", ""), ("document_id", "UNKNOWN"), ("title", None), ("snippet", 7)],
)
def test_invalid_chunk_metadata_is_an_index_error(snapshot, field, value):
    _, index, embedder, _, built = snapshot
    metadata = load_metadata(index, built.generation_id)
    metadata["chunks"][0][field] = value
    update_metadata(index, built.generation_id, metadata)
    with pytest.raises(IndexError):
        policy.get_policy_section("DOC-1", "Travel", index)
    with pytest.raises(IndexError):
        policy.search_policy_documents("travel", index, embedder=embedder, k=100)


@pytest.mark.parametrize(("start", "end"), [(-1, 10), (10, 10), (True, 10), (1, "2")])
def test_invalid_citation_offsets_are_distinct_from_corrupt_snapshot(snapshot, start, end):
    _, index, embedder, _, built = snapshot
    metadata = load_metadata(index, built.generation_id)
    metadata["chunks"][0]["start"] = start
    metadata["chunks"][0]["end"] = end
    update_metadata(index, built.generation_id, metadata)
    with pytest.raises(policy.InvalidCitationMetadataError):
        policy.get_policy_section("DOC-1", "Travel", index)
    with pytest.raises(IndexError):
        policy.search_policy_documents("travel", index, embedder=embedder, k=100)


@pytest.mark.parametrize("field", ["start", "end"])
def test_missing_citation_offset_is_distinct_from_corrupt_snapshot(snapshot, field):
    _, index, embedder, _, built = snapshot
    metadata = load_metadata(index, built.generation_id)
    del metadata["chunks"][0][field]
    update_metadata(index, built.generation_id, metadata)
    with pytest.raises(policy.InvalidCitationMetadataError):
        policy.get_policy_section("DOC-1", "Travel", index)
    with pytest.raises(IndexError):
        policy.search_policy_documents("travel", index, embedder=embedder)


def test_search_rejects_mixed_index_generations(monkeypatch, snapshot):
    _, index, embedder, _, _ = snapshot

    def different_generation(question, index_dir, *, embedder, k):
        return RetrievalResult(question=question, generation_id="0" * 32)

    monkeypatch.setattr(policy, "retrieve", different_generation)
    with pytest.raises(IndexError):
        policy.search_policy_documents("travel", index, embedder=embedder)


@pytest.mark.parametrize("change", ["wrong_snippet", "nonfinite_score"])
def test_search_rejects_invalid_retrieval_evidence(monkeypatch, snapshot, change):
    _, index, embedder, _, _ = snapshot
    result = retrieve("travel", index, embedder=embedder, k=1)
    if change == "wrong_snippet":
        evidence = replace(result.evidence[0], snippet="not the indexed snippet")
    else:
        evidence = replace(result.evidence[0], score=float("nan"))

    def invalid_retrieve(question, index_dir, *, embedder, k):
        return replace(result, evidence=(evidence,))

    monkeypatch.setattr(policy, "retrieve", invalid_retrieve)
    with pytest.raises(IndexError):
        policy.search_policy_documents("travel", index, embedder=embedder)


def test_missing_corrupt_index_and_embedding_failure_are_errors(snapshot, tmp_path):
    _, index, embedder, _, built = snapshot
    with pytest.raises(IndexError):
        policy.search_policy_documents("question", tmp_path / "missing", embedder=embedder)
    with pytest.raises(IndexError):
        policy.get_policy_section("DOC-1", "Travel", tmp_path / "missing")

    class BrokenEmbedder(DeterministicEmbedder):
        def encode(self, texts):
            raise EmbeddingError("Synthetic embedding failure.")

    with pytest.raises(EmbeddingError):
        policy.search_policy_documents("question", index, embedder=BrokenEmbedder())
    (index / "generations" / built.generation_id / "metadata.json").write_text(
        "{}", encoding="utf-8"
    )
    with pytest.raises(IndexError):
        policy.search_policy_documents("question", index, embedder=embedder)
    with pytest.raises(IndexError):
        policy.get_policy_section("DOC-1", "Travel", index)


@pytest.mark.parametrize("valid_checksum", [False, True])
def test_corrupt_faiss_file_is_an_index_error(snapshot, valid_checksum):
    _, index, embedder, _, built = snapshot
    index_file = index / "generations" / built.generation_id / "index.faiss"
    index_file.write_bytes(b"corrupt")
    if valid_checksum:
        pointer_file = index / "active.json"
        pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
        pointer["index_sha256"] = hashlib.sha256(index_file.read_bytes()).hexdigest()
        pointer_file.write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(IndexError):
        policy.search_policy_documents("question", index, embedder=embedder)
    with pytest.raises(IndexError):
        policy.get_policy_section("DOC-1", "Travel", index)


@pytest.mark.parametrize("mismatch", ["dimension", "count"])
def test_faiss_metadata_mismatch_is_an_index_error(snapshot, mismatch):
    _, index, embedder, _, built = snapshot
    if mismatch == "dimension":
        metadata = load_metadata(index, built.generation_id)
        metadata["dimension"] += 1
        update_metadata(index, built.generation_id, metadata)
    else:
        index_file = index / "generations" / built.generation_id / "index.faiss"
        faiss_index = faiss.read_index(str(index_file))
        faiss_index.reset()
        faiss.write_index(faiss_index, str(index_file))
        pointer_file = index / "active.json"
        pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
        pointer["index_sha256"] = hashlib.sha256(index_file.read_bytes()).hexdigest()
        pointer_file.write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(IndexError):
        policy.search_policy_documents("question", index, embedder=embedder)
    with pytest.raises(IndexError):
        policy.get_policy_section("DOC-1", "Travel", index)
