import pytest

from hr_rag import ChunkingConfig, answer_question, build_index
from hr_rag.models import DocumentValidationError, EmbeddingError, GenerationError, InvalidInputError
from tests.fixtures.doubles import DeterministicEmbedder


pytest.importorskip("faiss")


def test_blank_question_and_bad_chunk_configuration_raise(tmp_path):
    with pytest.raises(InvalidInputError):
        answer_question(" ", str(tmp_path), embedder=DeterministicEmbedder())
    with pytest.raises(InvalidInputError):
        ChunkingConfig(max_tokens=5, overlap_tokens=5)


def test_empty_corpus_fails_explicitly(tmp_path):
    corpus = tmp_path / "empty-corpus"
    corpus.mkdir()
    with pytest.raises(DocumentValidationError, match="no Markdown or TXT"):
        build_index(
            tmp_path / "index",
            corpus_dir=corpus,
            embedder=DeterministicEmbedder(),
            chunking_config=ChunkingConfig(),
        )


def test_embedding_failure_does_not_activate_partial_index(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "source.txt").write_text("A valid policy paragraph.", encoding="utf-8")
    index_dir = tmp_path / "index"
    good = DeterministicEmbedder()
    first = build_index(index_dir, corpus_dir=corpus, embedder=good, chunking_config=ChunkingConfig())

    class BrokenEmbedder(DeterministicEmbedder):
        def encode(self, texts):
            raise RuntimeError("internal provider details")

    with pytest.raises(EmbeddingError):
        build_index(index_dir, corpus_dir=corpus, embedder=BrokenEmbedder(), chunking_config=ChunkingConfig())
    active = (index_dir / "active.json").read_text(encoding="utf-8")
    assert first.generation_id in active


def test_provider_failure_is_typed_and_does_not_return_unsupported(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "policy.md").write_text("# Policy\nA policy paragraph.", encoding="utf-8")
    embedder = DeterministicEmbedder()
    index_dir = tmp_path / "index"
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())

    class BrokenGenerator:
        def generate(self, question, evidence):
            raise RuntimeError("secret details should not leak")

    with pytest.raises(GenerationError, match="Answer generation failed"):
        answer_question("question", str(index_dir), embedder=embedder, generator=BrokenGenerator())
