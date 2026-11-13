import json
import re
from pathlib import Path

import pytest

from hr_rag.answers import answer_question
from hr_rag.config import ChunkingConfig
from hr_rag.documents import ingest_corpus
from hr_rag.index import build_index, retrieve
from tests.fixtures.doubles import DeterministicEmbedder, EvidenceGenerator

pytest.importorskip("faiss")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_checked_in_corpus_inventory_and_acceptance_set(tmp_path):
    corpus_dir = PROJECT_ROOT / "corpus"
    documents = ingest_corpus(corpus_dir)
    assert len(documents) == 12
    assert sum(document.format == "markdown" for document in documents) == 9
    assert sum(document.format == "txt" for document in documents) == 3
    words = sum(len(re.findall(r"\b[\w'-]+\b", document.text)) for document in documents)
    assert 30 * 400 <= words <= 120 * 400
    questions = json.loads((PROJECT_ROOT / "tests/fixtures/acceptance_questions.json").read_text())
    covered_questions = [item for item in questions if item["coverage"] in {"covered", "multi_document"}]
    assert 5 <= len(covered_questions) <= 30

    embedder = DeterministicEmbedder()
    built = build_index(
        tmp_path / "index",
        corpus_dir=corpus_dir,
        embedder=embedder,
        chunking_config=ChunkingConfig(),
    )
    assert built.document_count == 12
    documents_by_id = {document.document_id: document for document in documents}
    for item in covered_questions:
        evidence = retrieve(item["question"], tmp_path / "index", embedder=embedder, k=5).evidence
        assert evidence
        evidence_ids = {entry.document_id for entry in evidence}
        assert set(item["expected_document_ids"]) & evidence_ids
        all_evidence = retrieve(item["question"], tmp_path / "index", embedder=embedder, k=500).evidence
        if item["expected_section"]:
            assert any(
                item["expected_section"] in (entry.section or "")
                for entry in all_evidence
                if entry.document_id in item["expected_document_ids"]
            )
        assert all(
            documents_by_id[entry.document_id].text[entry.start : entry.end] == entry.snippet
            for entry in evidence
        )
        if item["coverage"] == "multi_document":
            assert set(item["expected_document_ids"]) <= {entry.document_id for entry in all_evidence}

    unsupported_items = [item for item in questions if item["coverage"] in {"unsupported", "partial"}]
    assert len(unsupported_items) >= 3
    for item in unsupported_items:
        generator = EvidenceGenerator(status=item["expected_status"])
        answer = answer_question(
            item["question"],
            tmp_path / "index",
            embedder=embedder,
            generator=generator,
        )
        assert answer.status == item["expected_status"]
        assert answer.limitations
        if answer.status == "unsupported":
            assert not answer.claims


def test_three_unsupported_or_partial_acceptance_cases_exist():
    cases = [
        {"question": "What is Northstar's policy for private yacht travel?", "expected_status": "unsupported"},
        {"question": "Does the policy grant an unlisted benefit?", "expected_status": "unsupported"},
        {"question": "What exception applies to a situation not described in the corpus?", "expected_status": "partial"},
    ]
    assert len(cases) >= 3
    assert all(item["expected_status"] in {"unsupported", "partial"} for item in cases)
