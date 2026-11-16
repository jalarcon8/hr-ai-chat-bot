import asyncio
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig, get_agent_setting
from hr_agent.errors import AgentRuntimeError
from hr_agent.llm import GroqLLMClient
from hr_mcp.client import ClientError
from tests.fixtures.mcp.f004_diagnostic import (
    observe_calls,
    policy_citation_matches,
    require,
)
from tests.fixtures.mcp.harness import build_context, connect, rebuild
from tests.test_f004_workflows import APPROVAL_FACTS, assert_point_in_time_balance
from tests.unit.agent_orchestration_helpers import (
    FakeMCPClient,
    ScriptedLLM,
    final_completion,
    tool_completion,
)


def acceptance_client(provider, completions):
    if provider == "scripted":
        return ScriptedLLM(completions), AgentConfig()
    if get_agent_setting("AGENT_RUN_F004_LIVE") != "1":
        pytest.skip("Set AGENT_RUN_F004_LIVE=1 for one selected live acceptance scenario.")
    if not get_agent_setting("GROQ_API_KEY"):
        pytest.skip("BLOCKED: GROQ_API_KEY is not configured.")
    config = AgentConfig.from_environment()
    require(config.model_provider.lower() == "groq", "unsupported_provider")
    return GroqLLMClient(), config


def successful_call(observations, name):
    matches = [call for call in observations if call.name == name]
    require(bool(matches), f"missing_{name}")
    require(
        all(not call.is_error and isinstance(call.result, dict)
            and call.result.get("status") == "found" for call in matches),
        f"unsuccessful_{name}",
    )
    return matches[-1]


def assert_observed_sequence(response, observations, context):
    names = [call.name for call in observations]
    require(context.calls() == names, "mcp_dispatch_sequence_mismatch")
    require([record.tool_name for record in response.tool_calls] == names,
            "response_tool_sequence_mismatch")


def test_mismatched_employee_id_never_reaches_real_mcp(tmp_path):
    context = build_context(tmp_path)
    llm = ScriptedLLM([
        tool_completion("check_pto_balance", {"employee_id": "TEST-002"}, "mismatched-id")
    ])

    async def exercise():
        async with connect(context, "provided") as mcp:
            agent = await HRAgent.create(mcp, llm, AgentConfig())
            with pytest.raises(AgentRuntimeError, match="employee_id_mismatch"):
                await agent.process_request(
                    "Check the employee's PTO.", context={"employee_id": "TEST-001"}
                )
            assert context.calls() == []

    asyncio.run(exercise())


