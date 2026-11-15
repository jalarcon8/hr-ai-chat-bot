import copy
import hashlib
import json
import shutil
import socket
import unicodedata
from pathlib import Path

import pytest
from pydantic import ValidationError

from hr_mcp import tools
from hr_mcp.models import ComplianceInput
from hr_rag import ChunkingConfig, build_index
from hr_rag.models import IndexError
from tests.fixtures.doubles import DeterministicEmbedder

FIXTURES = Path(__file__).parent / "fixtures" / "mcp"
APPROVED = {
    "status": "approved",
    "authority": "people_operations",
    "format": "written",
    "approval_timestamp": "2026-01-01T10:00:00Z",
    "travel_start_timestamp": "2026-01-02T10:00:00Z",
}


@pytest.fixture
def context(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(FIXTURES / "policies", corpus)
    baseline = tmp_path / "baseline.json"
    shutil.copyfile(FIXTURES / "baseline.json", baseline)
    pin = json.loads((FIXTURES / "baseline-pin.json").read_text(encoding="utf-8"))
    index = tmp_path / "index"
    build_index(
        index, corpus_dir=corpus, embedder=DeterministicEmbedder(), chunking_config=ChunkingConfig()
    )
    return corpus, index, baseline, pin


def evaluate(context, facts=APPROVED, check_id="out_of_state_prior_approval"):
    corpus, index, baseline, pin = context
    return tools._check_policy_compliance(
        check_id, facts, index_dir=index, corpus_dir=corpus, baseline_path=baseline, pin=pin
    )


def rebuild(context):
    corpus, index, _, _ = context
    return build_index(
        index, corpus_dir=corpus, embedder=DeterministicEmbedder(), chunking_config=ChunkingConfig()
    )


def write_baseline(context, value):
    context[2].write_text(json.dumps(value), encoding="utf-8")


def mutate_snapshot(context, mutate):
    index = context[1]
    pointer_file = index / "active.json"
    pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
    metadata_file = index / "generations" / pointer["generation_id"] / "metadata.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    mutate(metadata)
    raw = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    metadata_file.write_bytes(raw)
    pointer["metadata_sha256"] = hashlib.sha256(raw).hexdigest()
    pointer_file.write_text(json.dumps(pointer), encoding="utf-8")


def assert_indeterminate(result):
    assert result.status == result.conclusion == "indeterminate"
    assert result.limitations
    assert any("unauthenticated" in item.lower() for item in result.limitations)
    assert any("only" in item.lower() for item in result.limitations)


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (APPROVED, "compliant"),
        ({**APPROVED, "no_other_approvals": False}, "compliant"),
        ({"status": "not_approved"}, "noncompliant"),
        ({"status": "not_approved", "no_other_approvals": True}, "noncompliant"),
        ({"status": "not_approved", "authority": "unknown", "no_other_approvals": None},
         "noncompliant"),
        (None, "indeterminate"),
        ({}, "indeterminate"),
        ({"status": "approved"}, "indeterminate"),
        ({**APPROVED, "status": "unknown"}, "indeterminate"),
        ({**APPROVED, "format": "verbal", "no_other_approvals": True}, "noncompliant"),
        ({**APPROVED, "authority": "other", "no_other_approvals": True}, "noncompliant"),
        (
            {**APPROVED, "approval_timestamp": "2026-01-02T10:00:00Z", "no_other_approvals": True},
            "noncompliant",
        ),
        (
            {**APPROVED, "approval_timestamp": "2026-01-02T10:00:00.000001Z",
             "no_other_approvals": True},
            "noncompliant",
        ),
        (
            {**APPROVED, "approval_timestamp": "2026-01-02T09:59:59.999999Z"},
            "compliant",
        ),
        (
            {**APPROVED, "approval_timestamp": "2026-01-02T11:00:00+01:00",
             "no_other_approvals": True},
            "noncompliant",
        ),
        ({"status": "unknown", "format": "verbal", "no_other_approvals": True}, "noncompliant"),
        ({"format": "verbal", "no_other_approvals": True}, "noncompliant"),
        ({"status": "unknown", "authority": "other", "no_other_approvals": True}, "noncompliant"),
        (
            {"status": "unknown", "approval_timestamp": "2026-01-02T10:00:00Z",
             "travel_start_timestamp": "2026-01-02T10:00:00Z", "no_other_approvals": True},
            "noncompliant",
        ),
    ],
)
def test_facts_follow_ordered_rules_and_cite_verified_evidence(context, facts, expected):
    result = evaluate(context, facts)
    assert result.conclusion == expected
    assert result.status == ("indeterminate" if expected == "indeterminate" else "found")
    assert result.evidence
    assert all(item.document_id == "HR-004" for item in result.evidence)
    assert all(item.section == "2.2 Out-of-State Work" for item in result.evidence)
    assert any("unauthenticated" in item.lower() for item in result.limitations)
    assert any("only" in item.lower() for item in result.limitations)
    if expected == "indeterminate":
        assert_indeterminate(result)


