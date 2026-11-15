import pytest
from pydantic import ValidationError

from hr_mcp.models import (
    ApprovalFacts,
    ComplianceInput,
    DraftInput,
    ErrorDetails,
    SearchInput,
    SectionInput,
)


@pytest.mark.parametrize(
    "values",
    [
        {"question": ""},
        {"question": " \n "},
        {"question": "policy", "k": 0},
        {"question": "policy", "k": True},
        {"question": "policy", "extra": 1},
    ],
)
def test_search_rejects_invalid_arguments(values):
    with pytest.raises(ValidationError):
        SearchInput.model_validate(values)


def test_search_default_and_required_strings():
    assert SearchInput(question="policy").k == 5
    with pytest.raises(ValidationError):
        SectionInput(document_id="HR-004", section=" ")
    with pytest.raises(ValidationError):
        DraftInput(recipient_name="Alex", purpose="PTO", supporting_details=3)
    with pytest.raises(ValidationError):
        DraftInput.model_validate(
            {"recipient_name": "Alex", "purpose": "PTO", "supporting_details": None}
        )


@pytest.mark.parametrize(
    "facts",
    [
        {"approval_timestamp": "2026-01-01T10:00:00-00:00"},
        {"approval_timestamp": "2026-01-01T10:00:00+01:99"},
        {"travel_start_timestamp": "2026-01-01T10:00:00.1234567Z"},
        {"no_other_approvals": 1},
        {"status": "not_approved", "approval_timestamp": "2026-01-01T10:00:00Z"},
        {"status": "not_approved", "authority": "people_operations"},
        {"status": "not_approved", "no_other_approvals": False},
        {"unknown": "value"},
    ],
)
def test_invalid_approval_facts_are_rejected(facts):
    with pytest.raises(ValidationError):
        ApprovalFacts.model_validate(facts)


def test_valid_approval_facts_and_old_argument():
    facts = ApprovalFacts.model_validate(
        {
            "status": "approved",
            "approval_timestamp": "2026-01-01T10:00:00.123456+05:30",
            "no_other_approvals": False,
        }
    )
    assert facts.status == "approved"
    with pytest.raises(ValidationError):
        ComplianceInput.model_validate(
            {"check_id": "out_of_state_prior_approval", "approval_status": "approved"}
        )


def test_error_details_reject_mismatched_classification_and_origin():
    with pytest.raises(ValidationError):
        ErrorDetails(
            classification="INVALID_ARGUMENT",
            origin="tool_execution",
            code="invalid_argument",
        )