@pytest.mark.parametrize("provider", ["scripted", "live"])
def test_pto_workflow_uses_real_mcp_results_and_cited_policy(tmp_path, provider):
    llm, config = acceptance_client(provider, [
        tool_completion("lookup_employee_profile", {"employee_id": "TEST-001"}, "profile"),
        tool_completion("check_pto_balance", {"employee_id": "TEST-001"}, "pto"),
        tool_completion(
            "search_policy_documents",
            {"question": "PTO request dates hours manager", "k": 3},
            "policy",
        ),
        final_completion(
            "As of January 1, 2026, the available PTO balance is 40.0 hours. "
            "Request the dates and hours from your manager, who reviews the request."
        ),
    ])
    context = build_context(tmp_path)
    fixture = Path(__file__).parents[1] / "fixtures" / "mcp" / "f004-policies" / "hr-pto.md"
    shutil.copyfile(fixture, context.corpus / fixture.name)
    rebuild(context)

    async def exercise():
        async with connect(context, "provided") as mcp:
            agent = await HRAgent.create(mcp, llm, config)
            with observe_calls(mcp) as observations:
                response = await agent.process_request(
                    "Can TEST-001 request 8 hours of PTO on 2026-02-01?",
                    context={"employee_id": "TEST-001"},
                )
            require(response.status == "answered", "pto_status")
            assert_observed_sequence(response, observations, context)
            require(all(record.status == "success" for record in response.tool_calls),
                    "pto_tool_status")
            profile = successful_call(observations, "lookup_employee_profile")
            pto = successful_call(observations, "check_pto_balance")
            search = successful_call(observations, "search_policy_documents")
            require(all(call.arguments == {"employee_id": "TEST-001"} for call in observations
                        if call.name in {"lookup_employee_profile", "check_pto_balance"}),
                    "employee_arguments")
            require(isinstance(search.arguments.get("question"), str)
                    and bool(search.arguments["question"].strip()), "search_arguments")
            require(profile.result["employee"]["employee_id"] == "TEST-001", "profile_result")
            balance = pto.result["pto"]
            require(
                balance["employee_id"] == "TEST-001"
                and balance["available_hours"] == 40 and balance["as_of"] == "2026-01-01",
                "pto_result",
            )
            require(policy_citation_matches(response, observations, "HR-005"), "pto_citation")
            require(any(c.document_id == "HR-005" and c.section == "1. PTO Requests"
                        for c in response.citations), "pto_citation_section")
            require(all(call.name != "draft_hr_email" for call in observations),
                    "unexpected_draft")
            if provider == "scripted":
                require(all(
                    json.loads(llm.requests[index + 1]["messages"][-1]["content"]) == call.result
                    for index, call in enumerate(observations)
                ), "tool_result_propagation")
            require(any(event["event"] == "completion" and event.get("outcome") == "answered"
                        for event in response.operational_trace.events), "pto_completion")
            require(not any(event.get("disposition") for event in response.operational_trace.events),
                    "unexpected_pto_disposition")
            trace = json.dumps(response.operational_trace.events)
            require("TEST-001" not in trace and "Taylor Fixture" not in trace, "trace_privacy")
            try:
                assert_point_in_time_balance(
                    response.answer, balance["available_hours"], balance["as_of"]
                )
            except AssertionError:
                if provider == "live":
                    pytest.skip("INCONCLUSIVE: inspect the synthetic answer in memory.")
                raise
            if provider == "live":
                pytest.skip("INCONCLUSIVE: review the synthetic PTO guidance in memory.")

    asyncio.run(exercise())


@pytest.mark.parametrize("provider", ["scripted", "live"])
def test_guidance_without_explicit_draft_never_calls_draft_tool(tmp_path, provider):
    llm, config = acceptance_client(provider, [
        tool_completion(
            "search_policy_documents", {"question": "PTO request dates hours manager"}, "policy"
        ),
        final_completion("Request the proposed PTO dates and hours from your manager."),
    ])
    context = build_context(tmp_path)
    fixture = Path(__file__).parents[1] / "fixtures" / "mcp" / "f004-policies" / "hr-pto.md"
    shutil.copyfile(fixture, context.corpus / fixture.name)
    rebuild(context)

    async def exercise():
        async with connect(context, "provided") as mcp:
            agent = await HRAgent.create(mcp, llm, config)
            with observe_calls(mcp) as observations:
                response = await agent.process_request(
                    "What is the PTO request process? I plan to contact my manager."
                )
            assert_observed_sequence(response, observations, context)
            require(all(call.name != "draft_hr_email" for call in observations), "unexpected_draft")
            successful_call(observations, "search_policy_documents")
            require(response.status in {"answered", "partial"}, "guidance_status")
            require(bool(response.answer.strip()), "missing_guidance")
            require(policy_citation_matches(response, observations, "HR-005"), "pto_citation")
            if provider == "live":
                pytest.skip("INCONCLUSIVE: review the synthetic guidance in memory.")

    asyncio.run(exercise())


@pytest.mark.parametrize("provider", ["scripted", "live"])
def test_explicit_draft_uses_real_mcp_and_requires_confirmation(tmp_path, provider):
    llm, config = acceptance_client(provider, [
        tool_completion(
            "draft_hr_email",
            {"recipient_name": "Synthetic Manager", "purpose": "PTO request"},
            "draft",
        ),
    ])
    context = build_context(tmp_path)

    async def exercise():
        async with connect(context, "provided") as mcp:
            agent = await HRAgent.create(mcp, llm, config)
            with observe_calls(mcp) as observations:
                proposal = await agent.process_request(
                    "Please draft an email to Synthetic Manager about my PTO request."
                )
            assert_observed_sequence(proposal, observations, context)
            draft = successful_call(observations, "draft_hr_email")
            require(draft.arguments.get("recipient_name") == "Synthetic Manager", "draft_recipient")
            require(bool(draft.arguments.get("purpose")), "draft_purpose")
            require(proposal.status == "confirmation_required" and proposal.confirmation_required,
                    "draft_confirmation")
            require(
                bool(draft.result["draft"]["subject"])
                and bool(draft.result["draft"]["body"])
                and draft.result["draft"]["subject"] in proposal.answer
                and draft.result["draft"]["body"] in proposal.answer,
                "draft_result",
            )
            require("No email was sent" in proposal.answer, "draft_unsent")
            confirmed = await agent.confirm_action(
                proposal.action_id, True, {"pending_action": proposal.pending_action}
            )
            require(confirmed.status == "answered" and "No email was sent" in confirmed.answer,
                    "confirmed_draft_unsent")

    asyncio.run(exercise())


