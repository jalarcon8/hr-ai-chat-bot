import json
import sys
from types import SimpleNamespace

import pytest

import evaluation.run_evaluation as evaluation
from evaluation.run_evaluation import (
    REQUIRED_CATEGORIES,
    classify_failure,
    load_cases,
    percentile_nearest_rank,
    run_cases,
    validate_cases,
)
from hr_agent.errors import AgentRuntimeError
from hr_agent.types import AgentResponse, Citation, ToolInvocationRecord


def _valid_cases():
    cases = []
    categories = sorted(REQUIRED_CATEGORIES)
    for index in range(20):
        cases.append(
            {
                "case_id": f"EVAL-{index:03d}",
                "category": categories[index % len(categories)],
                "request": f"Synthetic request {index}.",
                "context": None,
                "gold_answer_or_rubric": "Use only supported evidence.",
                "expected_source_ids": [],
                "required_tools": [],
                "forbidden_tools": [],
                "expected_status": ["answered"],
                "safety_assertions": ["Do not change records."],
                "latency_sample": index < 10,
            }
        )
    return cases


def test_cases_have_required_count_categories_and_fixed_latency_subset():
    cases = load_cases()

    assert len(cases) == 20
    assert {case["category"] for case in cases} == REQUIRED_CATEGORIES
    assert sum(case["latency_sample"] for case in cases) == 10
    assert any(case["context"] == {"employee_id": "SYN-001"} for case in cases)


def test_case_validation_rejects_missing_category_and_wrong_sample_count():
    cases = _valid_cases()
    for case in cases:
        if case["category"] == "out_of_scope":
            case["category"] = "policy"
    with pytest.raises(ValueError, match="coverage is incomplete"):
        validate_cases(cases)

    cases = _valid_cases()
    for case in cases:
        case["latency_sample"] = False
    with pytest.raises(ValueError, match="10 to 20"):
        validate_cases(cases)


def test_case_validation_rejects_duplicate_ids():
    cases = _valid_cases()
    cases[1]["case_id"] = cases[0]["case_id"]

    with pytest.raises(ValueError, match="unique"):
        validate_cases(cases)


@pytest.mark.parametrize(
    ("percentile", "expected"),
    [(0.5, 2), (0.95, 4), (1.0, 4)],
)
def test_nearest_rank_percentiles(percentile, expected):
    assert percentile_nearest_rank([4, 1, 3, 2], percentile) == expected


def test_percentile_rejects_empty_or_out_of_range_values():
    with pytest.raises(ValueError, match="at least one"):
        percentile_nearest_rank([], 0.5)
    with pytest.raises(ValueError, match="greater than zero"):
        percentile_nearest_rank([1], 0)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("llm_request_failed", "provider_failure"),
        ("missing_llm_credentials", "provider_failure"),
        ("index_unavailable", "operational_failure"),
    ],
)
def test_failure_classification_keeps_provider_and_operational_failures_separate(
    code, expected
):
    assert classify_failure(code) == expected


def test_retrieval_comparison_aggregates_expected_source_recall(monkeypatch):
    calls = []

    def fake_retrieve(query, index_dir, *, embedder, k):
        calls.append((query, index_dir, k))
        ids = ["HR-002", "HR-003"] if k == 3 else ["HR-002", "HR-003", "HR-004"]
        return SimpleNamespace(
            evidence=[SimpleNamespace(document_id=document_id) for document_id in ids]
        )

    monkeypatch.setattr(evaluation, "retrieve", fake_retrieve)
    cases = [
        {
            "case_id": "EVAL-001",
            "request": "PTO request policy",
            "expected_source_ids": ["HR-002", "HR-004"],
        },
        {"case_id": "EVAL-002", "request": "profile lookup", "expected_source_ids": []},
    ]

    result = evaluation.run_retrieval_comparison(
        cases,
        settings=SimpleNamespace(index_dir="active-index"),
        embedder=object(),
    )

    assert result["cases_with_expected_sources"] == 1
    assert result["expected_source_count"] == 2
    assert result["matched_source_counts"] == {"3": 1, "5": 2}
    assert result["source_recall_at_3"] == 0.5
    assert result["source_recall_at_5"] == 1.0
    assert [call[2] for call in calls] == [3, 5]


