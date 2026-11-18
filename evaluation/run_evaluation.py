"""Run one bounded, sequential live evaluation with the existing HR agent."""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from hr_agent.config import AgentConfig, get_agent_setting
from hr_agent.errors import AgentError
from hr_app.runtime import AgentSession
from hr_rag import SentenceTransformerEmbedder, Settings, retrieve

ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"
CASES_PATH = EVALUATION_DIR / "cases.json"
RESULTS_PATH = EVALUATION_DIR / "results.jsonl"
RETRIEVAL_PATH = EVALUATION_DIR / "retrieval_comparison.json"
REPORT_PATH = EVALUATION_DIR / "results.md"
REQUIRED_CATEGORIES = {
    "policy",
    "multi_document",
    "tool_requiring",
    "ambiguous",
    "out_of_scope",
}
VALID_STATUSES = {
    "answered",
    "partial",
    "clarification_needed",
    "confirmation_required",
    "out_of_scope",
    "error",
}
PROVIDER_FAILURE_CODES = {"missing_llm_credentials", "llm_request_failed"}
OPERATIONAL_FAILURE_CODES = {
    "data_unavailable",
    "discovery_failure",
    "embedding_failure",
    "index_unavailable",
    "internal_error",
    "mcp_tool_call_failed",
    "timeout",
    "trace_persistence_failure",
    "transport_failure",
    "unclassified_error",
}
REQUEST_DELAY_SECONDS = 1.0
SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,79}")


def validate_cases(raw: object) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        raise TypeError("Evaluation cases must be a list.")
    if not 20 <= len(raw) <= 30:
        raise ValueError("Evaluation cases must be a list of 20 to 30 entries.")

    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    categories: set[str] = set()
    latency_count = 0
    for entry in raw:
        if not isinstance(entry, dict):
            raise TypeError("Each evaluation case must be an object.")
        required_fields = {
            "case_id",
            "category",
            "request",
            "context",
            "gold_answer_or_rubric",
            "expected_source_ids",
            "required_tools",
            "forbidden_tools",
            "expected_status",
            "safety_assertions",
            "latency_sample",
        }
        if not required_fields <= entry.keys():
            raise ValueError("An evaluation case is missing required fields.")
        case_id = entry["case_id"]
        category = entry["category"]
        if not isinstance(case_id, str):
            raise TypeError("Evaluation case IDs must be strings.")
        if not case_id or case_id in seen_ids:
            raise ValueError("Evaluation case IDs must be unique nonempty strings.")
        if not isinstance(category, str):
            raise TypeError(f"Evaluation category in {case_id} must be a string.")
        if category not in REQUIRED_CATEGORIES:
            raise ValueError(f"Unknown evaluation category in {case_id}.")
        if not isinstance(entry["request"], str):
            raise TypeError(f"Evaluation request {case_id} must be a string.")
        if not entry["request"].strip():
            raise ValueError(f"Evaluation request {case_id} must not be blank.")
        if not isinstance(entry["gold_answer_or_rubric"], str):
            raise TypeError(f"Evaluation rubric {case_id} must be a string.")
        context = entry["context"]
        if context is not None and (
            not isinstance(context, dict)
            or any(not isinstance(key, str) for key in context)
        ):
            raise TypeError(f"Evaluation context {case_id} must be an object or null.")
        for field in (
            "expected_source_ids",
            "required_tools",
            "forbidden_tools",
            "expected_status",
            "safety_assertions",
        ):
            values = entry[field]
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise TypeError(f"{field} in {case_id} must be a string list.")
        if any(status not in VALID_STATUSES for status in entry["expected_status"]):
            raise ValueError(f"Evaluation case {case_id} has an unknown expected status.")
        latency_sample = entry["latency_sample"]
        if not isinstance(latency_sample, bool):
            raise TypeError(f"latency_sample in {case_id} must be boolean.")
        latency_count += int(latency_sample)
        seen_ids.add(case_id)
        categories.add(category)
        cases.append(entry)

    if categories != REQUIRED_CATEGORIES:
        missing = sorted(REQUIRED_CATEGORIES - categories)
        raise ValueError(f"Evaluation category coverage is incomplete: {', '.join(missing)}.")
    if not 10 <= latency_count <= 20:
        raise ValueError("Evaluation cases must select 10 to 20 fixed latency samples.")
    return cases


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as case_file:
        return validate_cases(json.load(case_file))


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("Percentiles require at least one value.")
    if not 0 < percentile <= 1:
        raise ValueError("Percentile must be greater than zero and at most one.")
    ordered = sorted(values)
    rank = math.ceil(percentile * len(ordered))
    return ordered[rank - 1]