@pytest.mark.parametrize(
    "disqualification",
    [
        {"format": "verbal"},
        {"authority": "other"},
        {"approval_timestamp": "2026-01-02T10:00:00Z"},
    ],
)
@pytest.mark.parametrize("other_approvals", [False, None, "omitted"])
@pytest.mark.parametrize("status", ["approved", "unknown"])
def test_disqualified_candidate_does_not_exclude_other_approval(
    context, disqualification, other_approvals, status
):
    facts = {**APPROVED, **disqualification, "status": status}
    if other_approvals != "omitted":
        facts["no_other_approvals"] = other_approvals
    assert_indeterminate(evaluate(context, facts))


@pytest.mark.parametrize(
    "field", ["status", "authority", "format", "approval_timestamp", "travel_start_timestamp"]
)
@pytest.mark.parametrize("value", [None, "omitted"])
def test_missing_fact_is_indeterminate_with_verified_evidence(context, field, value):
    facts = {**APPROVED}
    if value == "omitted":
        del facts[field]
    else:
        facts[field] = None
    result = evaluate(context, facts)
    assert_indeterminate(result)
    assert result.evidence
    assert field in " ".join(result.limitations)


@pytest.mark.parametrize("field", ["status", "authority", "format"])
def test_explicit_unknown_fact_is_indeterminate(context, field):
    facts = {**APPROVED, field: "unknown"}
    result = evaluate(context, facts)
    assert_indeterminate(result)
    assert field in " ".join(result.limitations)


@pytest.mark.parametrize(
    "facts",
    [
        {"status": "not_approved", "authority": "people_operations"},
        {"status": "not_approved", "format": "written"},
        {"status": "not_approved", "approval_timestamp": "2026-01-01T00:00:00Z"},
        {"status": "not_approved", "no_other_approvals": False},
        {"no_other_approvals": 1},
        {"approval_timestamp": "2026-01-01T10:00:00-00:00"},
        {"approval_timestamp": "2026-01-01T10:00:00.1234567Z"},
        {"approval_timestamp": "2026-02-30T10:00:00Z"},
        {"approval_timestamp": "2026-01-01T10:00:60Z"},
        {"approval_timestamp": "2026-01-01T10:00:00+24:00"},
        {"approval_timestamp": "2026-01-01T10:00:00"},
        {"status": "unsupported"},
        {"authority": 42},
        {"format": []},
        {"unexpected": True},
        "approved",
    ],
)
def test_invalid_arguments_are_rejected_before_baseline(context, facts):
    context[2].write_text("invalid", encoding="utf-8")
    with pytest.raises(ValidationError):
        evaluate(context, facts)
    with pytest.raises(ValidationError):
        evaluate(context, None, "unsupported")


