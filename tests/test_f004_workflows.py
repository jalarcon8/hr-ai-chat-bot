import asyncio
import json
import re
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

import pytest

from hr_agent.agent import HRAgent
from hr_agent.config import AgentConfig
from hr_agent.errors import AgentRuntimeError
from hr_mcp.client import ClientError
from tests.unit.agent_orchestration_helpers import (
    POLICY_EVIDENCE,
    FakeMCPClient,
    ScriptedLLM,
    final_completion,
    policy_result,
    tool_completion,
)

PTO_EVIDENCE = {
    "document_id": "HR-005",
    "title": "Synthetic PTO Policy",
    "section": "1. PTO Requests",
    "snippet": (
        "Employees should request PTO from their manager with the proposed dates and hours."
    ),
    "chunk_id": "hr-005-pto-1",
    "generation_id": "fixture-generation",
}


def assert_point_in_time_balance(answer, hours, as_of):
    date_pattern = (
        r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|"
        r"[A-Za-z]+\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})"
    )
    label = r"(?:available\s+(?:PTO\s+)?balance|PTO\s+balance)"
    value = r"(?<![\d.-])(?P<hours>\d+(?:\.\d+)?)(?![\d.])"
    units = r"(?:hours?\b|hrs?\.?(?!\w))"
    amount = rf"{value}\s+(?:available\s+)?(?:PTO\s+)?{units}"
    labelled_amount = rf"{label}\s*(?:is\b|of\b|:|=)\s*{amount}"
    as_of_date = rf"as\s+of\s+(?P<date>{date_pattern})(?![\w/-])"
    patterns = (
        (
            rf"\b{as_of_date}\s*,?\s*(?:(?:the|your)\s+)?"
            rf"{labelled_amount}(?=\s*(?:[.!?;,\n]|$))"
        ),
        (
            rf"\b{label}\s+{as_of_date}\s*(?:is\b|:|=)\s*"
            rf"{amount}(?=\s*(?:[.!?;,\n]|$))"
        ),
        rf"\b{labelled_amount}(?:\s+available)?\s*[,;(]?\s*{as_of_date}",
        rf"{amount}\s+(?:available|of\s+available\s+PTO)\s*[,;(]?\s*{as_of_date}",
    )
    expected_date = date.fromisoformat(as_of)
    for pattern in patterns:
        for match in re.finditer(pattern, answer, re.IGNORECASE):
            preceding = answer[max(0, match.start() - 24):match.start()]
            if re.search(r"\b(?:not|no|never)\s+$", preceding, re.IGNORECASE):
                continue
            reported_date = match.group("date")
            try:
                if "-" in reported_date:
                    parsed_date = date.fromisoformat(reported_date)
                elif "/" in reported_date:
                    parsed_date = datetime.strptime(reported_date, "%m/%d/%Y").date()
                else:
                    normalized = re.sub(
                        r"(?<=\d)(?:st|nd|rd|th)\b", "", reported_date, flags=re.IGNORECASE
                    ).replace(".", "").replace(",", "")
                    date_format = "%b %d %Y" if len(normalized.split()[0]) == 3 else "%B %d %Y"
                    parsed_date = datetime.strptime(normalized, date_format).date()
            except ValueError:
                continue
            if Decimal(match.group("hours")) == Decimal(str(hours)) and parsed_date == expected_date:
                return
    raise AssertionError("The available balance and its as-of date were not reported together.")


def employee_result(employee_id):
    return {
        "status": "found",
        "employee": {
            "employee_id": employee_id,
            "name": "Synthetic Employee",
            "role": "Analyst",
            "department": "Operations",
            "work_arrangement": "hybrid",
            "work_state": "CA",
        },
    }


def pto_result(employee_id, hours):
    if hours is None:
        return {"status": "not_found", "missing": "pto"}
    return {
        "status": "found",
        "pto": {
            "employee_id": employee_id,
            "available_hours": hours,
            "as_of": "2026-01-01",
        },
    }


def workflow_completions(employee_id, answer):
    return [
        tool_completion("lookup_employee_profile", {"employee_id": employee_id}, "profile"),
        tool_completion("check_pto_balance", {"employee_id": employee_id}, "balance"),
        tool_completion("search_policy_documents", {"question": "PTO request policy"}, "policy"),
        final_completion(answer),
    ]


