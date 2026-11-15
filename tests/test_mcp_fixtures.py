import hashlib
import json
import unicodedata
from pathlib import Path

from hr_rag import ChunkingConfig, build_index, ingest_corpus, retrieve
from tests.fixtures.mcp.doubles import DeterministicEmbedder

FIXTURES = Path(__file__).parent / "fixtures" / "mcp"


def canonical_hash(path):
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


def test_synthetic_policy_fixtures_match_separate_test_baseline(tmp_path):
    corpus = FIXTURES / "policies"
    documents = ingest_corpus(corpus)
    records = json.loads((FIXTURES / "baseline.json").read_text(encoding="utf-8"))["records"]
    pin = json.loads((FIXTURES / "baseline-pin.json").read_text(encoding="utf-8"))["records"]
    assert records == pin
    hashes = {doc.document_id: canonical_hash(corpus / doc.source_path) for doc in documents}
    assert hashes == {record["document_id"]: record["canonical_sha256"] for record in records}
    assert all(record["approver_id"] == "synthetic-test-reviewer" for record in records)

    embedder = DeterministicEmbedder()
    result = build_index(
        tmp_path / "index",
        corpus_dir=corpus,
        embedder=embedder,
        chunking_config=ChunkingConfig(),
    )
    evidence = retrieve("travel approval", tmp_path / "index", embedder=embedder)
    assert result.document_count == 2
    assert evidence.generation_id == result.generation_id
    assert evidence.evidence
    assert canonical_hash(FIXTURES / "variants" / "changed-hr-004.md") != hashes["HR-004"]
    missing = ingest_corpus(FIXTURES / "variants" / "missing-governing")
    assert {doc.document_id for doc in missing} == {"HR-004"}


def test_synthetic_fixture_includes_employee_without_pto():
    employees = json.loads((FIXTURES / "employees.json").read_text(encoding="utf-8"))
    pto = json.loads((FIXTURES / "pto.json").read_text(encoding="utf-8"))
    assert {record["employee_id"] for record in employees} - {
        record["employee_id"] for record in pto
    } == {"TEST-002"}
