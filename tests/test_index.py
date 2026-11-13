import json
import sys
from types import ModuleType

import numpy as np
import pytest

faiss = pytest.importorskip("faiss")
from hr_rag.config import ChunkingConfig
from hr_rag.index import SentenceTransformerEmbedder, build_index, retrieve
from hr_rag.models import EmbeddingError, IndexError, InvalidInputError
from tests.fixtures.doubles import DeterministicEmbedder


def test_sentence_transformer_embedder_forces_cpu(monkeypatch):
    captured = {}

    class FakeSentenceTransformer:
        def __init__(self, model_name, **options):
            captured["model_name"] = model_name
            captured.update(options)
            self.tokenizer = object()

    sentence_transformers_module = ModuleType("sentence_transformers")
    sentence_transformers_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", sentence_transformers_module)

    SentenceTransformerEmbedder("test-model", revision="test-revision")

    assert captured == {
        "model_name": "test-model",
        "revision": "test-revision",
        "device": "cpu",
    }


def make_corpus(path):
    path.mkdir()
    (path / "one.md").write_text(
        "document_id: DOC-1\ntitle: One\n\n# Apples\n\nApples are red fruit.",
        encoding="utf-8",
    )
    (path / "two.txt").write_text(
        "document_id: DOC-2\ntitle: Two\n\n1.1 Bananas\nBananas are yellow fruit.",
        encoding="utf-8",
    )


def test_build_persists_aligned_faiss_metadata_and_retrieves_top_k(tmp_path):
    corpus = tmp_path / "corpus"
    make_corpus(corpus)
    index_dir = tmp_path / "index"
    embedder = DeterministicEmbedder()
    built = build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())
    metadata = json.loads((index_dir / "generations" / built.generation_id / "metadata.json").read_text())
    stored_index = faiss.read_index(
        str(index_dir / "generations" / built.generation_id / "index.faiss")
    )
    stored_vectors = stored_index.reconstruct_n(0, stored_index.ntotal)
    assert built.document_count == 2
    assert built.chunk_count == metadata["vector_count"]
    assert stored_index.d == metadata["dimension"]
    assert len(metadata["chunks"]) == stored_index.ntotal
    assert metadata["chunking_config"]["tokenizer_id"] == embedder.tokenizer_id
    assert np.allclose(np.linalg.norm(stored_vectors, axis=1), 1.0, atol=1e-5)
    all_results = retrieve("apples red fruit", index_dir, embedder=DeterministicEmbedder(), k=100)
    assert len(all_results.evidence) == built.chunk_count
    assert list(item.score for item in all_results.evidence) == sorted(
        (item.score for item in all_results.evidence), reverse=True
    )
    result = retrieve("apples red fruit", index_dir, embedder=DeterministicEmbedder(), k=1)
    assert len(result.evidence) == 1
    assert result.evidence[0].document_id == "DOC-1"
    assert result.generation_id == built.generation_id
    assert result.evidence[0].snippet


@pytest.mark.parametrize("question,k", [("", 1), ("  ", 1), ("valid", 0), ("valid", -1)])
def test_retrieve_rejects_invalid_inputs(tmp_path, question, k):
    with pytest.raises(InvalidInputError):
        retrieve(question, tmp_path, embedder=DeterministicEmbedder(), k=k)


def test_retrieve_reports_missing_index(tmp_path):
    with pytest.raises(IndexError, match="missing or corrupt"):
        retrieve("question", tmp_path / "no-index", embedder=DeterministicEmbedder())


def test_corrupt_snapshot_metadata_is_rejected(tmp_path):
    corpus = tmp_path / "corpus"
    make_corpus(corpus)
    index_dir = tmp_path / "index"
    embedder = DeterministicEmbedder()
    built = build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())
    metadata_file = index_dir / "generations" / built.generation_id / "metadata.json"
    metadata_file.write_text("{}", encoding="utf-8")
    with pytest.raises(IndexError, match="missing or corrupt"):
        retrieve("apples", index_dir, embedder=embedder)


def test_retrieve_rejects_model_and_dimension_mismatch(tmp_path):
    corpus = tmp_path / "corpus"
    make_corpus(corpus)
    index_dir = tmp_path / "index"
    embedder = DeterministicEmbedder()
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())

    class OtherEmbedder(DeterministicEmbedder):
        model_id = "different-model"

    with pytest.raises(IndexError, match="different embedding model"):
        retrieve("apples", index_dir, embedder=OtherEmbedder())

    class WrongDimensions(DeterministicEmbedder):
        model_id = "test-deterministic-embedder-v1"
        dimensions = 64

        def encode(self, texts):
            return np.ones((len(texts), self.dimensions), dtype=np.float32)

    with pytest.raises(IndexError, match="dimension"):
        retrieve("apples", index_dir, embedder=WrongDimensions())

    class MultipleQueryVectors(DeterministicEmbedder):
        def encode(self, texts):
            return np.ones((2, self.dimensions), dtype=np.float32)

    with pytest.raises(EmbeddingError, match="exactly one vector"):
        retrieve("apples", index_dir, embedder=MultipleQueryVectors())