@pytest.mark.parametrize(
    ("employee_id", "hours", "answer", "expected_status"),
    [
        (
            "TEST-001",
            40,
            (
                "The available balance is 40 hours as of 2026-01-01. Request the dates and "
                "hours from your manager; the manager reviews the request."
            ),
            "answered",
        ),
        (
            "TEST-001",
            40,
            (
                "The available balance is 40.0 PTO hours available as of January 1, 2026. "
                "Request the dates and hours from your manager; the manager reviews the request."
            ),
            "answered",
        ),
        (
            "TEST-002",
            None,
            "The PTO balance is unavailable, not zero. Contact People Operations for review.",
            "partial",
        ),
        (
            "TEST-003",
            0,
            (
                "The available balance is 0 hours as of 2026-01-01. Contact People Operations "
                "about the requested hours."
            ),
            "answered",
        ),
    ],
)
def test_pto_workflow_grounds_profile_balance_and_policy(
    employee_id, hours, answer, expected_status
):
    results = {
        "lookup_employee_profile": employee_result(employee_id),
        "check_pto_balance": pto_result(employee_id, hours),
        "search_policy_documents": policy_result([PTO_EVIDENCE]),
    }
    llm = ScriptedLLM(workflow_completions(employee_id, answer))
    mcp = FakeMCPClient(results=results)

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            f"Can {employee_id} request 8 hours of PTO on 2026-02-01?",
            context={"employee_id": employee_id},
        )

        assert response.status == expected_status
        if hours is None:
            assert response.answer.startswith(answer)
        assert any(c.document_id == "HR-005" and c.snippet == PTO_EVIDENCE["snippet"]
                   for c in response.citations)
        assert [name for name, _ in mcp.calls] == [
            "lookup_employee_profile", "check_pto_balance", "search_policy_documents"
        ]
        for index, name in enumerate(
            ("lookup_employee_profile", "check_pto_balance", "search_policy_documents"), start=1
        ):
            assert json.loads(llm.requests[index]["messages"][-1]["content"]) == results[name]
        events = response.operational_trace.events
        tool_events = [event for event in events if event["event"] == "tool_call"]
        assert [event["tool"] for event in tool_events] == [name for name, _ in mcp.calls]
        assert all("argument_names" in event["arguments_summary"] for event in tool_events)
        assert all("outcome" in event["result_summary"] for event in tool_events)
        assert {"document_id": "HR-005"} in tool_events[-1]["source_refs"]
        assert events[-1]["answer_basis"] == "tool_evidence"
        trace = json.dumps(events)
        assert employee_id not in trace
        assert "Synthetic Employee" not in trace
        assert answer not in trace
        assert all(record.tool_name != "draft_hr_email" for record in response.tool_calls)
        assert all(word not in response.answer.lower()
                   for word in ("submitted", "approved", "projected balance"))
        if hours is None:
            assert response.tool_calls[1].status == "not_found"
            assert "unavailable" in response.answer
        else:
            assert response.tool_calls[1].status == "success"
            assert_point_in_time_balance(response.answer, hours, "2026-01-01")
            if hours == 40:
                assert all(term in response.answer.lower()
                           for term in ("request", "dates", "hours", "manager"))
            else:
                assert "People Operations" in response.answer

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (
            "The available PTO balance is 40 hours as of 2026-01-01.",
            True,
        ),
        ("As of 2026-01-01, the available PTO balance is 40 hours.", True),
        ("The available PTO balance is 40 hours (as of January 1, 2026).", True),
        ("Your PTO balance as of Jan 1, 2026 is 40.00 hrs.", True),
        ("Your PTO balance as of January 1st, 2026 is 40 available PTO hours.", True),
        ("As of 01/01/2026, the available balance is 40.0 hours.", True),
        ("40.0 PTO hours available as of 2026-01-01.", True),
        ("40 hours of available PTO as of 01/01/2026.", True),
        ("The available PTO balance is 8 hours as of 2026-01-01.", False),
        ("The available PTO balance is -40 hours as of 2026-01-01.", False),
        ("The available PTO balance is 40 hours as of 2026-02-01.", False),
        ("The available PTO balance is 40 hours as of 2026-01-010.", False),
        ("The available PTO balance is 40 hours as of January 32, 2026.", False),
        ("The available PTO balance is 40 as of 2026-01-01.", False),
        ("The available PTO balance is 40 days as of 2026-01-01.", False),
        ("The available PTO balance is 40 hours.", False),
        ("The available PTO balance is not 40 hours as of 2026-01-01.", False),
        ("There are not 40 PTO hours available as of 2026-01-01.", False),
        ("As of 2026-01-01, the available balance is 40 hours more than before.", False),
        (
            (
                "You requested 40 hours as of 2026-01-01; your available balance is 8 hours "
                "as of 2026-01-01."
            ),
            False,
        ),
        (
            "As of 2026-01-01, your request is open. The available PTO balance is 40 hours.",
            False,
        ),
        (
            (
                "The request is for 8 hours as of 2026-01-01; "
                "the available PTO balance is 40 hours as of 2026-02-01."
            ),
            False,
        ),
    ],
)
def test_pto_balance_assertion_distinguishes_valid_and_invalid_wording(answer, expected):
    if expected:
        assert_point_in_time_balance(answer, 40, "2026-01-01")
    else:
        with pytest.raises(AssertionError):
            assert_point_in_time_balance(answer, 40, "2026-01-01")