def classify_failure(code: str) -> str:
    return "provider_failure" if code in PROVIDER_FAILURE_CODES else "operational_failure"


def _safe_failure_code(code: str) -> str:
    return code if SAFE_CODE.fullmatch(code) else "unclassified_error"


def _metric_scores(response: Any, case: dict[str, Any]) -> dict[str, bool | None]:
    observed = [tool.tool_name for tool in response.tool_calls]
    required = set(case["required_tools"])
    forbidden = set(case["forbidden_tools"])
    tool_selection: bool | None = None
    if required or forbidden:
        tool_selection = required <= set(observed) and not forbidden.intersection(observed)
    return {
        "workflow_completion": response.status in case["expected_status"],
        "tool_selection": tool_selection,
        "case_correctness": None,
        "groundedness": None,
        "citation_accuracy": None,
        "escalation_clarification": (
            response.status in case["expected_status"]
            if case["category"] in {"ambiguous", "out_of_scope"}
            else None
        ),
        "action_safety": None,
    }


def _response_row(
    response: Any,
    case: dict[str, Any],
    *,
    run_id: str,
    code_revision: str,
    model_id: str,
    duration_ms: float,
    latency_condition: str,
) -> dict[str, Any]:
    source_ids = sorted(
        {
            citation.document_id
            for citation in response.citations
            if citation.source_type == "policy_evidence"
        }
    )
    tool_outcomes = [
        {
            "tool_name": tool.tool_name,
            "status": tool.status,
            "error_code": tool.error_code,
        }
        for tool in response.tool_calls
    ]
    failure_code = response.error_code
    outcome = "completed"
    if failure_code in PROVIDER_FAILURE_CODES:
        outcome = "provider_failure"
    elif failure_code in OPERATIONAL_FAILURE_CODES:
        outcome = "operational_failure"
    metric_scores = _metric_scores(response, case)
    if outcome != "completed":
        metric_scores["workflow_completion"] = None
        metric_scores["case_correctness"] = None
        metric_scores["groundedness"] = None
        metric_scores["citation_accuracy"] = None
        metric_scores["escalation_clarification"] = None
        metric_scores["action_safety"] = None
    return {
        "case_id": case["case_id"],
        "run_id": run_id,
        "code_revision": code_revision,
        "outcome": outcome,
        "response_status": response.status,
        "answer": response.answer,
        "tool_names": [tool.tool_name for tool in response.tool_calls],
        "tool_outcomes": tool_outcomes,
        "source_ids": source_ids,
        "metric_scores": metric_scores,
        "duration_ms": round(duration_ms, 2),
        "latency_condition": latency_condition,
        "failure_code": response.error_code,
        "model_id": model_id,
        "latency_sample": case["latency_sample"],
    }


def _failure_row(
    case: dict[str, Any],
    *,
    run_id: str,
    code_revision: str,
    model_id: str,
    error_code: str,
    duration_ms: float,
    latency_condition: str,
) -> dict[str, Any]:
    safe_code = _safe_failure_code(error_code)
    return {
        "case_id": case["case_id"],
        "run_id": run_id,
        "code_revision": code_revision,
        "outcome": classify_failure(safe_code),
        "response_status": None,
        "answer": None,
        "tool_names": [],
        "tool_outcomes": [],
        "source_ids": [],
        "metric_scores": {
            "workflow_completion": None,
            "tool_selection": None,
            "case_correctness": None,
            "groundedness": None,
            "citation_accuracy": None,
            "escalation_clarification": None,
            "action_safety": None,
        },
        "duration_ms": round(duration_ms, 2),
        "latency_condition": latency_condition,
        "failure_code": safe_code,
        "model_id": model_id,
        "latency_sample": case["latency_sample"],
    }


