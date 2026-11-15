import asyncio

import pytest

from hr_mcp.client import ClientError
from tests.fixtures.mcp.harness import build_context, call, connect


@pytest.fixture
def context(tmp_path):
    return build_context(tmp_path)


INVALID = [
    ("search_policy_documents", {"question": " "}),
    ("search_policy_documents", {"question": "policy", "k": 0}),
    ("search_policy_documents", {"question": "policy", "k": True}),
    ("get_policy_section", {"document_id": " ", "section": "2.2"}),
    ("get_policy_section", {"document_id": "HR-004", "section": ""}),
    ("lookup_employee_profile", {}),
    ("lookup_employee_profile", {"employee_id": " "}),
    ("check_pto_balance", {}),
    ("check_pto_balance", {"employee_id": " "}),
    ("check_pto_balance", {"employee_id": 1}),
    ("check_policy_compliance", {"check_id": "unsupported"}),
    ("check_policy_compliance", {
        "check_id": "out_of_state_prior_approval",
        "approval_facts": {"status": "not_approved", "format": "written"},
    }),
    ("draft_hr_email", {"recipient_name": " ", "purpose": "PTO"}),
    ("draft_hr_email", {"recipient_name": "Taylor"}),
    ("draft_hr_email", {"recipient_name": "Taylor", "purpose": " "}),
    ("draft_hr_email", {"recipient_name": "Taylor", "purpose": "PTO", "supporting_details": 1}),
]


def assert_error(result, classification, origin, code):
    assert result.isError is True
    assert result.structuredContent == {
        "error": {"classification": classification, "origin": origin, "code": code}
    }
    assert [item.text for item in result.content] == ["Tool request failed."]


def assert_last_trace(context, name, outcome):
    event = context.events("server")[-1]
    assert event["tool"] == name
    assert event["outcome"] == outcome
    return event


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_six_tool_invalid_and_domain_matrix(context, kind):
    async def exercise():
        async with connect(context, kind) as client:
            for name, arguments in INVALID:
                before = context.calls()
                result = await call(client, name, arguments)
                assert_error(result, "INVALID_ARGUMENT", "input_validation", "invalid_argument")
                assert context.calls() == before
                assert_last_trace(context, name, "INVALID_ARGUMENT")

            domain_cases = [
                ("search_policy_documents", {"question": "synthetic-empty-result"},
                 {"status": "not_found", "evidence": []}),
                ("get_policy_section", {"document_id": "HR-004", "section": "missing"},
                 {"status": "not_found", "evidence": []}),
                ("lookup_employee_profile", {"employee_id": "TEST-UNKNOWN"},
                 {"status": "not_found", "missing": "employee"}),
                ("check_pto_balance", {"employee_id": "TEST-UNKNOWN"},
                 {"status": "not_found", "missing": "employee"}),
                ("check_pto_balance", {"employee_id": "TEST-002"},
                 {"status": "not_found", "missing": "pto"}),
                ("check_policy_compliance", {"check_id": "out_of_state_prior_approval"},
                 {"status": "indeterminate", "conclusion": "indeterminate"}),
            ]
            for name, arguments, expected in domain_cases:
                result = await call(client, name, arguments)
                assert not result.isError
                assert all(result.structuredContent[key] == value for key, value in expected.items())
                if name in {"search_policy_documents", "get_policy_section"}:
                    assert result.structuredContent["generation_id"]
                    assert "evidence_kind" not in result.structuredContent
                if name in {"lookup_employee_profile", "check_pto_balance"}:
                    assert set(result.structuredContent) == {"status", "missing"}
                assert_last_trace(context, name, expected["status"])

            result = await call(
                client, "search_policy_documents", {"question": "synthetic-embedding-failure"}
            )
            assert_error(result, "OPERATIONAL_ERROR", "tool_execution", "embedding_failure")
            assert_last_trace(context, "search_policy_documents", "OPERATIONAL_ERROR")
            result = await call(
                client, "draft_hr_email",
                {"recipient_name": "Taylor", "purpose": "synthetic-handler-failure"},
            )
            assert_error(result, "UNKNOWN_ERROR", "tool_execution", "internal_error")
            assert_last_trace(context, "draft_hr_email", "UNKNOWN_ERROR")
            result = await call(
                client, "draft_hr_email",
                {"recipient_name": "Taylor", "purpose": "synthetic-bad-output"},
            )
            assert_error(result, "UNKNOWN_ERROR", "tool_execution", "internal_error")
            assert_last_trace(context, "draft_hr_email", "UNKNOWN_ERROR")

    asyncio.run(exercise())


@pytest.mark.parametrize("kind", ["provided", "raw"])
def test_operational_and_adapter_failures(context, kind):
    async def exercise():
        async with connect(context, kind, index=context.root / "missing-index") as client:
            for name, arguments in [
                ("search_policy_documents", {"question": "policy"}),
                ("get_policy_section", {"document_id": "HR-004", "section": "2.2"}),
                ("check_policy_compliance", {"check_id": "out_of_state_prior_approval"}),
            ]:
                result = await call(client, name, arguments)
                assert_error(result, "OPERATIONAL_ERROR", "tool_execution", "index_unavailable")
                assert_last_trace(context, name, "OPERATIONAL_ERROR")

        async with connect(context, kind, data_dir=context.root / "missing-data") as client:
            for name in ("lookup_employee_profile", "check_pto_balance"):
                result = await call(client, name, {"employee_id": "TEST-001"})
                assert_error(result, "OPERATIONAL_ERROR", "tool_execution", "data_unavailable")
                assert_last_trace(context, name, "OPERATIONAL_ERROR")

        async with connect(context, kind, mode="adapter-error") as client:
            before = context.calls()
            result = await call(client, "draft_hr_email", {"recipient_name": "Taylor", "purpose": "PTO"})
            assert_error(result, "UNKNOWN_ERROR", "request_adapter", "internal_error")
            assert context.calls() == before
            assert_last_trace(context, "draft_hr_email", "UNKNOWN_ERROR")

    asyncio.run(exercise())


def test_client_does_not_infer_ambiguous_error_origin(context):
    async def exercise():
        async with connect(context, "provided", mode="ambiguous") as client:
            for message in ("INVALID_ARGUMENT", "OPERATIONAL_ERROR", "missing-envelope"):
                result = await call(
                    client, "draft_hr_email", {"recipient_name": "Taylor", "purpose": message}
                )
                assert result.isError
                assert result.structuredContent == {
                    "error": {
                        "classification": "UNCLASSIFIED_ERROR",
                        "origin": None,
                        "code": "unclassified_error",
                    }
                }
                assert "secret" not in str(result.content)
                assert context.events("client")[-1]["classification"] == "UNCLASSIFIED_ERROR"
            assert not context.events("server")

        async with connect(context, "provided", mode="protocol-error") as client:
            with pytest.raises(ClientError) as error:
                await call(client, "draft_hr_email", {"recipient_name": "Taylor", "purpose": "PTO"})
            assert error.value.classification == "UNCLASSIFIED_ERROR"
            assert error.value.origin is None
            assert error.value.protocol_code == -32603
            assert "secret" not in str(error.value)

    asyncio.run(exercise())