def test_diagnostic_observes_results_without_exposing_values():
    synthetic_value = "synthetic-private-diagnostic-value"
    result = {"status": "found", "employee": {"name": synthetic_value}}
    arguments = {"employee_id": synthetic_value}
    mcp = FakeMCPClient(results={"lookup_employee_profile": result})

    async def exercise():
        with observe_calls(mcp) as observations:
            await mcp.call("lookup_employee_profile", arguments)
        require(observations[0].arguments["employee_id"] == synthetic_value, "argument_capture")
        require(observations[0].result == result, "result_capture")
        arguments["employee_id"] = "changed"
        result["employee"]["name"] = "changed"
        require(observations[0].arguments["employee_id"] == synthetic_value
                and observations[0].result["employee"]["name"] == synthetic_value,
                "observation_snapshot")
        require(synthetic_value not in repr(observations), "observation_repr_privacy")

    asyncio.run(exercise())


def test_diagnostic_citation_requires_matching_returned_evidence():
    evidence = {
        "document_id": "HR-005", "title": "Synthetic PTO Policy", "section": "PTO",
        "snippet": "Request PTO from your manager.", "chunk_id": "pto-1",
    }
    citation = SimpleNamespace(source_type="policy_evidence", **evidence)
    response = SimpleNamespace(citations=[citation])
    mcp = FakeMCPClient(results={
        "search_policy_documents": {"status": "found", "evidence": [evidence]}
    })

    async def exercise():
        with observe_calls(mcp) as observations:
            await mcp.call("search_policy_documents", {"question": "PTO"})
        require(policy_citation_matches(response, observations, "HR-005"), "matching_citation")
        citation.snippet = "Unreturned policy text."
        require(not policy_citation_matches(response, observations, "HR-005"), "mismatched_citation")

    asyncio.run(exercise())


def test_diagnostic_records_failed_dispatch_without_result():
    mcp = FakeMCPClient(failures={"draft_hr_email": ClientError("transport_failure")})

    async def exercise():
        with observe_calls(mcp) as observations, pytest.raises(ClientError, match="transport_failure"):
            await mcp.call("draft_hr_email", {"purpose": "synthetic"})
        require(len(observations) == 1, "failed_call_recorded")
        require(observations[0].name == "draft_hr_email" and observations[0].is_error
                and observations[0].result is None, "failed_call_classification")

    asyncio.run(exercise())


