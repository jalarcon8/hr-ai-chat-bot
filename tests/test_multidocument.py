import pytest

from hr_rag import ChunkingConfig, answer_question, build_index
from tests.fixtures.doubles import DeterministicEmbedder, EvidenceGenerator

pytest.importorskip("faiss")


def test_multi_document_answer_cites_each_retrieved_policy(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "pto.md").write_text(
        "document_id: HR-002\ntitle: PTO\n\n# Request\nSubmit PTO requests in the People Portal.",
        encoding="utf-8",
    )
    (corpus / "holiday.txt").write_text(
        "document_id: HR-003\ntitle: Holidays\n\n1.1 Holiday pay\n"
        "Observed company holidays are not charged as PTO.",
        encoding="utf-8",
    )
    embedder = DeterministicEmbedder()
    index_dir = tmp_path / "index"
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())
    result = answer_question(
        "How do PTO requests interact with company holidays?",
        str(index_dir),
        embedder=embedder,
        generator=EvidenceGenerator(),
        k=5,
    )
    cited_ids = {citation.document_id for citation in result.citations}
    assert {"HR-002", "HR-003"} <= cited_ids


def test_missing_required_policy_is_reported_as_partial(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "pto.md").write_text(
        "document_id: HR-002\ntitle: PTO\n\n# Request\nSubmit PTO requests in the People Portal.",
        encoding="utf-8",
    )
    embedder = DeterministicEmbedder()
    index_dir = tmp_path / "index"
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())

    class PartialGenerator:
        def generate(self, question, evidence):
            return {
                "status": "partial",
                "claims": [{
                    "text": "PTO requests go through the People Portal.",
                    "citation_ids": [evidence[0].chunk_id],
                    "kind": "policy_fact",
                }],
                "limitations": ["The corpus does not include the relevant holiday policy."],
            }

    result = answer_question(
        "How do PTO requests interact with company holidays?",
        index_dir,
        embedder=embedder,
        generator=PartialGenerator(),
    )
    assert result.status == "partial"
    assert result.claims
    assert result.limitations
    assert {citation.document_id for citation in result.citations} == {"HR-002"}