def test_old_top_level_approval_status_is_invalid(context):
    context[2].write_text("invalid", encoding="utf-8")
    with pytest.raises(ValidationError):
        ComplianceInput.model_validate(
            {"check_id": "out_of_state_prior_approval", "approval_status": "approved"}
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("baseline_id", "wrong"),
        ("baseline_version", "1"),
        ("check_id", "wrong"),
        ("document_id", "HR-999"),
        ("canonical_sha256", "0" * 64),
        ("normalization_version", "unknown"),
        ("approval_status", "pending"),
        ("approver_id", " "),
        ("approved_at", "not-a-date"),
        ("approval_reference", "https://example.com/review"),
    ],
)
def test_bad_baseline_fields_or_pin_mismatch_fail_closed(context, field, value):
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    baseline["records"][0][field] = value
    write_baseline(context, baseline)
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approval_status", "pending"),
        ("approver_id", ""),
        ("approver_id", "not a reviewer"),
        ("approved_at", "2026-02-30T00:00:00Z"),
        ("approval_reference", "https://github.com/example/repo/pull/1"),
        ("approval_reference", "https://github.com/../repo/pull/1#pullrequestreview-1"),
        ("canonical_sha256", "0" * 63),
        ("normalization_version", "other"),
        ("baseline_version", "1"),
    ],
)
def test_identically_invalid_baseline_and_pin_do_not_establish_approval(context, field, value):
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    baseline["records"][0][field] = value
    context[3]["records"][0][field] = value
    write_baseline(context, baseline)
    assert_indeterminate(evaluate(context))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approver_id", "another-reviewer"),
        ("approved_at", "2026-01-02T00:00:00Z"),
        ("approval_reference", "https://github.com/example/fictional/pull/2#pullrequestreview-2"),
        ("canonical_sha256", "0" * 64),
    ],
)
def test_well_formed_but_pin_mismatched_review_is_indeterminate(context, field, value):
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    baseline["records"][0][field] = value
    write_baseline(context, baseline)
    assert_indeterminate(evaluate(context))


@pytest.mark.parametrize("field", [
    "baseline_id", "baseline_version", "check_id", "document_id", "canonical_sha256",
    "normalization_version", "approval_status", "approver_id", "approved_at", "approval_reference",
])
def test_missing_approval_fields_fail_closed(context, field):
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    del baseline["records"][0][field]
    write_baseline(context, baseline)
    assert_indeterminate(evaluate(context))


def test_v1_missing_duplicate_and_unapproved_baselines_fail_closed(context):
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    for bad in [
        {},
        {"records": baseline["records"][:1]},
        {"records": baseline["records"] + baseline["records"][:1]},
        json.loads(
            (Path(__file__).parent.parent / "data" / "compliance-baselines"
             / "hr-004-section-2.2-v1.json").read_text(encoding="utf-8")
        ),
    ]:
        write_baseline(context, bad)
        assert_indeterminate(evaluate(context))
        assert evaluate(context).evidence == []
    context[2].unlink()
    assert_indeterminate(evaluate(context))


def test_malformed_and_duplicate_field_baselines_fail_closed(context):
    for data in ("not json", '{"records": [], "records": []}'):
        context[2].write_text(data, encoding="utf-8")
        result = evaluate(context)
        assert_indeterminate(result)
        assert result.evidence == []


def test_duplicate_or_missing_pin_records_fail_closed(context):
    records = context[3]["records"]
    context[3]["records"] = [records[0], records[0]]
    assert_indeterminate(evaluate(context))
    context[3]["records"] = []
    assert_indeterminate(evaluate(context))


@pytest.mark.parametrize("filename", ["hr-001.md", "hr-004.md"])
def test_changed_governing_document_fails_closed_even_after_reindex(context, filename):
    path = context[0] / filename
    path.write_text(path.read_text(encoding="utf-8") + "\n# Other\n\nChanged policy.\n", encoding="utf-8")
    assert_indeterminate(evaluate(context))
    rebuild(context)
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


@pytest.mark.parametrize(
    ("filename", "original", "replacement"),
    [
        ("hr-004.md", "approval is required", "approval is never required"),
        ("hr-001.md", "governs prior travel approval", "does not govern prior travel approval"),
    ],
)
def test_edited_governing_provisions_fail_closed(context, filename, original, replacement):
    path = context[0] / filename
    content = path.read_text(encoding="utf-8")
    assert original in content
    path.write_text(content.replace(original, replacement), encoding="utf-8")
    rebuild(context)
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