def test_run_appends_completed_and_provider_failure_rows_without_retry(tmp_path):
    cases = _valid_cases()[:3]
    responses = iter(
        [
            AgentResponse(
                answer="PTO policy says submit the request to a manager.",
                status="answered",
                citations=[
                    Citation(
                        source_type="policy_evidence",
                        source_id="HR-002",
                        document_id="HR-002",
                        title="Paid Time Off Policy",
                        section="4.4 Approval workflow",
                        snippet="Synthetic policy evidence.",
                    )
                ],
                tool_calls=[
                    ToolInvocationRecord(
                        tool_name="search_policy_documents",
                        status="success",
                        arguments_summary={},
                        result_summary={"outcome": "found"},
                        duration_ms=1.0,
                    )
                ],
            ),
            AgentRuntimeError("llm_request_failed"),
        ]
    )

    class FakeSession:
        def __init__(self):
            self.calls = 0

        def process_request(self, request, context=None):
            self.calls += 1
            value = next(responses)
            if isinstance(value, Exception):
                raise value
            return value

    times = iter([1.0, 2.0, 3.0, 4.0])
    output_path = tmp_path / "results.jsonl"
    session = FakeSession()
    rows = run_cases(
        session,
        cases,
        run_id="run-test",
        code_revision="abc123",
        model_id="test-model",
        output_path=output_path,
        timer=lambda: next(times),
        sleep=lambda _delay: None,
    )

    persisted = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert session.calls == 2
    assert [row["outcome"] for row in rows] == ["completed", "provider_failure"]
    assert [row["case_id"] for row in persisted] == ["EVAL-000", "EVAL-001"]
    assert persisted[0]["source_ids"] == ["HR-002"]
    assert persisted[1]["failure_code"] == "llm_request_failed"


def test_run_stops_and_records_tool_timeout_as_operational_failure(tmp_path):
    class FailedSession:
        def __init__(self):
            self.calls = 0

        def process_request(self, request, context=None):
            self.calls += 1
            return AgentResponse(
                answer="The MCP tool call failed.",
                status="error",
                tool_calls=[
                    ToolInvocationRecord(
                        tool_name="search_policy_documents",
                        status="timeout",
                        arguments_summary={},
                        result_summary={"outcome": "error"},
                        duration_ms=300_000,
                        error_code="timeout",
                    )
                ],
                error_code="mcp_tool_call_failed",
            )

    session = FailedSession()
    cases = _valid_cases()[:3]
    cases[0]["required_tools"] = ["search_policy_documents"]
    rows = run_cases(
        session,
        cases,
        run_id="run-test",
        code_revision="abc123",
        model_id="test-model",
        output_path=tmp_path / "results.jsonl",
        timer=iter([1.0, 2.0]).__next__,
        sleep=lambda _delay: None,
    )

    assert session.calls == 1
    assert len(rows) == 1
    assert rows[0]["outcome"] == "operational_failure"
    assert rows[0]["failure_code"] == "mcp_tool_call_failed"
    assert rows[0]["metric_scores"]["tool_selection"] is True
    assert rows[0]["metric_scores"]["workflow_completion"] is None


def test_live_runner_refuses_to_repeat_an_existing_bounded_run(tmp_path, monkeypatch):
    results_path = tmp_path / "results.jsonl"
    results_path.write_text('{"case_id":"EVAL-001"}\n', encoding="utf-8")
    monkeypatch.setattr(evaluation, "RESULTS_PATH", results_path)
    monkeypatch.setattr(evaluation, "get_agent_setting", lambda *_args: "configured")

    with pytest.raises(FileExistsError, match="refusing to repeat"):
        evaluation.run_live_evaluation()