def run_cases(
    session: Any,
    cases: list[dict[str, Any]],
    *,
    run_id: str,
    code_revision: str,
    model_id: str,
    output_path: Path,
    timer: Callable[[], float] = time.perf_counter,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, case in enumerate(cases):
        if index:
            sleep(REQUEST_DELAY_SECONDS)
        latency_condition = "first_request" if index == 0 else "warm"
        started = timer()
        try:
            response = session.process_request(case["request"], context=case["context"])
        except AgentError as exc:
            duration_ms = (timer() - started) * 1000
            row = _failure_row(
                case,
                run_id=run_id,
                code_revision=code_revision,
                model_id=model_id,
                error_code=exc.code,
                duration_ms=duration_ms,
                latency_condition=latency_condition,
            )
            _append_jsonl(output_path, row)
            rows.append(row)
            break
        duration_ms = (timer() - started) * 1000
        row = _response_row(
            response,
            case,
            run_id=run_id,
            code_revision=code_revision,
            model_id=model_id,
            duration_ms=duration_ms,
            latency_condition=latency_condition,
        )
        _append_jsonl(output_path, row)
        rows.append(row)
        if row["outcome"] != "completed":
            break
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as result_file:
        result_file.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_retrieval_comparison(
    cases: list[dict[str, Any]],
    *,
    settings: Settings,
    embedder: Any,
) -> dict[str, Any]:
    per_case: list[dict[str, Any]] = []
    for case in cases:
        expected = sorted(set(case["expected_source_ids"]))
        if not expected:
            continue
        query = case.get("retrieval_query", case["request"])
        retrieved_by_k: dict[str, list[str]] = {}
        matched_by_k: dict[str, list[str]] = {}
        for k in (3, 5):
            result = retrieve(query, settings.index_dir, embedder=embedder, k=k)
            ids = sorted({item.document_id for item in result.evidence})
            retrieved_by_k[str(k)] = ids
            matched_by_k[str(k)] = sorted(set(expected) & set(ids))
        per_case.append(
            {
                "case_id": case["case_id"],
                "expected_source_ids": expected,
                "retrieved_source_ids": retrieved_by_k,
                "matched_source_ids": matched_by_k,
                "source_recall_at_3": len(matched_by_k["3"]) / len(expected),
                "source_recall_at_5": len(matched_by_k["5"]) / len(expected),
            }
        )

    expected_count = sum(len(item["expected_source_ids"]) for item in per_case)
    hit_counts = {
        str(k): sum(len(item["matched_source_ids"][str(k)]) for item in per_case)
        for k in (3, 5)
    }
    return {
        "cases_with_expected_sources": len(per_case),
        "expected_source_count": expected_count,
        "source_recall_at_3": hit_counts["3"] / expected_count if expected_count else None,
        "source_recall_at_5": hit_counts["5"] / expected_count if expected_count else None,
        "matched_source_counts": hit_counts,
        "per_case": per_case,
    }


def _git_revision() -> str:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return revision + ("+dirty" if status else "")


def _write_retrieval_result(
    run_id: str,
    retrieval: dict[str, Any],
    *,
    output_path: Path = RETRIEVAL_PATH,
) -> None:
    payload = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        **retrieval,
    }
    with output_path.open("w", encoding="utf-8") as result_file:
        json.dump(payload, result_file, ensure_ascii=False, indent=2)
        result_file.write("\n")


def _metric_summary(
    rows: list[dict[str, Any]], metric_name: str
) -> tuple[int, int]:
    values = [row["metric_scores"].get(metric_name) for row in rows]
    scored = [value for value in values if isinstance(value, bool)]
    return sum(value is True for value in scored), len(scored)


