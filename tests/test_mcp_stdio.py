import asyncio
import hashlib
import json
import unicodedata

import pytest

from tests.fixtures.mcp.harness import build_context, call, connect, rebuild
from tests.test_mcp_errors import assert_error

APPROVED = {
    "status": "approved",
    "authority": "people_operations",
    "format": "written",
    "approval_timestamp": "2026-01-01T10:00:00Z",
    "travel_start_timestamp": "2026-01-02T10:00:00Z",
}


@pytest.fixture
def context(tmp_path):
    return build_context(tmp_path)


def snapshot(context):
    pointer_path = context.index / "active.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    metadata_path = context.index / "generations" / pointer["generation_id"] / "metadata.json"
    return pointer_path, pointer, metadata_path, json.loads(metadata_path.read_text(encoding="utf-8"))


def update_metadata(context, mutate):
    pointer_path, pointer, metadata_path, metadata = snapshot(context)
    mutate(metadata)
    raw = json.dumps(metadata, ensure_ascii=False).encode("utf-8")
    metadata_path.write_bytes(raw)
    pointer["metadata_sha256"] = hashlib.sha256(raw).hexdigest()
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")


def assert_citations(context, result):
    _, _, _, metadata = snapshot(context)
    chunks = {chunk["chunk_id"]: chunk for chunk in metadata["chunks"]}
    source = (context.corpus / "hr-004.md").read_bytes().decode("utf-8")
    assert result["evidence"]
    for evidence in result["evidence"]:
        chunk = chunks[evidence["chunk_id"]]
        assert evidence["document_id"] == "HR-004"
        assert evidence["title"] == chunk["title"]
        assert evidence["section"] == "2.2 Out-of-State Work"
        assert evidence["snippet"] == chunk["snippet"] == source[chunk["start"]:chunk["end"]]
        assert evidence["generation_id"] == metadata["generation_id"]
        assert "score" not in evidence


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_six_real_tools_and_source_metadata(context, kind):
    async def exercise():
        async with connect(context, kind) as client:
            tools = await client.discover() if kind == "provided" else (await client.list_tools()).tools
            assert {tool.name for tool in tools} == {
                "search_policy_documents", "get_policy_section", "lookup_employee_profile",
                "check_pto_balance", "check_policy_compliance", "draft_hr_email",
            }
            cases = [
                ("search_policy_documents", {"question": "travel approval"}),
                ("get_policy_section", {"document_id": "HR-004", "section": "2.2 Out-of-State Work"}),
                ("lookup_employee_profile", {"employee_id": "TEST-001"}),
                ("check_pto_balance", {"employee_id": "TEST-001"}),
                ("check_policy_compliance", {
                    "check_id": "out_of_state_prior_approval", "approval_facts": APPROVED,
                }),
                ("draft_hr_email", {"recipient_name": "Taylor", "purpose": "PTO request"}),
            ]
            for name, arguments in cases:
                result = await call(client, name, arguments)
                assert not result.isError
                body = result.structuredContent
                assert body["status"] == "found"
                if name == "search_policy_documents":
                    assert body["evidence_kind"] == "candidate"
                    assert all(
                        item["document_id"] and item["title"] and item["snippet"]
                        and item["chunk_id"] and item["generation_id"] == body["generation_id"]
                        for item in body["evidence"]
                    )
                elif name in {"get_policy_section", "check_policy_compliance"}:
                    assert_citations(context, body)
                elif name == "lookup_employee_profile":
                    assert body["employee"]["name"] == "Taylor Fixture"
                elif name == "check_pto_balance":
                    assert body["pto"]["employee_id"] == "TEST-001"
                else:
                    assert body["draft"]["subject"] == "PTO request"

            employee = await call(client, "lookup_employee_profile", {"employee_id": "TEST-UNKNOWN"})
            assert employee.structuredContent == {"status": "not_found", "missing": "employee"}
            pto = await call(client, "check_pto_balance", {"employee_id": "TEST-002"})
            assert pto.structuredContent == {"status": "not_found", "missing": "pto"}
            section = await call(
                client, "get_policy_section", {"document_id": "HR-004", "section": "Missing"}
            )
            assert section.structuredContent["status"] == "not_found"
            assert section.structuredContent["evidence"] == []

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_compliance_outcomes_and_citations_over_stdio(context, kind):
    cases = [
        (APPROVED, "compliant"),
        ({**APPROVED, "no_other_approvals": False}, "compliant"),
        ({"status": "not_approved"}, "noncompliant"),
        ({"status": "not_approved", "no_other_approvals": True}, "noncompliant"),
        (None, "indeterminate"),
        ({}, "indeterminate"),
        ({"status": "approved"}, "indeterminate"),
        ({**APPROVED, "status": "unknown"}, "indeterminate"),
        ({**APPROVED, "approval_timestamp": "2026-01-02T11:00:00+01:00",
          "no_other_approvals": True}, "noncompliant"),
        ({**APPROVED, "approval_timestamp": "2026-01-02T10:00:00.000001Z",
          "no_other_approvals": True}, "noncompliant"),
        ({**APPROVED, "approval_timestamp": "2026-01-02T09:59:59.999999Z"}, "compliant"),
        ({**APPROVED, "approval_timestamp": "2026-01-01T11:00:00+01:00"}, "compliant"),
    ]
    for field in ("status", "authority", "format", "approval_timestamp", "travel_start_timestamp"):
        cases.append(({**APPROVED, field: None}, "indeterminate"))
        cases.append(({key: value for key, value in APPROVED.items() if key != field}, "indeterminate"))
    for field in ("status", "authority", "format"):
        cases.append(({**APPROVED, field: "unknown"}, "indeterminate"))
    for disqualification in (
        {"format": "verbal"},
        {"authority": "other"},
        {"approval_timestamp": "2026-01-02T10:00:00Z"},
    ):
        for status in ("approved", "unknown", None):
            facts = {**APPROVED, **disqualification, "no_other_approvals": True}
            if status is None:
                del facts["status"]
            else:
                facts["status"] = status
            cases.append((facts, "noncompliant"))
            for other in (False, None):
                cases.append(({**facts, "no_other_approvals": other}, "indeterminate"))
            cases.append(({key: value for key, value in facts.items() if key != "no_other_approvals"},
                          "indeterminate"))

    async def exercise():
        async with connect(context, kind) as client:
            for facts, conclusion in cases:
                result = await call(
                    client, "check_policy_compliance",
                    {"check_id": "out_of_state_prior_approval", "approval_facts": facts},
                )
                assert not result.isError
                body = result.structuredContent
                assert body["status"] == ("indeterminate" if conclusion == "indeterminate" else "found")
                assert body["conclusion"] == conclusion
                assert body["check_id"] == "out_of_state_prior_approval"
                assert body["limitations"]
                assert "unauthenticated" in " ".join(body["limitations"])
                assert "only" in " ".join(body["limitations"])
                if conclusion == "indeterminate":
                    assert any(
                        "missing" in item.lower() or "unknown" in item.lower()
                        for item in body["limitations"]
                    )
                assert_citations(context, body)

            for arguments in [
                {"check_id": "out_of_state_prior_approval", "approval_status": "approved"},
                {"check_id": "out_of_state_prior_approval",
                 "approval_facts": {"status": "not_approved", "format": "written"}},
                {"check_id": "out_of_state_prior_approval",
                 "approval_facts": {"approval_timestamp": "2026-01-01T00:00:00-00:00"}},
                {"check_id": "out_of_state_prior_approval",
                 "approval_facts": {"approval_timestamp": "2026-01-01T00:00:00.1234567Z"}},
                {"check_id": "unsupported"},
            ]:
                before = context.calls()
                result = await call(client, "check_policy_compliance", arguments)
                assert_error(result, "INVALID_ARGUMENT", "input_validation", "invalid_argument")
                assert context.calls() == before

            context.baseline.write_text("invalid", encoding="utf-8")
            result = await call(
                client, "check_policy_compliance",
                {"check_id": "out_of_state_prior_approval", "approval_facts": {"status": "not_approved"}},
            )
            assert not result.isError
            assert result.structuredContent["conclusion"] == "indeterminate"
            assert result.structuredContent["evidence"] == []
            assert "baseline" in " ".join(result.structuredContent["limitations"]).lower()

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_added_subsection_invalidates_unchanged_citation(context, kind):
    _, _, _, original_metadata = snapshot(context)
    original = next(
        chunk for chunk in original_metadata["chunks"]
        if chunk["document_id"] == "HR-004" and chunk["section"] == "2.2 Out-of-State Work"
    )
    path = context.corpus / "hr-004.md"
    before = path.read_bytes()
    path.write_bytes(before + b"\n# 2.2.1 Exception\n\nA conflicting exception.\n")
    assert hashlib.sha256(path.read_bytes()).digest() != hashlib.sha256(before).digest()
    rebuild(context)
    _, _, _, metadata = snapshot(context)
    assert original in metadata["chunks"]

    async def exercise():
        async with connect(context, kind) as client:
            result = await call(
                client, "check_policy_compliance",
                {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVED},
            )
            assert not result.isError
            assert result.structuredContent["conclusion"] == "indeterminate"
            assert result.structuredContent["evidence"] == []
            assert "verified" in " ".join(result.structuredContent["limitations"]).lower()

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["provided", "raw"])
@pytest.mark.parametrize("filename", ["hr-001.md", "hr-004.md"])
def test_changed_governing_document_is_indeterminate(context, kind, filename):
    path = context.corpus / filename
    with path.open("a", encoding="utf-8") as policy:
        policy.write("\n# Fictional amendment\nA revised governing provision.\n")
    rebuild(context)

    async def exercise():
        async with connect(context, kind) as client:
            result = await call(
                client, "check_policy_compliance",
                {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVED},
            )
            assert not result.isError
            assert result.structuredContent["conclusion"] == "indeterminate"
            assert result.structuredContent["evidence"] == []
            assert "verified" in " ".join(result.structuredContent["limitations"]).lower()

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_unrelated_document_does_not_invalidate_baseline(context, kind):
    path = context.corpus / "unrelated.md"
    path.write_text(
        "document_id: HR-999\ntitle: Synthetic unrelated policy\n\n# Other\n\nChanged text.\n",
        encoding="utf-8",
    )
    rebuild(context)

    async def exercise():
        async with connect(context, kind) as client:
            result = await call(
                client, "check_policy_compliance",
                {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVED},
            )
            assert not result.isError
            assert result.structuredContent["conclusion"] == "compliant"
            assert_citations(context, result.structuredContent)

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_corrupt_index_is_an_operational_error(context, kind):
    _, _, metadata_path, _ = snapshot(context)
    metadata_path.write_text("{}", encoding="utf-8")

    async def exercise():
        async with connect(context, kind) as client:
            result = await call(
                client, "check_policy_compliance",
                {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVED},
            )
            assert_error(result, "OPERATIONAL_ERROR", "tool_execution", "index_unavailable")

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_unicode_crlf_and_invalid_indexed_citations_over_stdio(context, kind):
    path = context.corpus / "hr-004.md"
    text = path.read_text(encoding="utf-8").replace(
        "# 2.2 Out-of-State Work", "Fictional cafe\u0301 \U0001f600.\n\n# 2.2 Out-of-State Work"
    )
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    digest = hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()
    for file in (context.baseline, context.pin):
        baseline = json.loads(file.read_text(encoding="utf-8"))
        record = next(item for item in baseline["records"] if item["document_id"] == "HR-004")
        record["canonical_sha256"] = digest
        file.write_text(json.dumps(baseline), encoding="utf-8")
    rebuild(context)

    async def exercise():
        async with connect(context, kind) as client:
            arguments = {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVED}
            result = await call(client, "check_policy_compliance", arguments)
            assert result.structuredContent["conclusion"] == "compliant"
            assert_citations(context, result.structuredContent)
            _, _, _, metadata = snapshot(context)
            citation = result.structuredContent["evidence"][0]
            chunk = next(item for item in metadata["chunks"] if item["chunk_id"] == citation["chunk_id"])
            assert path.read_bytes()[chunk["start"]:chunk["end"]].decode(
                "utf-8", errors="replace"
            ) != citation["snippet"]

            for field, value in [("start", -1), ("snippet", "unreconstructable indexed text")]:
                rebuild(context)

                def mutate(data, field=field, value=value):
                    target = next(item for item in data["chunks"] if item["chunk_id"] == citation["chunk_id"])
                    target[field] = value

                update_metadata(context, mutate)
                result = await call(client, "check_policy_compliance", arguments)
                assert not result.isError
                assert result.structuredContent["conclusion"] == "indeterminate"
                assert result.structuredContent["evidence"] == []
                assert "verified" in " ".join(result.structuredContent["limitations"]).lower()

    asyncio.run(exercise())
