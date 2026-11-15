import asyncio
import json
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from anyio import BrokenResourceError

from hr_mcp.client import ClientError, MCPClient
from hr_rag import ChunkingConfig, build_index
from tests.fixtures.mcp.doubles import DeterministicEmbedder

FIXTURES = Path(__file__).parent / "fixtures" / "mcp"
APPROVED = {
    "status": "approved",
    "authority": "people_operations",
    "format": "written",
    "approval_timestamp": "2026-01-01T10:00:00Z",
    "travel_start_timestamp": "2026-01-02T10:00:00Z",
}
SCHEMAS = {
    "search_policy_documents": ({"question"}, {"question", "k"}),
    "get_policy_section": ({"document_id", "section"}, {"document_id", "section"}),
    "lookup_employee_profile": ({"employee_id"}, {"employee_id"}),
    "check_pto_balance": ({"employee_id"}, {"employee_id"}),
    "check_policy_compliance": ({"check_id"}, {"check_id", "approval_facts"}),
    "draft_hr_email": ({"recipient_name", "purpose"}, {"recipient_name", "purpose", "supporting_details"}),
}


@pytest.fixture(autouse=True)
def isolate_traces(tmp_path, monkeypatch):
    monkeypatch.setenv("HR_MCP_TRACE_PATH", str(tmp_path / "traces.jsonl"))


@pytest.fixture
def snapshot(tmp_path):
    corpus = tmp_path / "corpus"
    shutil.copytree(FIXTURES / "policies", corpus)
    index = tmp_path / "index"
    build_index(
        index, corpus_dir=corpus, embedder=DeterministicEmbedder(), chunking_config=ChunkingConfig()
    )
    return corpus, index


def test_six_real_handlers_over_stdio(snapshot):
    corpus, index = snapshot

    async def exercise():
        async with MCPClient(
            command=sys.executable,
            args=["-m", "tests.fixtures.mcp.integration_server", str(corpus), str(index)],
        ) as client:
            discovered = {tool.name: tool for tool in await client.discover()}
            assert set(discovered) == set(SCHEMAS)
            for name, (required, properties) in SCHEMAS.items():
                tool = discovered[name]
                assert tool.description
                assert set(tool.inputSchema["required"]) == required
                assert set(tool.inputSchema["properties"]) == properties
                assert tool.inputSchema["additionalProperties"] is False
                assert tool.outputSchema.get("anyOf") or tool.outputSchema.get("properties")
            assert discovered["search_policy_documents"].inputSchema["properties"]["k"]["default"] == 5
            assert discovered["search_policy_documents"].inputSchema["properties"]["k"]["exclusiveMinimum"] == 0
            assert discovered["check_policy_compliance"].inputSchema["properties"]["check_id"]["const"] == "out_of_state_prior_approval"
            assert discovered["draft_hr_email"].inputSchema["properties"]["supporting_details"]["default"] == ""
            employee_schema = discovered["lookup_employee_profile"].outputSchema
            assert employee_schema["$defs"]["RecordNotFound"]["properties"]["missing"]["enum"] == [
                "employee"
            ]

            async def call(name, arguments):
                result = await client.call(name, arguments)
                assert not result.isError
                assert isinstance(result.structuredContent, dict)
                return result.structuredContent

            search = await call("search_policy_documents", {"question": "travel approval", "k": 2})
            assert search["status"] == "found"
            assert search["evidence_kind"] == "candidate"
            assert len(search["evidence"]) == 2
            for item in search["evidence"]:
                assert item["document_id"] and item["title"] and item["snippet"] and item["chunk_id"]
                assert item["generation_id"] == search["generation_id"]
                assert isinstance(item["score"], float)

            section = await call(
                "get_policy_section",
                {"document_id": "HR-004", "section": "2.2 Out-of-State Work"},
            )
            assert section["status"] == "found"
            assert all(item["section"] == "2.2 Out-of-State Work" for item in section["evidence"])
            assert section["generation_id"] == search["generation_id"]

            employee = await call("lookup_employee_profile", {"employee_id": "TEST-001"})
            assert employee["status"] == "found"
            assert employee["employee"]["name"] == "Taylor Fixture"
            pto = await call("check_pto_balance", {"employee_id": "TEST-001"})
            assert pto["status"] == "found"
            assert pto["pto"]["employee_id"] == "TEST-001"

            for facts, conclusion in [(APPROVED, "compliant"), ({"status": "not_approved"}, "noncompliant")]:
                result = await call(
                    "check_policy_compliance",
                    {"check_id": "out_of_state_prior_approval", "approval_facts": facts},
                )
                assert result["status"] == "found"
                assert result["conclusion"] == conclusion
                assert result["evidence"] and result["limitations"]
                assert result["evidence"][0]["document_id"] == "HR-004"

            draft = await call("draft_hr_email", {"recipient_name": "Taylor", "purpose": "PTO request"})
            assert draft["status"] == "found"
            assert draft["draft"]["subject"] == "PTO request"
            assert "Hello Taylor" in draft["draft"]["body"]

            missing = await call("check_pto_balance", {"employee_id": "TEST-002"})
            assert missing == {"status": "not_found", "missing": "pto"}

    asyncio.run(exercise())


