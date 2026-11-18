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


@pytest.mark.parametrize("case_id", [None, "EVAL-003"])
def test_live_diagnostic_records_one_selected_mcp_case_without_overwriting_partial_results(
    tmp_path, monkeypatch, case_id
):
    cases = load_cases()
    selected_case = next(
        case for case in cases if case["case_id"] == (case_id or "EVAL-001")
    )
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
            assert request == selected_case["request"]
            assert context == selected_case["context"]
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

    if case_id is None:
        assert evaluation.run_live_diagnostic(tmp_path) is True
    else:
        assert evaluation.run_live_diagnostic(tmp_path, case_id=case_id) is True
    diagnostic_rows = [
        json.loads(line)
        for line in (tmp_path / "diagnostic.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert session.calls == 1
    assert session.closed
    assert [row["case_id"] for row in diagnostic_rows] == [selected_case["case_id"]]
    assert diagnostic_rows[0]["outcome"] == "completed"
    assert partial_results.read_text(encoding="utf-8") == (
        '{"case_id":"EVAL-001","outcome":"operational_failure"}\n'
    )


def test_live_diagnostic_fails_closed_after_mcp_timeout(tmp_path, monkeypatch):
    cases = load_cases()
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


@pytest.mark.parametrize("case_id", [None, "EVAL-003"])
def test_diagnostic_cli_selects_one_case_and_returns_failure_status_to_gate_full_evaluation(
    tmp_path, monkeypatch, case_id
):
    argv = ["run_evaluation.py", "--diagnostic", "--output-dir", str(tmp_path)]
    if case_id is not None:
        argv.extend(["--diagnostic-case", case_id])
    monkeypatch.setattr(sys, "argv", argv)
    calls = []

    def fake_diagnostic(output_dir, *, case_id):
        calls.append((output_dir, case_id))
        return False

    monkeypatch.setattr(evaluation, "run_live_diagnostic", fake_diagnostic)

    assert evaluation.main() == 1
    assert calls == [(tmp_path, case_id or "EVAL-001")]


@pytest.mark.parametrize("mode", ["--live", "--validate-only"])
def test_diagnostic_case_option_rejects_other_modes_before_execution(monkeypatch, mode):
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_evaluation.py", mode, "--diagnostic-case", "EVAL-003"],
    )

    with pytest.raises(SystemExit) as exc:
        evaluation.main()
    assert exc.value.code == 2


@pytest.mark.parametrize("case_id", ["EVAL-999", "EVAL-001"])
def test_diagnostic_rejects_unknown_or_non_mcp_case_before_live_configuration(
    tmp_path, monkeypatch, case_id
):
    cases = load_cases()
    cases[0]["required_tools"] = []
    monkeypatch.setattr(evaluation, "load_cases", lambda: cases)

    def fail_if_configured():
        pytest.fail("Invalid case selection must not configure or start a live session.")

    monkeypatch.setattr(evaluation, "_live_config", fail_if_configured)

    with pytest.raises(ValueError, match="Unknown diagnostic case|must require an MCP tool"):
        evaluation.run_live_diagnostic(tmp_path, case_id=case_id)
    assert not (tmp_path / "diagnostic.jsonl").exists()


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


@pytest.mark.parametrize("coverage_first", [False, True])
@pytest.mark.parametrize(
    ("diagnostic", "expected_calls", "expected_reason"),
    [
        ({"http_status": 400, "provider_error_code": "tool_use_failed"}, 4, "failure_limit"),
        ({"http_status": 401}, 1, "fatal_provider_error"),
        ({"http_status": 403}, 1, "fatal_provider_error"),
        ({"http_status": 429}, 1, "fatal_provider_error"),
        ({"http_status": 404}, 1, "fatal_provider_error"),
        ({"http_status": 400, "provider_error_code": "insufficient_quota"}, 1, "fatal_provider_error"),
        ({"http_status": 400, "provider_error_code": "model_decommissioned"}, 1, "fatal_provider_error"),
        (None, 1, "provider_diagnostic_unavailable"),
    ],
)
def test_continuation_records_failures_once_and_stops_at_bound(
    tmp_path, diagnostic, expected_calls, expected_reason, coverage_first
):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(json.dumps({"events": [{"provider_diagnostic": {"http_status": 401}}]}) + "\n")
    cases = load_cases()[3:9]
    if coverage_first:
        cases = [
            case for case in load_cases() if case["case_id"] in evaluation.COVERAGE_CASE_IDS
        ]
    if coverage_first and diagnostic == {
        "http_status": 400, "provider_error_code": "tool_use_failed",
    }:
        expected_calls, expected_reason = len(cases), None
    attempted = []

    class Session:
        def process_request(self, request, context=None):
            attempted.append(request)
            if diagnostic is not None:
                with trace.open("a") as handle:
                    handle.write(json.dumps({"events": [{"provider_diagnostic": diagnostic}]}) + "\n")
            if len(attempted) == 2:
                return AgentResponse(answer="Synthetic answer", status="answered")
            raise AgentRuntimeError("llm_request_failed")

    output = tmp_path / "continuation-results.jsonl"
    rows = run_cases(
        Session(), cases, run_id="run", code_revision="sha", model_id="model",
        output_path=output, sleep=lambda _delay: None,
        continue_on_failure=True, provider_trace_path=trace,
        coverage_first=coverage_first,
    )
    assert len(attempted) == expected_calls
    assert len(set(attempted)) == len(attempted)
    assert rows[-1].get("evaluation_stop_reason") == expected_reason
    if diagnostic is not None and diagnostic.get("http_status") == 400:
        assert rows[0]["provider_diagnostic"]["http_status"] == 400
    assert len(output.read_text().splitlines()) == expected_calls
    journal_name = "coverage-attempts.jsonl" if coverage_first else "continuation-attempts.jsonl"
    journal = [
        json.loads(line)
        for line in (tmp_path / journal_name).read_text().splitlines()
    ]
    assert [entry["state"] for entry in journal] == ["started", "finished"] * expected_calls


def test_continuation_stops_after_three_operational_failures(tmp_path):
    class Session:
        def process_request(self, request, context=None):
            raise AgentRuntimeError("mcp_tool_call_failed")

    rows = run_cases(
        Session(), load_cases()[3:], run_id="run", code_revision="sha", model_id="model",
        output_path=tmp_path / "results.jsonl", sleep=lambda _delay: None,
        continue_on_failure=True, provider_trace_path=tmp_path / "trace.jsonl",
    )
    assert len(rows) == 3
    assert rows[-1]["evaluation_stop_reason"] == "failure_limit"
    assert all(row["outcome"] == "operational_failure" for row in rows)


@pytest.mark.parametrize("completed_count", [9, 10, 17])
def test_continuation_selection_preserves_defaults_and_requires_ten_latency_samples(
    tmp_path, monkeypatch, completed_count
):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(evaluation, "_git_revision", lambda: "sha")
    monkeypatch.setattr(
        evaluation, "_live_config",
        lambda: SimpleNamespace(model_name="test-model", trace_path=tmp_path / "trace.jsonl"),
    )
    monkeypatch.setattr(
        evaluation, "AgentSession", lambda _config: SimpleNamespace(close=lambda: None)
    )
    observed = []

    def fake_run_cases(_session, cases, **kwargs):
        observed.extend(case["case_id"] for case in cases)
        assert kwargs["continue_on_failure"] is True
        return [
            {"outcome": "completed", "response_status": "clarification_needed", "duration_ms": i + 1}
            for i in range(completed_count)
        ]

    monkeypatch.setattr(evaluation, "run_cases", fake_run_cases)
    source_cases = load_cases()
    evaluation.run_continuation(tmp_path)
    assert observed == list(evaluation.CONTINUATION_CASE_IDS)
    assert set(observed) == {f"EVAL-{i:03d}" for i in range(4, 21)}
    categories = {case["case_id"]: case["category"] for case in source_cases}
    assert [categories[case_id] for case_id in observed[:5]] == [
        "policy", "multi_document", "tool_requiring", "ambiguous", "out_of_scope",
    ]
    assert len(set(observed)) == 17
    assert load_cases() == source_cases
    summary = json.loads((tmp_path / "continuation-summary.json").read_text())
    assert summary["qualifying_latency_samples"] == completed_count
    assert summary["p50_ms"] == (5 if completed_count == 10 else 9 if completed_count == 17 else None)
    assert summary["p95_ms"] == (10 if completed_count == 10 else 17 if completed_count == 17 else None)
    with pytest.raises(FileExistsError, match="Refusing to repeat"):
        evaluation.run_continuation(tmp_path)


@pytest.mark.parametrize("mode", ["--continue-remaining", "--cover-unattempted"])
def test_continuation_cli_rejects_missing_output_dir_before_live_work(monkeypatch, mode):
    monkeypatch.setattr(sys, "argv", ["run_evaluation.py", mode])
    with pytest.raises(SystemExit) as exc:
        evaluation.main()
    assert exc.value.code == 2


def test_duplicate_selection_is_rejected_before_attempting_any_case(tmp_path):
    case = load_cases()[0]
    with pytest.raises(ValueError, match="at most once"):
        run_cases(
            None, [case, case], run_id="run", code_revision="sha", model_id="model",
            output_path=tmp_path / "results.jsonl",
        )
    assert not (tmp_path / "results.jsonl").exists()


def test_coverage_counts_repeated_infrastructure_failures_but_not_tool_generation(tmp_path):
    trace = tmp_path / "trace.jsonl"
    attempted = []

    class Session:
        def process_request(self, request, context=None):
            attempted.append(request)
            if len(attempted) % 2:
                with trace.open("a") as handle:
                    handle.write(json.dumps({"events": [{"provider_diagnostic": {
                        "http_status": 400, "provider_error_code": "tool_use_failed",
                    }}]}) + "\n")
                raise AgentRuntimeError("llm_request_failed")
            raise AgentRuntimeError("mcp_tool_call_failed")

    rows = run_cases(
        Session(), load_cases()[3:], run_id="run", code_revision="sha", model_id="model",
        output_path=tmp_path / "coverage-results.jsonl", sleep=lambda _delay: None,
        continue_on_failure=True, provider_trace_path=trace, coverage_first=True,
    )
    assert len(attempted) == len(set(attempted)) == len(rows) == 6
    assert rows[-1]["evaluation_stop_reason"] == "failure_limit"
    assert [row["outcome"] for row in rows] == [
        "provider_failure", "operational_failure",
    ] * 3


def test_coverage_retains_fatal_category_stop_even_with_tool_failure_code(tmp_path):
    trace = tmp_path / "trace.jsonl"

    class Session:
        def process_request(self, request, context=None):
            trace.write_text(json.dumps({"events": [{"provider_diagnostic": {
                "http_status": 400, "provider_error_code": "tool_use_failed",
                "category": "authentication",
            }}]}) + "\n")
            raise AgentRuntimeError("llm_request_failed")

    rows = run_cases(
        Session(), load_cases()[3:], run_id="run", code_revision="sha", model_id="model",
        output_path=tmp_path / "coverage-results.jsonl", sleep=lambda _delay: None,
        continue_on_failure=True, provider_trace_path=trace, coverage_first=True,
    )
    assert len(rows) == 1
    assert rows[0]["evaluation_stop_reason"] == "fatal_provider_error"


def test_coverage_selects_only_unattempted_cases_and_reserves_new_artifacts(tmp_path, monkeypatch):
    output = tmp_path / "fresh"
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(evaluation, "_git_revision", lambda: "sha")
    monkeypatch.setattr(
        evaluation, "_live_config",
        lambda: SimpleNamespace(
            model_name="test-model", trace_path=output / "agent.jsonl", max_tool_calls=3,
        ),
    )
    monkeypatch.setenv("HR_MCP_TRACE_PATH", str(output / "mcp.jsonl"))
    sessions = []
    monkeypatch.setattr(
        evaluation, "AgentSession",
        lambda _config: sessions.append(True) or SimpleNamespace(close=lambda: None),
    )
    observed = []

    def fake_run_cases(_session, cases, **kwargs):
        assert kwargs["coverage_first"] is True
        assert kwargs["output_path"] == output / "coverage-results.jsonl"
        observed.extend(case["case_id"] for case in cases)
        return [
            {"outcome": "completed", "response_status": "answered", "duration_ms": i + 1}
            for i in range(len(cases))
        ]

    monkeypatch.setattr(evaluation, "run_cases", fake_run_cases)
    original_cases = load_cases()
    assert evaluation.run_continuation(output, coverage_first=True)
    prior = json.loads(
        (evaluation.EVALUATION_DIR / "completion-metrics.json").read_text()
    )["attempted_case_ids"]
    assert len(observed) == len(set(observed)) == 13
    assert set(observed) == {case["case_id"] for case in original_cases} - set(prior)
    assert observed == [
        "EVAL-017", "EVAL-006", "EVAL-010", "EVAL-014", "EVAL-018",
        "EVAL-007", "EVAL-011", "EVAL-015", "EVAL-019",
        "EVAL-008", "EVAL-012", "EVAL-016", "EVAL-020",
    ]
    assert load_cases() == original_cases
    summary = json.loads((output / "coverage-summary.json").read_text())
    assert summary["max_completion_calls"] == 52
    assert summary["max_sdk_http_attempts_estimate"] == 156
    assert summary["overall_job_timeout_minutes"] == 15
    assert summary["live_step_timeout_minutes"] == 10
    assert summary["p50_ms"] == 7 and summary["p95_ms"] == 13
    with pytest.raises(FileExistsError):
        evaluation.run_continuation(output, coverage_first=True)
    assert len(sessions) == 1


@pytest.mark.parametrize("guard", ["tool_budget", "agent_trace", "mcp_trace"])
def test_coverage_rejects_unsafe_configuration_before_creating_session(
    tmp_path, monkeypatch, guard
):
    output = tmp_path / "fresh"
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        evaluation, "_live_config",
        lambda: SimpleNamespace(
            model_name="test-model",
            trace_path=(tmp_path if guard == "agent_trace" else output) / "agent.jsonl",
            max_tool_calls=4 if guard == "tool_budget" else 3,
        ),
    )
    monkeypatch.setenv(
        "HR_MCP_TRACE_PATH",
        str((tmp_path if guard == "mcp_trace" else output) / "mcp.jsonl"),
    )
    monkeypatch.setattr(evaluation, "AgentSession", lambda _config: pytest.fail("live session"))
    with pytest.raises(ValueError):
        evaluation.run_continuation(output, coverage_first=True)
    assert not output.exists()


