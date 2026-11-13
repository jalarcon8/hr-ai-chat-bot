from pathlib import Path

from hr_rag.config import ChunkingConfig
from hr_rag.documents import chunk_documents, ingest_corpus
from tests.fixtures.doubles import DeterministicEmbedder


def test_corpus_order_and_chunks_are_reproducible():
    root = Path(__file__).resolve().parents[1] / "corpus"
    first = ingest_corpus(root)
    second = ingest_corpus(root)
    assert [item.source_path for item in first] == [item.source_path for item in second]
    settings = ChunkingConfig()
    tokenizer = DeterministicEmbedder()
    first_chunks = chunk_documents(first, settings, tokenizer)
    second_chunks = chunk_documents(second, settings, tokenizer)
    assert first_chunks == second_chunks