@pytest.mark.parametrize(
    ("user_request", "tool"),
    [
        ("Can I use PTO?", "check_pto_balance"),
        ("Can Jordan use PTO? The employee identity is ambiguous.", "lookup_employee_profile"),
        ("Can employee J use PTO? The identifier is ambiguous.", "check_pto_balance"),
    ],
)
def test_pto_missing_or_ambiguous_identity_requests_id_without_lookup(user_request, tool):
    llm = ScriptedLLM([tool_completion(tool, {}, "missing-id")])
    mcp = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(user_request)
        assert response.status == "clarification_needed"
        assert "employee identifier" in response.clarification_prompt
        assert not mcp.calls
        assert not response.citations

    asyncio.run(exercise())


@pytest.mark.parametrize("search_first", [False, True])
def test_final_identity_signal_requests_id_without_employee_claims(search_first):
    completions = []
    if search_first:
        completions.append(
            tool_completion("search_policy_documents", {"question": "PTO policy"}, "policy")
        )
    completions.append(final_completion(
        "Invented employee information must not be shown.",
        clarification_needed="employee_id",
    ))
    mcp = FakeMCPClient(results={"search_policy_documents": policy_result([PTO_EVIDENCE])})
    llm = ScriptedLLM(completions)

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("Can Jordan use PTO? The identity is ambiguous.")
        assert response.status == "clarification_needed"
        assert "employee identifier" in response.clarification_prompt
        assert response.answer == response.clarification_prompt
        assert "Invented" not in response.answer
        assert [name for name, _ in mcp.calls] == (
            ["search_policy_documents"] if search_first else []
        )

    asyncio.run(exercise())


def test_final_answer_without_evidence_or_clarification_remains_error():
    async def exercise():
        agent = await HRAgent.create(
            FakeMCPClient(), ScriptedLLM([final_completion("Unsupported claim.")]), AgentConfig()
        )
        response = await agent.process_request("Can Jordan use PTO?")
        assert response.status == "error"
        assert response.error_code == "missing_policy_evidence"
        assert "Unsupported claim" not in response.answer

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "completion",
    [
        final_completion("Please clarify.", clarification_needed="other"),
        final_completion(
            "Please clarify.",
            clarification_needed="employee_id",
            final_disposition="human_review_recommended",
        ),
        replace(
            tool_completion("lookup_employee_profile", {"employee_id": "TEST-001"}, "profile"),
            clarification_needed="employee_id",
        ),
    ],
)
def test_invalid_or_contradictory_clarification_is_rejected(completion):
    async def exercise():
        mcp = FakeMCPClient()
        agent = await HRAgent.create(mcp, ScriptedLLM([completion]), AgentConfig())
        with pytest.raises(AgentRuntimeError, match="invalid_clarification"):
            await agent.process_request("Can Jordan use PTO?")
        assert not mcp.calls

    asyncio.run(exercise())


