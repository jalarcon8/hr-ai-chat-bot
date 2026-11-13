import pytest

from hr_rag import ChunkingConfig, build_index, retrieve
from hr_rag.models import IndexError, MetadataValidationError
from tests.fixtures.doubles import DeterministicEmbedder
import hr_rag.index as index_module


pytest.importorskip("faiss")


def test_successful_rebuild_adds_edits_removes_and_failure_preserves_active(tmp_path, monkeypatch):
    corpus = tmp_path / "temporary-corpus"
    corpus.mkdir()
    first_doc = corpus / "one.txt"
    second_doc = corpus / "two.md"
    first_doc.write_text(
        "document_id: DOC-ONE\ntitle: One\n\n1.1 Original\n"
        "The unique policy marker is amber-otter.",
        encoding="utf-8",
    )
    second_doc.write_text(
        "document_id: DOC-TWO\ntitle: Two\n\n# Old policy\n"
        "The unique policy marker is cobalt-badger.",
        encoding="utf-8",
    )
    index_dir = tmp_path / "local-index"
    embedder = DeterministicEmbedder()
    settings = ChunkingConfig()
    initial = build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=settings)
    assert retrieve("amber-otter", index_dir, embedder=embedder).evidence[0].document_id == "DOC-ONE"

    first_doc.write_text(
        "document_id: DOC-ONE\ntitle: One Revised\n\n1.1 Revised\n"
        "The unique policy marker is amber-fox.",
        encoding="utf-8",
    )
    second_doc.unlink()
    (corpus / "three.md").write_text(
        "document_id: DOC-THREE\ntitle: Three\n\n# Added\n"
        "The unique policy marker is violet-heron.",
        encoding="utf-8",
    )
    updated = build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=settings)
    assert updated.generation_id != initial.generation_id
    assert updated.document_count == 2
    assert retrieve("amber-fox", index_dir, embedder=embedder).evidence[0].document_id == "DOC-ONE"
    current_ids = {item.document_id for item in retrieve(
        "cobalt-badger", index_dir, embedder=embedder, k=10
    ).evidence}
    assert "DOC-TWO" not in current_ids
    assert "DOC-THREE" in {item.document_id for item in retrieve(
        "violet-heron", index_dir, embedder=embedder, k=10
    ).evidence}

    (corpus / "broken.txt").write_text("document_id:\n\ninvalid identity", encoding="utf-8")

    class BrokenEmbedder(DeterministicEmbedder):
        def encode(self, texts):
            raise RuntimeError("should not be called for invalid identity")

    with pytest.raises(MetadataValidationError):
        build_index(index_dir, corpus_dir=corpus, embedder=BrokenEmbedder(), chunking_config=settings)
    active = retrieve("amber-fox", index_dir, embedder=embedder)
    assert active.generation_id == updated.generation_id
    assert active.evidence[0].document_id == "DOC-ONE"

    (corpus / "broken.txt").unlink()
    original_replace = index_module.os.replace

    def fail_active_pointer(source, destination):
        if str(destination) == str(index_dir / "active.json"):
            raise OSError("simulated pointer activation failure")
        original_replace(source, destination)

    monkeypatch.setattr(index_module.os, "replace", fail_active_pointer)
    with pytest.raises(IndexError, match="Could not build or activate"):
        build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=settings)
    monkeypatch.setattr(index_module.os, "replace", original_replace)
    after_activation_failure = retrieve("amber-fox", index_dir, embedder=embedder)
    assert after_activation_failure.generation_id == updated.generation_id
    assert after_activation_failure.evidence[0].document_id == "DOC-ONE"
