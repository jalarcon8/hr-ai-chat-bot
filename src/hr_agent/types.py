"""Typed request, response, trace, and LLM boundary structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import uuid4

from .config import AgentConfig

AgentStatus = Literal[
    "answered",
    "partial",
    "clarification_needed",
    "confirmation_required",
    "out_of_scope",
    "error",
]
ToolCallStatus = Literal["success", "not_found", "indeterminate", "error", "timeout"]


@dataclass(frozen=True)
class LLMToolCall:
    call_id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMCompletion:
    content: str | None
    tool_call: LLMToolCall | None
    assistant_message: dict[str, Any]
    final_disposition: Literal["human_review_recommended"] | None = None
    clarification_needed: Literal["employee_id"] | None = None


class LLMClient(Protocol):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        config: AgentConfig,
    ) -> LLMCompletion: ...


@dataclass(frozen=True)
class Citation:
    source_type: Literal["policy_evidence", "tool_result"]
    source_id: str
    document_id: str
    title: str
    section: str | None
    snippet: str
    claim: str = ""
    chunk_id: str = ""


@dataclass(frozen=True)
class ToolInvocationRecord:
    tool_name: str
    status: ToolCallStatus
    arguments_summary: dict[str, Any]
    result_summary: dict[str, Any]
    duration_ms: float
    error_code: str | None = None


@dataclass
class OperationalTrace:
    events: list[dict[str, Any]] = field(default_factory=list)
    request_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class AgentResponse:
    answer: str
    status: AgentStatus
    citations: list[Citation] = field(default_factory=list)
    evidence_limitations: str = ""
    tool_calls: list[ToolInvocationRecord] = field(default_factory=list)
    operational_trace: OperationalTrace = field(default_factory=OperationalTrace)
    clarification_prompt: str | None = None
    confirmation_required: bool = False
    confirmation_prompt: str | None = None
    action_id: str | None = None
    pending_action: dict[str, Any] | None = None
    error_code: str | None = None
