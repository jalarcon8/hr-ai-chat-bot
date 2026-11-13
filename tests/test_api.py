import pytest

from hr_rag import ChunkingConfig, answer_question, build_index
from hr_rag.models import GroundingValidationError
from tests.fixtures.doubles import DeterministicEmbedder, EvidenceGenerator

pytest.importorskip("faiss")


def test_public_python_api_returns_inspectable_citations(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "policy.md").write_text(
        "document_id: HR-100\ntitle: Leave Policy\n\n## Eligibility\n"
        "Employees receive 12 leave days per year.",
        encoding="utf-8",
    )
    embedder = DeterministicEmbedder()
    index_dir = tmp_path / "index"
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())
    result = answer_question(
        "How many leave days?", str(index_dir), embedder=embedder, generator=EvidenceGenerator()
    )
    assert result.status == "answered"
    assert result.claims[0].citation_ids
    citation = result.citations[0]
    assert citation.document_id == "HR-100"
    assert citation.section == "Eligibility"
    assert citation.snippet == "Employees receive 12 leave days per year."


def test_unknown_citation_is_rejected(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "policy.md").write_text("# Policy\nEvidence is available.", encoding="utf-8")
    embedder = DeterministicEmbedder()
    index_dir = tmp_path / "index"
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())

    class BadGenerator:
        def generate(self, question, evidence):
            return {
                "status": "answered",
                "claims": [{"text": "Claim.", "citation_ids": ["unknown"]}],
                "limitations": [],
            }

    with pytest.raises(GroundingValidationError, match="unknown evidence"):
        answer_question("question", str(index_dir), embedder=embedder, generator=BadGenerator())


def test_unsupported_generator_result_and_no_evidence_result(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "policy.md").write_text("# Policy\nA policy paragraph.", encoding="utf-8")
    embedder = DeterministicEmbedder()
    index_dir = tmp_path / "index"
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())
    unsupported = answer_question(
        "unrelated query", str(index_dir), embedder=embedder,
        generator=EvidenceGenerator(status="unsupported"),
    )
    assert unsupported.status == "unsupported"
    assert not unsupported.claims


def test_partial_or_conflicting_requires_limitation(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "policy.md").write_text("# Policy\nA policy paragraph.", encoding="utf-8")
    embedder = DeterministicEmbedder()
    index_dir = tmp_path / "index"
    build_index(index_dir, corpus_dir=corpus, embedder=embedder, chunking_config=ChunkingConfig())

    class MissingLimitation:
        def generate(self, question, evidence):
            return {"status": "partial", "claims": [], "limitations": []}

    with pytest.raises(GroundingValidationError, match="explain their limitations"):
        answer_question("question", str(index_dir), embedder=embedder, generator=MissingLimitation())