@pytest.mark.parametrize("provider", ["scripted", "live"])
def test_remote_work_uses_real_mcp_results_and_records_human_review(tmp_path, provider):
    llm, config = acceptance_client(provider, [
        tool_completion("lookup_employee_profile", {"employee_id": "TEST-002"}, "profile"),
        tool_completion(
            "search_policy_documents",
            {"question": "remote work security and out-of-state approval", "k": 3},
            "policy",
        ),
        tool_completion(
            "check_policy_compliance",
            {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVAL_FACTS},
            "compliance",
        ),
        final_completion(
            "The current remote OR profile does not authorize the proposed location. "
            "The prior-approval check is compliant based on unverified caller-provided facts. "
            "Security policy describes requirements but not this employee's security posture. "
            "Please ask People Operations and IT to review eligibility.",
            final_disposition="human_review_recommended",
        ),
    ])
    context = build_context(tmp_path)
    fixture = Path(__file__).parents[1] / "fixtures" / "mcp" / "f004-policies" / "hr-security.md"
    shutil.copyfile(fixture, context.corpus / fixture.name)
    rebuild(context)

    async def exercise():
        async with connect(context, "provided") as mcp:
            agent = await HRAgent.create(mcp, llm, config)
            with observe_calls(mcp) as observations:
                response = await agent.process_request(
                    "Can TEST-002 work remotely in CA? Caller-provided approval facts: "
                    + json.dumps(APPROVAL_FACTS),
                    context={"employee_id": "TEST-002"},
                )
            require(response.status == "partial", "remote_status")
            assert_observed_sequence(response, observations, context)
            require(all(record.status == "success" for record in response.tool_calls),
                    "remote_tool_status")
            profile = successful_call(observations, "lookup_employee_profile")
            successful_call(observations, "search_policy_documents")
            compliance = successful_call(observations, "check_policy_compliance")
            require(all(call.arguments == {"employee_id": "TEST-002"} for call in observations
                        if call.name == "lookup_employee_profile"), "profile_arguments")
            require(
                profile.result["employee"]["employee_id"] == "TEST-002"
                and profile.result["employee"]["work_state"] == "OR"
                and profile.result["employee"]["work_arrangement"] == "remote",
                "profile_result",
            )
            require(
                all(call.arguments == {
                    "check_id": "out_of_state_prior_approval", "approval_facts": APPROVAL_FACTS
                } for call in observations if call.name == "check_policy_compliance"),
                "compliance_arguments",
            )
            require(compliance.result["conclusion"] == "compliant", "compliance_result")
            require(any("unauthenticated" in item.lower()
                        for item in compliance.result["limitations"]), "compliance_limitations")
            require(policy_citation_matches(response, observations, "HR-004"), "location_citation")
            require(policy_citation_matches(response, observations, "HR-006"), "security_citation")
            require(all(call.name != "draft_hr_email" for call in observations),
                    "unexpected_draft")
            if provider == "scripted":
                require(all(
                    json.loads(llm.requests[index + 1]["messages"][-1]["content"]) == call.result
                    for index, call in enumerate(observations)
                ), "tool_result_propagation")
            completion_events = [
                event for event in response.operational_trace.events
                if event["event"] == "completion"
            ]
            require(bool(completion_events), "missing_completion")
            require(all(event.get("disposition") == "human_review_recommended"
                        for event in completion_events), "remote_disposition")
            trace = json.dumps(response.operational_trace.events)
            require(all(value not in trace for value in (
                "TEST-002", "Jordan Fixture", "2026-01-01T10:00:00Z"
            )), "trace_privacy")
            if provider == "scripted":
                require("The current remote OR profile does not authorize" in response.answer
                        and "unverified caller-provided facts" in response.answer
                            and "not this employee's security posture" in response.answer
                        and "ask People Operations and IT" in response.answer,
                        "remote_answer")
            else:
                pytest.skip("INCONCLUSIVE: review the synthetic remote-work answer in memory.")

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "scenario",
    [
        test_pto_workflow_uses_real_mcp_results_and_cited_policy,
        test_remote_work_uses_real_mcp_results_and_records_human_review,
        test_guidance_without_explicit_draft_never_calls_draft_tool,
    ],
)
def test_live_diagnostic_requires_manual_review_without_calling_provider(
    tmp_path, monkeypatch, scenario
):
    monkeypatch.setattr(
        sys.modules[__name__],
        "acceptance_client",
        lambda provider, completions: (ScriptedLLM(completions), AgentConfig()),
    )
    with pytest.raises(pytest.skip.Exception, match="INCONCLUSIVE"):
        scenario(tmp_path, "live")


def test_live_pto_unrecognized_wording_is_inconclusive_offline(tmp_path, monkeypatch):
    def scripted_client(provider, completions):
        completions[-1] = final_completion(
            "The available PTO balance is 40 hours as of 01-01-2026."
        )
        return ScriptedLLM(completions), AgentConfig()

    monkeypatch.setattr(sys.modules[__name__], "acceptance_client", scripted_client)
    with pytest.raises(pytest.skip.Exception, match="inspect the synthetic answer"):
        test_pto_workflow_uses_real_mcp_results_and_cited_policy(tmp_path, "live")