@pytest.mark.parametrize("newline", ["\r", "\r\n"])
def test_equivalent_reindexed_newlines_preserve_canonical_digest(context, newline):
    path = context[0] / "hr-004.md"
    text = path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    path.write_bytes(text.encode("utf-8"))
    rebuild(context)
    assert evaluate(context).conclusion == "compliant"
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    assert_indeterminate(evaluate(context))
    rebuild(context)
    result = evaluate(context)
    assert result.conclusion == "compliant", result.model_dump()


def test_equivalent_reindexed_unicode_preserves_canonical_digest(context):
    path = context[0] / "hr-004.md"
    composed = path.read_text(encoding="utf-8").replace(
        "# 2.2 Out-of-State Work", "Fictional caf\u00e9.\n\n# 2.2 Out-of-State Work"
    )
    path.write_bytes(composed.encode("utf-8"))
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    for data in (baseline, context[3]):
        record = next(item for item in data["records"] if item["document_id"] == "HR-004")
        record["canonical_sha256"] = hashlib.sha256(composed.encode("utf-8")).hexdigest()
    write_baseline(context, baseline)
    rebuild(context)
    assert evaluate(context).conclusion == "compliant"
    decomposed = unicodedata.normalize("NFD", composed)
    path.write_bytes(decomposed.encode("utf-8"))
    assert_indeterminate(evaluate(context))
    rebuild(context)
    assert evaluate(context).conclusion == "compliant"