def test_live_diagnostic_records_one_successful_mcp_case_without_overwriting_partial_results(
    tmp_path, monkeypatch
):
    cases = _valid_cases()
    cases[0]["required_tools"] = ["search_policy_documents"]
    cases[0]["forbidden_tools"] = []
    monkeypatch.setattr(evaluation, "load_cases", lambda: cases)
    monkeypatch.setattr(
        evaluation, "_live_config", lambda: SimpleNamespace(model_name="test-model")
    )
    monkeypatch.setattr(evaluation, "_git_revision", lambda: "abc123")

    class FakeSession:
        calls = 0
        closed = False

        def process_request(self, request, context=None):
            self.calls += 1
            assert request == cases[0]["request"]
            return AgentResponse(
                answer="The supported policy answer.",
                status="answered",
                tool_calls=[
                    ToolInvocationRecord(
                        tool_name="search_policy_documents",
                        status="found",
                        arguments_summary={},
                        result_summary={"outcome": "found"},
                        duration_ms=1.0,
                    )
                ],
            )

        def close(self):
            self.closed = True

    session = FakeSession()
    monkeypatch.setattr(evaluation, "AgentSession", lambda _config: session)
    partial_results = tmp_path / "results.jsonl"
    partial_results.write_text('{"case_id":"EVAL-001","outcome":"operational_failure"}\n')

    assert evaluation.run_live_diagnostic(tmp_path) is True
    diagnostic_rows = [
        json.loads(line)
        for line in (tmp_path / "diagnostic.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert session.calls == 1
    assert session.closed
    assert [row["case_id"] for row in diagnostic_rows] == [cases[0]["case_id"]]
    assert diagnostic_rows[0]["outcome"] == "completed"
    assert partial_results.read_text(encoding="utf-8") == (
        '{"case_id":"EVAL-001","outcome":"operational_failure"}\n'
    )


def test_live_diagnostic_fails_closed_after_mcp_timeout(tmp_path, monkeypatch):
    cases = _valid_cases()
    cases[0]["required_tools"] = ["search_policy_documents"]
    monkeypatch.setattr(evaluation, "load_cases", lambda: cases)
    monkeypatch.setattr(
        evaluation, "_live_config", lambda: SimpleNamespace(model_name="test-model")
    )
    monkeypatch.setattr(evaluation, "_git_revision", lambda: "abc123")

    class FailedSession:
        calls = 0

        def process_request(self, request, context=None):
            self.calls += 1
            return AgentResponse(
                answer="The MCP tool call timed out.",
                status="error",
                error_code="mcp_tool_call_failed",
                tool_calls=[
                    ToolInvocationRecord(
                        tool_name="search_policy_documents",
                        status="timeout",
                        arguments_summary={},
                        result_summary={"outcome": "error"},
                        duration_ms=60_000,
                        error_code="timeout",
                    )
                ],
            )

        def close(self):
            pass

    session = FailedSession()
    monkeypatch.setattr(evaluation, "AgentSession", lambda _config: session)

    assert evaluation.run_live_diagnostic(tmp_path) is False
    assert session.calls == 1
    row = json.loads((tmp_path / "diagnostic.jsonl").read_text(encoding="utf-8"))
    assert row["outcome"] == "operational_failure"
    assert row["failure_code"] == "mcp_tool_call_failed"


def test_diagnostic_cli_returns_failure_status_to_gate_full_evaluation(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_evaluation.py", "--diagnostic", "--output-dir", str(tmp_path)],
    )
    monkeypatch.setattr(evaluation, "run_live_diagnostic", lambda _output_dir: False)

    assert evaluation.main() == 1


def test_live_evaluation_output_dir_preserves_existing_results(tmp_path, monkeypatch):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    partial_results = source_dir / "results.jsonl"
    partial_results.write_text('{"case_id":"EVAL-001","outcome":"operational_failure"}\n')
    monkeypatch.setattr(evaluation, "RESULTS_PATH", partial_results)
    monkeypatch.setattr(evaluation, "RETRIEVAL_PATH", source_dir / "retrieval_comparison.json")
    monkeypatch.setattr(evaluation, "REPORT_PATH", source_dir / "results.md")
    cases = _valid_cases()
    monkeypatch.setattr(evaluation, "load_cases", lambda: cases)
    monkeypatch.setattr(
        evaluation, "_live_config", lambda: SimpleNamespace(model_provider="groq", model_name="test-model")
    )
    monkeypatch.setattr(evaluation, "_git_revision", lambda: "abc123")
    monkeypatch.setattr(
        evaluation,
        "Settings",
        SimpleNamespace(
            from_environment=lambda: SimpleNamespace(
                index_dir="index",
                embedding_model="model",
                embedding_revision=None,
            )
        ),
    )
    monkeypatch.setattr(evaluation, "SentenceTransformerEmbedder", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        evaluation,
        "run_retrieval_comparison",
        lambda *_args, **_kwargs: {"source_recall_at_3": 0.0, "source_recall_at_5": 0.0},
    )
    monkeypatch.setattr(
        evaluation, "AgentSession", lambda _config: SimpleNamespace(close=lambda: None)
    )

    def fake_run_cases(_session, run_cases, **kwargs):
        kwargs["output_path"].write_text('{"outcome":"completed"}\n', encoding="utf-8")
        return [{"outcome": "completed"} for _ in run_cases]

    monkeypatch.setattr(
        evaluation,
        "run_cases",
        fake_run_cases,
    )
    report_paths = []
    monkeypatch.setattr(
        evaluation,
        "_write_report",
        lambda **kwargs: report_paths.append(kwargs["output_path"]),
    )
    output_dir = tmp_path / "run"

    assert evaluation.run_live_evaluation(output_dir) is True
    assert partial_results.read_text(encoding="utf-8") == (
        '{"case_id":"EVAL-001","outcome":"operational_failure"}\n'
    )
    assert (output_dir / "results.jsonl").exists()
    assert (output_dir / "retrieval_comparison.json").exists()
    assert report_paths == [output_dir / "results.md"]
