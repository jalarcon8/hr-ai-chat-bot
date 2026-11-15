"""Validated MCP inputs, result envelopes, errors, and trace events."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from typing import Annotated, Literal, Self
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

NonBlank = Annotated[str, StringConstraints(strict=True, min_length=1, pattern=r"\S")]
_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:[0-5]\d"
    r"(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchInput(StrictModel):
    question: NonBlank
    k: Annotated[StrictInt, Field(gt=0)] = 5


class SectionInput(StrictModel):
    document_id: NonBlank
    section: NonBlank


class EmployeeInput(StrictModel):
    employee_id: NonBlank


class ApprovalFacts(StrictModel):
    status: Literal["approved", "not_approved", "unknown"] | None = None
    authority: Literal["people_operations", "other", "unknown"] | None = None
    format: Literal["written", "verbal", "unknown"] | None = None
    approval_timestamp: str | None = None
    travel_start_timestamp: str | None = None
    no_other_approvals: StrictBool | None = None

    @field_validator("approval_timestamp", "travel_start_timestamp")
    @classmethod
    def validate_timestamp(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _TIMESTAMP.fullmatch(value) or value.endswith("-00:00"):
            raise ValueError("timestamp must be RFC 3339 with a known offset")
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("timestamp must contain a valid date and time") from exc
        return value

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if self.status == "not_approved" and (
            self.authority not in (None, "unknown")
            or self.format not in (None, "unknown")
            or self.approval_timestamp is not None
            or self.no_other_approvals is False
        ):
            raise ValueError("not_approved conflicts with the supplied approval facts")
        return self


class ComplianceInput(StrictModel):
    check_id: Literal["out_of_state_prior_approval"]
    approval_facts: ApprovalFacts | None = None


class DraftInput(StrictModel):
    recipient_name: NonBlank
    purpose: NonBlank
    supporting_details: str = ""


class PolicyEvidence(StrictModel):
    document_id: NonBlank
    title: NonBlank
    section: str | None
    snippet: str
    chunk_id: NonBlank
    generation_id: NonBlank


class RankedPolicyEvidence(PolicyEvidence):
    score: float


class Employee(StrictModel):
    employee_id: NonBlank
    name: NonBlank
    role: NonBlank
    department: NonBlank
    work_arrangement: Literal["office", "hybrid", "remote"]
    work_state: NonBlank


class PTORecord(StrictModel):
    employee_id: NonBlank
    available_hours: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    as_of: str

    @field_validator("as_of")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("as_of must be an ISO 8601 calendar date") from exc
        if parsed.isoformat() != value:
            raise ValueError("as_of must use YYYY-MM-DD")
        return value


class SearchFound(StrictModel):
    status: Literal["found"] = "found"
    evidence_kind: Literal["candidate"] = "candidate"
    evidence: Annotated[list[RankedPolicyEvidence], Field(min_length=1)]
    generation_id: NonBlank


class SectionFound(StrictModel):
    status: Literal["found"] = "found"
    evidence: Annotated[list[PolicyEvidence], Field(min_length=1)]
    generation_id: NonBlank


class EvidenceNotFound(StrictModel):
    status: Literal["not_found"] = "not_found"
    evidence: Annotated[list[PolicyEvidence], Field(max_length=0)] = Field(default_factory=list)
    generation_id: NonBlank


class EmployeeFound(StrictModel):
    status: Literal["found"] = "found"
    employee: Employee


class PTOFound(StrictModel):
    status: Literal["found"] = "found"
    pto: PTORecord


class RecordNotFound(StrictModel):
    status: Literal["not_found"] = "not_found"
    missing: Literal["employee", "pto"]


class ComplianceResult(StrictModel):
    status: Literal["found", "indeterminate"]
    check_id: Literal["out_of_state_prior_approval"] = "out_of_state_prior_approval"
    conclusion: Literal["compliant", "noncompliant", "indeterminate"]
    evidence: list[PolicyEvidence]
    limitations: Annotated[list[NonBlank], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_outcome(self) -> Self:
        if self.conclusion == "indeterminate":
            if self.status != "indeterminate":
                raise ValueError("indeterminate conclusion requires indeterminate status")
        elif self.status != "found" or not self.evidence:
            raise ValueError("definitive conclusion requires found status and evidence")
        return self


class Draft(StrictModel):
    subject: str
    body: str


class DraftFound(StrictModel):
    status: Literal["found"] = "found"
    draft: Draft


class ErrorDetails(StrictModel):
    classification: Literal["INVALID_ARGUMENT", "OPERATIONAL_ERROR", "UNKNOWN_ERROR"]
    origin: Literal["input_validation", "tool_execution", "trace_persistence", "request_adapter"]
    code: Literal[
        "invalid_argument",
        "index_unavailable",
        "embedding_failure",
        "data_unavailable",
        "trace_persistence_failure",
        "internal_error",
    ]

    @model_validator(mode="after")
    def validate_combination(self) -> Self:
        known = {
            ("INVALID_ARGUMENT", "input_validation", "invalid_argument"),
            ("OPERATIONAL_ERROR", "tool_execution", "index_unavailable"),
            ("OPERATIONAL_ERROR", "tool_execution", "embedding_failure"),
            ("OPERATIONAL_ERROR", "tool_execution", "data_unavailable"),
            ("OPERATIONAL_ERROR", "trace_persistence", "trace_persistence_failure"),
            ("UNKNOWN_ERROR", "tool_execution", "internal_error"),
            ("UNKNOWN_ERROR", "request_adapter", "internal_error"),
        }
        if (self.classification, self.origin, self.code) not in known:
            raise ValueError("invalid error classification, origin, and code combination")
        return self


class ErrorEnvelope(StrictModel):
    error: ErrorDetails


class UnclassifiedError(StrictModel):
    classification: Literal["UNCLASSIFIED_ERROR"] = "UNCLASSIFIED_ERROR"
    origin: None = None
    code: Literal["unclassified_error"] = "unclassified_error"


class TraceEvent(StrictModel):
    invocation_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    component: Literal["server", "client"]
    event_type: Literal["discovery", "tool_call"]
    tool: str | None
    outcome: str
    classification: Literal[
        "INVALID_ARGUMENT", "OPERATIONAL_ERROR", "UNKNOWN_ERROR", "UNCLASSIFIED_ERROR"
    ] | None = None
    argument_names: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