def _write_report(
    *,
    run_id: str,
    code_revision: str,
    model_id: str,
    cases: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    retrieval: dict[str, Any],
    output_path: Path = REPORT_PATH,
) -> None:
    outcomes = Counter(row["outcome"] for row in rows)
    not_run = len(cases) - len(rows)
    latency_rows = [
        row
        for row in rows
        if row["outcome"] == "completed"
        and row["latency_sample"]
        and isinstance(row["duration_ms"], (int, float))
    ]
    latency_values = [row["duration_ms"] for row in latency_rows]
    latency_target = sum(case["latency_sample"] for case in cases)
    if latency_values:
        latency_text = (
            f"{len(latency_values)}/{latency_target} selected cases completed; "
            f"p50={percentile_nearest_rank(latency_values, 0.50):.2f} ms, "
            f"p95={percentile_nearest_rank(latency_values, 0.95):.2f} ms "
            "(nearest rank; agent request duration)"
        )
    else:
        latency_text = (
            f"0/{latency_target} selected cases completed; p50/p95 unavailable "
            "(failed attempts are excluded)"
        )

    workflow_passed, workflow_scored = _metric_summary(rows, "workflow_completion")
    tool_passed, tool_scored = _metric_summary(rows, "tool_selection")
    category_counts = Counter(case["category"] for case in cases)
    failure_rows = [
        row for row in rows if row["outcome"] in {"provider_failure", "operational_failure"}
    ]
    first_failure = failure_rows[0] if failure_rows else None
    operational_label = "operational failure" if outcomes["operational_failure"] == 1 else "operational failures"
    recall_3 = retrieval["source_recall_at_3"]
    recall_5 = retrieval["source_recall_at_5"]
    recall_3_text = "n/a" if recall_3 is None else f"{recall_3:.1%}"
    recall_5_text = "n/a" if recall_5 is None else f"{recall_5:.1%}"
    report = [
        "# F006 Bounded Evaluation Results",
        "",
        f"- Run: `{run_id}`",
        f"- Code revision: `{code_revision}`",
        f"- Groq model: `{model_id}`",
        (
            f"- Cases: {len(cases)} planned; {len(rows)} attempted; "
            f"{outcomes['completed']} successful completions; "
            f"{outcomes['provider_failure']} provider failures; "
            f"{outcomes['operational_failure']} {operational_label}; {not_run} not run."
        ),
        (
            f"- Stop reason: {first_failure['case_id']} ended as "
            f"{first_failure['outcome']} ({first_failure['failure_code']}) after "
            f"{first_failure['duration_ms']:.2f} ms."
            if first_failure
            else "- Stop reason: all planned cases completed."
        ),
        f"- Categories: {', '.join(f'{category}={category_counts[category]}' for category in sorted(category_counts))}.",
        f"- Workflow status match: {workflow_passed}/{workflow_scored} scored.",
        f"- Tool-selection match: {tool_passed}/{tool_scored} cases with tool constraints.",
        f"- Latency: {latency_text}.",
        (
            "- Correctness, groundedness, citation accuracy, escalation quality, and action safety "
            "require answer-level rubric review; their per-case fields remain null until scored."
        ),
        "",
        "## Retrieval comparison",
        "",
        (
            f"- Applicable cases: {retrieval['cases_with_expected_sources']}; "
            f"expected source labels: {retrieval['expected_source_count']}."
        ),
        (
            f"- k=3 source recall: {retrieval['matched_source_counts']['3']}/"
            f"{retrieval['expected_source_count']} "
            f"({recall_3_text})."
        ),
        (
            f"- k=5 source recall: {retrieval['matched_source_counts']['5']}/"
            f"{retrieval['expected_source_count']} "
            f"({recall_5_text})."
        ),
        (
            "- Retrieval is measured independently from Groq answers against the checked-in "
            "expected-source labels; it makes no provider calls."
        ),
        "",
        "## Review and limitations",
        "",
        (
            "- Provider and operational errors are stored separately in `results.jsonl`; no case "
            "is retried and completed rows are appended immediately."
        ),
        (
            "- Answer-level correctness and safety scores are intentionally not inferred from "
            "keyword matching. Review each retained synthetic answer against its case rubric."
        ),
        (
            "- Latency measures `AgentSession.process_request`, including Groq and MCP work but not "
            "browser rendering. `first_request` and `warm` refer to this evaluation session."
        ),
        "- No raw provider payloads, tool arguments, credentials, or hidden reasoning are stored.",
        "",
    ]
    if rows:
        report.extend(
            [
                "## Attempted cases",
                "",
                "| Case | Outcome | Status | Tools | Sources | Workflow match | Failure | Duration |",
                "|---|---|---|---|---|---:|---|---:|",
            ]
        )
        for row in rows:
            scores = row["metric_scores"]
            status_match = scores.get("workflow_completion")
            report.append(
                f"| {row['case_id']} | {row['outcome']} | "
                f"{row['response_status'] or '—'} | "
                f"{', '.join(row['tool_names']) or '—'} | "
                f"{', '.join(row['source_ids']) or '—'} | "
                f"{status_match if status_match is not None else 'unscored'} | "
                f"{row['failure_code'] or '—'} | {row['duration_ms']:.2f} ms |"
            )
        report.append("")
    output_path.write_text("\n".join(report), encoding="utf-8")


def _live_config() -> AgentConfig:
    if not get_agent_setting("GROQ_API_KEY"):
        raise RuntimeError("GROQ_API_KEY is not configured; no live evaluation was started.")
    config = AgentConfig.from_environment()
    if config.model_provider.lower() != "groq":
        raise ValueError("F006 evaluation must use the existing Groq provider.")
    return config