@pytest.mark.parametrize("history", ["result", "started_journal", "repository_output"])
def test_coverage_preflight_rejects_prior_attempt_or_repository_output(
    tmp_path, monkeypatch, history
):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(evaluation, "_live_config", lambda: pytest.fail("live configuration"))
    if history == "repository_output":
        output = evaluation.ROOT / "evaluation" / "new-output"
    else:
        evidence = tmp_path / "history"
        evidence.mkdir()
        monkeypatch.setattr(evaluation, "EVALUATION_DIR", evidence)
        (evidence / "prior.jsonl").write_text(json.dumps({
            "case_id": "EVAL-006",
            **({"state": "started"} if history == "started_journal" else {"outcome": "completed"}),
        }) + "\n")
        output = tmp_path / "fresh"
    with pytest.raises(ValueError, match="already attempted|outside the repository"):
        evaluation.run_continuation(output, coverage_first=True)


def test_interrupted_case_remains_in_attempt_journal(tmp_path):
    class InterruptedSession:
        def process_request(self, request, context=None):
            raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError, match="interrupted"):
        run_cases(
            InterruptedSession(), load_cases()[3:4], run_id="run",
            code_revision="sha", model_id="model", output_path=tmp_path / "results.jsonl",
            continue_on_failure=True, provider_trace_path=tmp_path / "trace.jsonl",
        )
    journal = [
        json.loads(line)
        for line in (tmp_path / "continuation-attempts.jsonl").read_text().splitlines()
    ]
    assert [(entry["case_id"], entry["state"]) for entry in journal] == [("EVAL-004", "started")]
    assert not (tmp_path / "results.jsonl").exists()