def test_failed_tool_is_not_hidden_by_final_identity_clarification():
    llm = ScriptedLLM([
        tool_completion("search_policy_documents", {"question": "PTO policy"}, "policy"),
        final_completion("Please provide an ID.", clarification_needed="employee_id"),
    ])
    mcp = FakeMCPClient(failures={"search_policy_documents": ClientError("transport_failure")})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("Can Jordan use PTO?")
        assert response.status == "error"
        assert response.error_code == "transport_failure"

    asyncio.run(exercise())


@pytest.mark.parametrize("missing", ["dates", "hours"])
def test_pto_missing_request_details_are_asked_for(missing):
    employee_id = "TEST-001"
    answer = f"Please provide the requested PTO {missing} before comparing the request."
    llm = ScriptedLLM(workflow_completions(employee_id, answer))
    mcp = FakeMCPClient(results={
        "lookup_employee_profile": employee_result(employee_id),
        "check_pto_balance": pto_result(employee_id, 40),
        "search_policy_documents": policy_result([PTO_EVIDENCE]),
    })

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            f"Check PTO for {employee_id}; {missing} missing.", context={"employee_id": employee_id}
        )
        assert answer in response.answer
        assert "draft_hr_email" not in [name for name, _ in mcp.calls]

    asyncio.run(exercise())


def test_pto_unavailable_tool_is_not_reported_as_success():
    llm = ScriptedLLM([
        tool_completion("check_pto_balance", {"employee_id": "TEST-001"}, "pto-failure"),
        final_completion("The PTO balance is unavailable."),
    ])
    mcp = FakeMCPClient(failures={"check_pto_balance": ClientError("transport_failure")})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            "Check PTO for TEST-001.", context={"employee_id": "TEST-001"}
        )
        assert response.status == "error"
        assert response.tool_calls[0].status == "error"
        assert response.error_code
        assert "unavailable" in response.answer

    asyncio.run(exercise())


def test_pto_insufficient_policy_evidence_escalates_without_exception():
    llm = ScriptedLLM([
        tool_completion("search_policy_documents", {"question": "PTO exception"}, "policy"),
        final_completion("The policy evidence is insufficient. Ask People Operations to review."),
    ])
    mcp = FakeMCPClient(results={"search_policy_documents": policy_result([])})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("Is a PTO exception available?")
        assert response.status == "partial"
        assert response.evidence_limitations
        assert "People Operations" in response.answer
        assert "approved" not in response.answer.lower()
        assert not response.citations

    asyncio.run(exercise())


def test_pto_explicit_manager_draft_requires_confirmation_and_is_unsent():
    llm = ScriptedLLM([
        tool_completion(
            "draft_hr_email",
            {"recipient_name": "Synthetic Manager", "purpose": "PTO request"},
            "pto-draft",
        ),
    ])
    mcp = FakeMCPClient(results={
        "draft_hr_email": {
            "status": "found",
            "draft": {"subject": "PTO request", "body": "Please review my PTO request."},
        },
    })

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        proposal = await agent.process_request(
            "Please draft an email to Synthetic Manager about my PTO request."
        )
        assert proposal.status == "confirmation_required"
        assert "No email was sent" in proposal.answer
        confirmed = await agent.confirm_action(
            proposal.action_id, True, {"pending_action": proposal.pending_action}
        )
        assert confirmed.status == "answered"
        assert "No email was sent" in confirmed.answer
        assert [name for name, _ in mcp.calls] == ["draft_hr_email"]
        assert "submitted" not in confirmed.answer.lower()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "arguments",
    [{"purpose": "PTO request"}, {"recipient_name": "Synthetic Manager"}],
)
def test_pto_draft_missing_details_are_requested_before_tool_call(arguments):
    llm = ScriptedLLM([tool_completion("draft_hr_email", arguments, "draft-details")])
    mcp = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("Please draft a PTO email.")
        assert response.status == "clarification_needed"
        assert response.clarification_prompt
        assert not mcp.calls

    asyncio.run(exercise())