def run_live_diagnostic(
    output_dir: Path | None = None, *, case_id: str = "EVAL-001"
) -> bool:
    cases = load_cases()
    case = next((case for case in cases if case["case_id"] == case_id), None)
    if case is None:
        raise ValueError(f"Unknown diagnostic case ID: {case_id}")
    if not case["required_tools"]:
        raise ValueError("The diagnostic evaluation case must require an MCP tool.")
    config = _live_config()
    code_revision = _git_revision()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    diagnostic_path = (
        output_dir / "diagnostic.jsonl"
        if output_dir is not None
        else EVALUATION_DIR / "diagnostic.jsonl"
    )
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)
    if diagnostic_path.exists():
        raise FileExistsError(
            f"{diagnostic_path} already exists; refusing to overwrite the diagnostic result."
        )

    session = AgentSession(config)
    try:
        rows = run_cases(
            session,
            [case],
            run_id=run_id,
            code_revision=code_revision,
            model_id=config.model_name,
            output_path=diagnostic_path,
        )
    finally:
        session.close()

    row = rows[0]
    required_tools = set(case["required_tools"])
    successful_tools = {
        tool["tool_name"]
        for tool in row["tool_outcomes"]
        if tool["status"] in {"found", "success"}
    }
    passed = (
        row["outcome"] == "completed"
        and row["metric_scores"]["workflow_completion"] is True
        and row["metric_scores"]["tool_selection"] is True
        and required_tools <= successful_tools
    )
    print(
        f"Diagnostic {run_id}: case={row['case_id']}, "
        f"result={'passed' if passed else 'failed'}, outcome={row['outcome']}, "
        f"failure={row['failure_code'] or 'none'}, duration_ms={row['duration_ms']:.2f}"
    )
    return passed


def run_live_evaluation(output_dir: Path | None = None) -> bool:
    cases = load_cases()
    config = _live_config()
    results_path = output_dir / RESULTS_PATH.name if output_dir is not None else RESULTS_PATH
    retrieval_path = (
        output_dir / RETRIEVAL_PATH.name if output_dir is not None else RETRIEVAL_PATH
    )
    report_path = output_dir / REPORT_PATH.name if output_dir is not None else REPORT_PATH
    results_path.parent.mkdir(parents=True, exist_ok=True)
    if results_path.exists():
        raise FileExistsError(
            f"{results_path} already exists; refusing to repeat or overwrite the bounded run."
        )

    revision = _git_revision()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    settings = Settings.from_environment()
    embedder = SentenceTransformerEmbedder(
        settings.embedding_model,
        revision=settings.embedding_revision,
    )
    retrieval = run_retrieval_comparison(cases, settings=settings, embedder=embedder)
    _write_retrieval_result(run_id, retrieval, output_path=retrieval_path)

    session = AgentSession(config)
    try:
        rows = run_cases(
            session,
            cases,
            run_id=run_id,
            code_revision=revision,
            model_id=config.model_name,
            output_path=results_path,
        )
    finally:
        session.close()
    _write_report(
        run_id=run_id,
        code_revision=revision,
        model_id=config.model_name,
        cases=cases,
        rows=rows,
        retrieval=retrieval,
        output_path=report_path,
    )
    outcomes = Counter(row["outcome"] for row in rows)
    print(
        f"Evaluation {run_id}: attempted={len(rows)}/{len(cases)}, "
        f"completed={outcomes['completed']}, provider_failures={outcomes['provider_failure']}, "
        f"operational_failures={outcomes['operational_failure']}, "
        f"not_run={len(cases) - len(rows)}"
    )
    return len(rows) == len(cases) and outcomes["completed"] == len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="authorize one bounded Groq run")
    mode.add_argument(
        "--diagnostic",
        action="store_true",
        help="run one MCP-backed case before the bounded evaluation",
    )
    mode.add_argument("--validate-only", action="store_true", help="validate cases without Groq")
    parser.add_argument(
        "--diagnostic-case",
        help="case ID for --diagnostic (default: EVAL-001); does not select full-suite cases",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="write run outputs outside the checked-in evaluation evidence",
    )
    args = parser.parse_args()
    if args.diagnostic_case is not None and not args.diagnostic:
        parser.error("--diagnostic-case requires --diagnostic")
    cases = load_cases()
    if args.validate_only:
        latency_count = sum(case["latency_sample"] for case in cases)
        print(
            f"Valid cases: {len(cases)}; categories: {len(REQUIRED_CATEGORIES)}; "
            f"latency samples selected: {latency_count}"
        )
        return 0
    if args.diagnostic:
        return 0 if run_live_diagnostic(
            args.output_dir,
            case_id=args.diagnostic_case if args.diagnostic_case is not None else "EVAL-001",
        ) else 1
    return 0 if run_live_evaluation(args.output_dir) else 1


if __name__ == "__main__":
    sys.exit(main())