def test_reviewed_exact_numeric_section_label_is_supported(context):
    path = context[0] / "hr-004.md"
    text = path.read_bytes().decode("utf-8").replace("2.2 Out-of-State Work", "2.2")
    path.write_bytes(text.encode("utf-8"))
    canonical = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    for data in (baseline, context[3]):
        record = next(item for item in data["records"] if item["document_id"] == "HR-004")
        record["canonical_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    write_baseline(context, baseline)
    rebuild(context)
    result = evaluate(context)
    assert result.conclusion == "compliant"
    assert all(item.section == "2.2" for item in result.evidence)


def test_other_whitespace_changes_do_not_preserve_canonical_digest(context):
    path = context[0] / "hr-004.md"
    text = path.read_bytes().decode("utf-8")
    assert "approval is" in text
    path.write_bytes(text.replace("approval is", "approval  is").encode("utf-8"))
    rebuild(context)
    assert_indeterminate(evaluate(context))


def test_new_subsection_fails_closed_despite_unchanged_original_chunk(context):
    index = context[1]
    original_pointer = json.loads((index / "active.json").read_text(encoding="utf-8"))
    original_metadata = json.loads(
        (index / "generations" / original_pointer["generation_id"] / "metadata.json").read_text(
            encoding="utf-8"
        )
    )
    original = next(
        chunk for chunk in original_metadata["chunks"]
        if chunk["document_id"] == "HR-004" and chunk["section"] == "2.2 Out-of-State Work"
    )
    path = context[0] / "hr-004.md"
    raw = path.read_bytes()
    path.write_bytes(raw + b"\n# 2.2.1 Exception\n\nA conflicting exception.\n")
    assert hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(raw).digest()
    old_canonical = unicodedata.normalize("NFC", raw.decode("utf-8").replace("\r\n", "\n"))
    new_canonical = unicodedata.normalize(
        "NFC", path.read_bytes().decode("utf-8").replace("\r\n", "\n")
    )
    assert hashlib.sha256(old_canonical.encode()).digest() != hashlib.sha256(new_canonical.encode()).digest()
    built = rebuild(context)
    current = json.loads(
        (index / "generations" / built.generation_id / "metadata.json").read_text(encoding="utf-8")
    )
    unchanged = next(
        chunk for chunk in current["chunks"]
        if chunk["document_id"] == "HR-004" and chunk["section"] == "2.2 Out-of-State Work"
    )
    assert unchanged == original
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


def test_unrelated_document_does_not_invalidate_baseline(context):
    unrelated = context[0] / "unrelated.md"
    unrelated.write_text(
        "document_id: HR-999\ntitle: Unrelated\n\n# Other\n\nUnrelated policy.\n", encoding="utf-8"
    )
    rebuild(context)
    assert evaluate(context).conclusion == "compliant"
    unrelated.write_text(
        "document_id: HR-999\ntitle: Unrelated\n\n# Other\n\nChanged unrelated policy.\n",
        encoding="utf-8",
    )
    rebuild(context)
    assert evaluate(context).conclusion == "compliant"


@pytest.mark.parametrize("filename", ["hr-001.md", "hr-004.md"])
def test_missing_source_and_unreviewed_production_are_indeterminate(context, filename):
    corpus, index, _, _ = context
    assert_indeterminate(
        tools.check_policy_compliance(
            "out_of_state_prior_approval", APPROVED, index_dir=index, corpus_dir=corpus
        )
    )
    (corpus / filename).unlink()
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


def test_unreadable_governing_source_is_indeterminate(monkeypatch, context):
    blocked = (context[0] / "hr-004.md").resolve()
    read_bytes = Path.read_bytes

    def deny_source(path):
        if path == blocked:
            raise PermissionError("Synthetic unreadable source.")
        return read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", deny_source)
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


def test_missing_index_remains_an_operational_error(context):
    corpus, _, baseline, pin = context
    with pytest.raises(IndexError):
        tools._check_policy_compliance(
            "out_of_state_prior_approval", APPROVED, index_dir=corpus / "missing",
            corpus_dir=corpus, baseline_path=baseline, pin=pin,
        )


@pytest.mark.parametrize("source_path", ["../outside.md", "/outside.md", "C:\\outside.md"])
def test_unsafe_governing_source_path_is_indeterminate(context, source_path):
    def change(metadata):
        record = next(item for item in metadata["documents"] if item["document_id"] == "HR-004")
        record["source_path"] = source_path

    mutate_snapshot(context, change)
    assert_indeterminate(evaluate(context))
    assert evaluate(context).evidence == []


@pytest.mark.parametrize("field", ["source_path", "content_hash"])
def test_missing_governing_document_metadata_is_indeterminate(context, field):
    def change(metadata):
        record = next(item for item in metadata["documents"] if item["document_id"] == "HR-004")
        del record[field]

    mutate_snapshot(context, change)
    assert_indeterminate(evaluate(context))


def test_missing_governing_document_record_is_indeterminate(context):
    def change(metadata):
        metadata["documents"] = [
            item for item in metadata["documents"] if item["document_id"] != "HR-001"
        ]

    mutate_snapshot(context, change)
    assert_indeterminate(evaluate(context))


@pytest.mark.parametrize("field", ["start", "end"])
def test_missing_indexed_citation_offset_is_indeterminate(context, field):
    def change(metadata):
        chunk = next(
            item for item in metadata["chunks"]
            if item["document_id"] == "HR-004" and item["section"] == "2.2 Out-of-State Work"
        )
        del chunk[field]

    mutate_snapshot(context, change)
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


def test_reversed_citation_offsets_are_indeterminate(context):
    def change(metadata):
        chunk = next(
            item for item in metadata["chunks"]
            if item["document_id"] == "HR-004" and item["section"] == "2.2 Out-of-State Work"
        )
        chunk["start"], chunk["end"] = chunk["end"], chunk["start"]

    mutate_snapshot(context, change)
    assert_indeterminate(evaluate(context))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("start", -1),
        ("start", True),
        ("start", "1"),
        ("end", -1),
        ("end", 999999),
        ("snippet", "incorrect indexed text"),
        ("chunk_id", ""),
    ],
)
def test_invalid_citation_metadata_is_indeterminate(context, field, value):
    def change(metadata):
        chunk = next(
            item for item in metadata["chunks"]
            if item["document_id"] == "HR-004" and item["section"] == "2.2 Out-of-State Work"
        )
        chunk[field] = value

    mutate_snapshot(context, change)
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


def test_invalid_utf8_source_bound_to_snapshot_is_indeterminate(context):
    path = context[0] / "hr-004.md"
    raw = path.read_bytes() + b"\xff"
    path.write_bytes(raw)

    def change(metadata):
        record = next(item for item in metadata["documents"] if item["document_id"] == "HR-004")
        record["content_hash"] = hashlib.sha256(raw).hexdigest()

    mutate_snapshot(context, change)
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


def test_corrupt_snapshot_is_operational_error(context):
    pointer = json.loads((context[1] / "active.json").read_text(encoding="utf-8"))
    (context[1] / "generations" / pointer["generation_id"] / "metadata.json").write_text(
        "{}", encoding="utf-8"
    )
    with pytest.raises(IndexError):
        evaluate(context)