def test_pto_guidance_is_in_the_model_contract():
    llm = ScriptedLLM([tool_completion("check_pto_balance", {}, "missing-id")])
    mcp = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        await agent.process_request("Can I use PTO?")
        prompt = llm.requests[0]["messages"][0]["content"].lower()
        for requirement in (
            "ambiguous", "employee id", "as_of", "not zero", "not a projected balance",
            "dates or hours", "only when explicitly requested",
        ):
            assert requirement in prompt

    asyncio.run(exercise())


SECURITY_EVIDENCE = {
    "document_id": "HR-006",
    "title": "Synthetic Remote Work Security Policy",
    "section": "1. Remote Work Security",
    "snippet": "Remote workers should use a company-managed device and a secure network.",
    "chunk_id": "hr-006-security-1",
    "generation_id": "fixture-generation",
}

APPROVAL_FACTS = {
    "status": "approved",
    "authority": "people_operations",
    "format": "written",
    "approval_timestamp": "2026-01-01T10:00:00Z",
    "travel_start_timestamp": "2026-01-02T10:00:00Z",
}


def remote_profile():
    result = employee_result("TEST-002")
    result["employee"]["work_arrangement"] = "remote"
    result["employee"]["work_state"] = "OR"
    return result


@pytest.mark.parametrize(
    ("facts", "conclusion", "result_status"),
    [
        (APPROVAL_FACTS, "compliant", "found"),
        ({"status": "approved"}, "indeterminate", "indeterminate"),
    ],
)
def test_remote_work_uses_caller_facts_without_claiming_overall_eligibility(
    facts, conclusion, result_status
):
    profile = remote_profile()
    evidence = policy_result([POLICY_EVIDENCE, SECURITY_EVIDENCE])
    compliance = {
        "status": result_status,
        "check_id": "out_of_state_prior_approval",
        "conclusion": conclusion,
        "evidence": [POLICY_EVIDENCE],
        "limitations": ["Caller-provided approval facts are unauthenticated."],
    }
    answer = (
        f"TEST-002's current profile is remote in OR, not authorization for the proposed state. "
        f"The prior-approval check is {conclusion} based on caller-provided, unverified facts. "
        "Policy requires a managed device and secure network, but the employee's security "
        "posture is unknown. Please ask People Operations and IT to review eligibility."
    )
    llm = ScriptedLLM([
        tool_completion("lookup_employee_profile", {"employee_id": "TEST-002"}, "remote-profile"),
        tool_completion(
            "search_policy_documents", {"question": "remote location and security"}, "remote-policy"
        ),
        tool_completion(
            "check_policy_compliance",
            {"check_id": "out_of_state_prior_approval", "approval_facts": facts},
            "remote-compliance",
        ),
        final_completion(answer, final_disposition="human_review_recommended"),
    ])
    mcp = FakeMCPClient(results={
        "lookup_employee_profile": profile,
        "search_policy_documents": evidence,
        "check_policy_compliance": compliance,
    })

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            "For TEST-002, can remote work in CA be approved? "
            f"The caller provides these approval facts: {json.dumps(facts)}.",
            context={"employee_id": "TEST-002"},
        )
        assert response.status == "partial"
        assert response.answer.startswith(answer)
        assert {c.document_id for c in response.citations} >= {"HR-004", "HR-006"}
        assert mcp.calls[2] == (
            "check_policy_compliance",
            {"check_id": "out_of_state_prior_approval", "approval_facts": facts},
        )
        assert json.loads(llm.requests[1]["messages"][-1]["content"]) == profile
        assert json.loads(llm.requests[2]["messages"][-1]["content"]) == evidence
        assert json.loads(llm.requests[3]["messages"][-1]["content"]) == compliance
        assert response.tool_calls[2].status == (
            "success" if result_status == "found" else "indeterminate"
        )
        completions = [e for e in response.operational_trace.events if e["event"] == "completion"]
        assert completions
        assert all(e.get("disposition") == "human_review_recommended" for e in completions)
        events = response.operational_trace.events
        tool_events = [event for event in events if event["event"] == "tool_call"]
        assert [event["tool"] for event in tool_events] == [name for name, _ in mcp.calls]
        assert all("argument_names" in event["arguments_summary"] for event in tool_events)
        assert all("outcome" in event["result_summary"] for event in tool_events)
        assert {ref["document_id"] for ref in tool_events[1]["source_refs"]} == {"HR-004", "HR-006"}
        assert events[-1]["answer_basis"] == "tool_evidence"
        trace = json.dumps(events)
        assert "TEST-002" not in trace
        assert "Synthetic Employee" not in trace
        assert "2026-01-01T10:00:00Z" not in trace
        assert answer not in trace

    asyncio.run(exercise())