def test_synthetic_compliance_rejects_changed_governing_source(snapshot):
    corpus, index = snapshot
    with (corpus / "hr-004.md").open("a", encoding="utf-8") as policy:
        policy.write("\n# Fictional amendment\nPolicy changed after indexing.\n")

    async def exercise():
        async with MCPClient(
            command=sys.executable,
            args=["-m", "tests.fixtures.mcp.integration_server", str(corpus), str(index)],
        ) as client:
            result = await client.call(
                "check_policy_compliance",
                {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVED},
            )
            assert not result.isError
            assert result.structuredContent["conclusion"] == "indeterminate"
            assert result.structuredContent["evidence"] == []

    asyncio.run(exercise())


def test_default_server_uses_configured_snapshot_and_fails_closed(snapshot, monkeypatch):
    corpus, index = snapshot
    monkeypatch.setenv("HR_RAG_CORPUS_DIR", str(corpus))
    monkeypatch.setenv("HR_RAG_INDEX_DIR", str(index))

    async def exercise():
        async with MCPClient() as client:
            section = await client.call(
                "get_policy_section",
                {"document_id": "HR-004", "section": "2.2 Out-of-State Work"},
            )
            assert not section.isError
            assert section.structuredContent["status"] == "found"
            employee = await client.call("lookup_employee_profile", {"employee_id": "SYN-001"})
            assert not employee.isError
            assert employee.structuredContent["employee"]["name"] == "Alex Example"
            result = await client.call(
                "check_policy_compliance",
                {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVED},
            )
            assert not result.isError
            assert result.structuredContent["conclusion"] == "indeterminate"
            assert result.structuredContent["evidence"] == []

    asyncio.run(exercise())


def test_missing_index_surfaces_tool_error(snapshot, monkeypatch, tmp_path):
    corpus, _ = snapshot
    monkeypatch.setenv("HR_RAG_CORPUS_DIR", str(corpus))
    monkeypatch.setenv("HR_RAG_INDEX_DIR", str(tmp_path / "missing"))

    async def exercise():
        async with MCPClient() as client:
            result = await client.call(
                "get_policy_section", {"document_id": "HR-004", "section": "2.2 Out-of-State Work"}
            )
            assert result.isError
            assert result.structuredContent["error"]["code"] == "index_unavailable"

    asyncio.run(exercise())


def test_client_cli_discovery_and_synthetic_example():
    root = Path(__file__).parent.parent
    for arguments in (["--discover"], ["--example", "lookup_employee_profile"]):
        process = subprocess.run(
            [sys.executable, "-m", "hr_mcp.client", *arguments],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        output = json.loads(process.stdout)
        if arguments == ["--discover"]:
            assert {tool["name"] for tool in output} == set(SCHEMAS)
        else:
            assert output["structuredContent"]["employee"]["employee_id"] == "SYN-001"


def test_client_allows_longer_tool_execution_than_connection_timeout(snapshot):
    corpus, index = snapshot

    async def exercise():
        async with MCPClient(
            command=sys.executable,
            args=[
                "-m", "tests.fixtures.mcp.integration_server",
                str(corpus), str(index), "slow-search",
            ],
            call_timeout=timedelta(seconds=10),
        ) as client:
            result = await client.call("search_policy_documents", {"question": "travel approval"})
            assert not result.isError
            assert result.structuredContent["evidence_kind"] == "candidate"

    asyncio.run(exercise())


@pytest.mark.parametrize("mode", ["slow-search", "blocking-search"])
def test_tool_timeout_surfaces_client_error_after_context_cleanup(snapshot, mode):
    corpus, index = snapshot

    async def exercise():
        with pytest.raises(ClientError) as error:
            async with MCPClient(
                command=sys.executable,
                args=[
                    "-m", "tests.fixtures.mcp.integration_server",
                    str(corpus), str(index), mode,
                ],
                call_timeout=timedelta(milliseconds=100),
            ) as client:
                await client.call("search_policy_documents", {"question": "policy"})
        assert error.value.classification == "UNCLASSIFIED_ERROR"
        assert error.value.origin is None

    asyncio.run(exercise())


def test_cleanup_does_not_hide_unexpected_errors(monkeypatch):
    async def exercise():
        client = MCPClient()

        async def fail_cleanup():
            raise ExceptionGroup("cleanup", [BrokenResourceError(), ValueError("unexpected cleanup")])

        monkeypatch.setattr(client._stack, "aclose", fail_cleanup)
        with pytest.raises(ExceptionGroup) as error:
            await client.__aexit__(ClientError, ClientError("unclassified_error"), None)
        assert isinstance(error.value.exceptions[0], ValueError)

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("name", "arguments"),
    [
        ("check_policy_compliance", {"check_id": "out_of_state_prior_approval", "unexpected": True}),
        (
            "check_policy_compliance",
            {"check_id": "out_of_state_prior_approval", "approval_facts": '{"status":"approved"}'},
        ),
        ("search_policy_documents", {"question": "policy", "k": True}),
        ("search_policy_documents", {"question": "policy", "k": 0}),
    ],
)
def test_mcp_rejects_invalid_raw_arguments(snapshot, name, arguments):
    corpus, index = snapshot

    async def exercise():
        async with MCPClient(
            command=sys.executable,
            args=["-m", "tests.fixtures.mcp.integration_server", str(corpus), str(index)],
        ) as client:
            result = await client.call(name, arguments)
            assert result.isError

    asyncio.run(exercise())