def test_incomplete_indexed_citations_are_not_presented_as_support(context):
    built = build_index(
        context[1],
        corpus_dir=context[0],
        embedder=DeterministicEmbedder(),
        chunking_config=ChunkingConfig(max_tokens=4, overlap_tokens=0),
    )
    metadata_file = context[1] / "generations" / built.generation_id / "metadata.json"
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    candidates = [
        chunk for chunk in metadata["chunks"]
        if chunk["document_id"] == "HR-004" and chunk["section"] == "2.2 Out-of-State Work"
    ]
    assert len(candidates) > 1
    candidates[0]["section"] = "Other"
    raw = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    metadata_file.write_bytes(raw)
    pointer_file = context[1] / "active.json"
    pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
    pointer["metadata_sha256"] = hashlib.sha256(raw).hexdigest()
    pointer_file.write_text(json.dumps(pointer), encoding="utf-8")
    result = evaluate(context)
    assert_indeterminate(result)
    assert result.evidence == []


def test_indeterminate_names_unknown_facts(context):
    result = evaluate(context, {"status": "approved"})
    assert_indeterminate(result)
    explanation = " ".join(result.limitations)
    assert "authority" in explanation
    assert "format" in explanation
    assert "approval_timestamp" in explanation
    assert "travel_start_timestamp" in explanation


def test_synthetic_verification_uses_no_network_or_credentials(monkeypatch, context):
    for name in ("GROQ_API_KEY", "OPENAI_API_KEY", "HF_TOKEN"):
        monkeypatch.delenv(name, raising=False)

    def no_network(*args, **kwargs):
        pytest.fail("Synthetic compliance must not use a network service.")

    monkeypatch.setattr(socket, "socket", no_network)
    assert evaluate(context).conclusion == "compliant"


def test_synthetic_baseline_file_cannot_activate_production(monkeypatch, tmp_path, context):
    baseline_dir = tmp_path / "data" / "compliance-baselines"
    baseline_dir.mkdir(parents=True)
    shutil.copyfile(context[2], baseline_dir / "out-of-state-prior-approval-v2.json")
    monkeypatch.chdir(tmp_path)
    result = tools.check_policy_compliance(
        "out_of_state_prior_approval", APPROVED, index_dir=context[1], corpus_dir=context[0]
    )
    assert_indeterminate(result)
    assert result.evidence == []


def test_unicode_crlf_offsets_match_original_decoded_text(context):
    path = context[0] / "hr-004.md"
    text = path.read_text(encoding="utf-8").replace(
        "# 2.2 Out-of-State Work", "Fictional caf\u0065\u0301 \U0001f600.\n\n# 2.2 Out-of-State Work"
    )
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    canonical = unicodedata.normalize("NFC", text).encode("utf-8")
    baseline = json.loads(context[2].read_text(encoding="utf-8"))
    pin = copy.deepcopy(context[3])
    for data in (baseline, pin):
        for record in data["records"]:
            if record["document_id"] == "HR-004":
                record["canonical_sha256"] = hashlib.sha256(canonical).hexdigest()
    write_baseline(context, baseline)
    context[3].clear()
    context[3].update(pin)
    built = rebuild(context)
    result = evaluate(context)
    assert result.conclusion == "compliant"
    metadata = json.loads(
        (context[1] / "generations" / built.generation_id / "metadata.json").read_text(encoding="utf-8")
    )
    chunk = next(chunk for chunk in metadata["chunks"] if chunk["chunk_id"] == result.evidence[0].chunk_id)
    raw = path.read_bytes()
    decoded = raw.decode("utf-8")
    assert decoded[chunk["start"]:chunk["end"]] == result.evidence[0].snippet
    assert raw[chunk["start"]:chunk["end"]].decode("utf-8", errors="replace") != result.evidence[0].snippet
    normalized = unicodedata.normalize("NFC", decoded.replace("\r\n", "\n").replace("\r", "\n"))
    assert normalized[chunk["start"]:chunk["end"]] != result.evidence[0].snippet