def test_international_work_uses_cited_policy_and_human_review_not_prior_approval_check():
    answer = (
        "The current remote profile is not approval for international work. "
        "The available location and security evidence does not establish eligibility. "
        "Please ask People Operations to review the request."
    )
    llm = ScriptedLLM([
        tool_completion("lookup_employee_profile", {"employee_id": "TEST-002"}, "intl-profile"),
        tool_completion(
            "search_policy_documents", {"question": "remote work and security"}, "intl-policy"
        ),
        final_completion(answer, final_disposition="human_review_recommended"),
    ])
    mcp = FakeMCPClient(results={
        "lookup_employee_profile": remote_profile(),
        "search_policy_documents": policy_result([POLICY_EVIDENCE, SECURITY_EVIDENCE]),
    })

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            "Can TEST-002 work remotely from another country?", context={"employee_id": "TEST-002"}
        )
        assert response.status == "partial"
        assert "People Operations" in response.answer
        assert "does not establish eligibility" in response.answer
        assert {c.document_id for c in response.citations} >= {"HR-004", "HR-006"}
        assert "check_policy_compliance" not in [name for name, _ in mcp.calls]
        assert any(
            event.get("disposition") == "human_review_recommended"
            for event in response.operational_trace.events
        )

    asyncio.run(exercise())


def test_remote_work_surfaces_policy_tool_failure():
    llm = ScriptedLLM([
        tool_completion("search_policy_documents", {"question": "remote policy"}, "policy-failure"),
        final_completion("Remote-work policy evidence is unavailable."),
    ])
    mcp = FakeMCPClient(failures={"search_policy_documents": ClientError("transport_failure")})

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request("What is the remote-work policy?")
        assert response.status == "error"
        assert response.tool_calls[0].status == "error"
        assert response.error_code
        assert "unavailable" in response.answer
        assert not response.citations

    asyncio.run(exercise())


def test_remote_work_surfaces_compliance_failure_after_policy_evidence():
    llm = ScriptedLLM([
        tool_completion("search_policy_documents", {"question": "remote policy"}, "policy"),
        tool_completion(
            "check_policy_compliance",
            {"check_id": "out_of_state_prior_approval", "approval_facts": APPROVAL_FACTS},
            "compliance-failure",
        ),
        final_completion("The prior-approval check failed; ask People Operations to review."),
    ])
    mcp = FakeMCPClient(
        results={"search_policy_documents": policy_result([POLICY_EVIDENCE])},
        failures={"check_policy_compliance": ClientError("transport_failure")},
    )

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        response = await agent.process_request(
            "Check out-of-state approval using these facts: " + json.dumps(APPROVAL_FACTS)
        )
        assert response.status == "partial"
        assert response.citations
        assert response.tool_calls[1].status == "error"
        assert "failed" in response.evidence_limitations
        assert "compliant" not in response.answer.lower()

    asyncio.run(exercise())


def test_remote_work_guidance_is_in_the_model_contract():
    llm = ScriptedLLM([tool_completion("lookup_employee_profile", {}, "missing-id")])
    mcp = FakeMCPClient()

    async def exercise():
        agent = await HRAgent.create(mcp, llm, AgentConfig())
        await agent.process_request("Can I work remotely?")
        prompt = llm.requests[0]["messages"][0]["content"].lower()
        for requirement in (
            "current work state", "not authorization", "out_of_state_prior_approval",
            "caller-provided", "unverified", "international", "security posture",
        ):
            assert requirement in prompt

    asyncio.run(exercise())
