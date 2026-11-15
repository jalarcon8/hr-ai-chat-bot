"""Pure fictional HR operations."""

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    StringConstraints,
    ValidationError,
    field_validator,
)

from hr_rag.documents import _parse_metadata, _section_ranges
from hr_rag.models import IndexError, PolicyDocument

from .models import (
    ApprovalFacts,
    ComplianceInput,
    ComplianceResult,
    Draft,
    DraftFound,
    DraftInput,
    NonBlank,
    PolicyEvidence,
)
from .policy import _active_snapshot

_BASELINE_PATH = Path("data") / "compliance-baselines" / "out-of-state-prior-approval-v2.json"
_ACTIVE_BASELINE_PIN: object = None
_GOVERNING_IDS = {"HR-001", "HR-004"}
_DIGEST = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]
_REVIEWER = re.compile(r"^@?[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_REVIEW = re.compile(
    r"^https://github\.com/[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
    r"/(?!\.{1,2}/)[A-Za-z0-9_.-]+"
    r"/pull/[1-9][0-9]*#pullrequestreview-[1-9][0-9]*$"
)
_LIMITATIONS = [
    "Approval facts are unauthenticated caller assertions.",
    "This check covers only the prior-approval requirement, not overall eligibility.",
]


class _BaselineRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    baseline_id: Literal["out-of-state-prior-approval"]
    baseline_version: Literal["2"]
    check_id: Literal["out_of_state_prior_approval"]
    document_id: Literal["HR-001", "HR-004"]
    canonical_sha256: _DIGEST
    normalization_version: Literal["utf8-lf-nfc-v1"]
    approval_status: Literal["approved"]
    approver_id: NonBlank
    approved_at: str
    approval_reference: str

    @field_validator("approver_id")
    @classmethod
    def valid_approver(cls, value: str) -> str:
        if not _REVIEWER.fullmatch(value) or "--" in value:
            raise ValueError("Approval must identify a repository reviewer.")
        return value

    @field_validator("approved_at")
    @classmethod
    def valid_approval_time(cls, value: str) -> str:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
            raise ValueError("Approval timestamp must be UTC RFC 3339.")
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        return value

    @field_validator("approval_reference")
    @classmethod
    def valid_review_reference(cls, value: str) -> str:
        if not _REVIEW.fullmatch(value):
            raise ValueError("Approval reference must identify a GitHub pull request review.")
        return value


class _Baseline(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    records: list[_BaselineRecord]


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def _approved_baseline(path: Path, pin: object) -> dict[str, _BaselineRecord] | None:
    if pin is None:
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object)
        records = _Baseline.model_validate(raw).records
        pinned = _Baseline.model_validate(pin).records
    except (OSError, UnicodeError, ValueError, ValidationError):
        return None
    if len(records) != 2 or len(pinned) != 2:
        return None
    by_id = {record.document_id: record for record in records}
    pinned_by_id = {record.document_id: record for record in pinned}
    if set(by_id) != _GOVERNING_IDS or set(pinned_by_id) != _GOVERNING_IDS:
        return None
    return by_id if by_id == pinned_by_id else None


def _source_bytes(root: Path, record: dict[str, object]) -> bytes | None:
    source_path = record.get("source_path")
    if not isinstance(source_path, str) or not source_path or "\\" in source_path:
        return None
    path = PurePosixPath(source_path)
    if (
        path.is_absolute()
        or PureWindowsPath(source_path).drive
        or any(part in {"", ".", ".."} for part in source_path.split("/"))
    ):
        return None
    try:
        resolved_root = root.resolve(strict=True)
        resolved = (resolved_root / Path(*path.parts)).resolve(strict=True)
        resolved.relative_to(resolved_root)
        raw = resolved.read_bytes()
    except (OSError, RuntimeError, ValueError):
        return None
    content_hash = record.get("content_hash")
    if not isinstance(content_hash, str) or hashlib.sha256(raw).hexdigest() != content_hash:
        return None
    return raw


def _canonical_sha256(raw: bytes) -> str:
    text = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()


def _verified_evidence(
    generation_id: str,
    metadata: dict[str, object],
    corpus_dir: Path,
    baseline: dict[str, _BaselineRecord],
) -> list[PolicyEvidence] | None:
    documents = metadata["documents"]
    chunks = metadata["chunks"]
    if not isinstance(documents, list) or not isinstance(chunks, list):
        raise IndexError("Policy snapshot metadata is invalid.")
    governing: dict[str, dict[str, object]] = {}
    for document in documents:
        if not isinstance(document, dict):
            raise IndexError("Policy snapshot document metadata is invalid.")
        document_id = document.get("document_id")
        if isinstance(document_id, str) and document_id in _GOVERNING_IDS:
            if document_id in governing:
                return None
            governing[document_id] = document
    if set(governing) != _GOVERNING_IDS:
        return None

    sources: dict[str, str] = {}
    for document_id, record in governing.items():
        raw = _source_bytes(corpus_dir, record)
        if raw is None:
            return None
        try:
            if _canonical_sha256(raw) != baseline[document_id].canonical_sha256:
                return None
            sources[document_id] = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

    candidates: list[dict[str, object]] = []
    labels: set[str] = set()
    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise IndexError("Policy snapshot chunk metadata is invalid.")
        section = chunk.get("section")
        if (
            chunk.get("document_id") == "HR-004"
            and isinstance(section, str)
            and re.match(r"^2\.2(?:\s|$)", section)
        ):
            labels.add(section)
            candidates.append(chunk)
    if not candidates or len(labels) != 1:
        return None

    governing_document = governing["HR-004"]
    source_format = governing_document.get("format")
    source_path = governing_document.get("source_path")
    title = governing_document.get("title")
    if source_format not in ("markdown", "txt") or not isinstance(source_path, str):
        return None
    if not isinstance(title, str) or not title.strip():
        return None
    text = sources["HR-004"]
    _, malformed, content_start = _parse_metadata(text, markdown=source_format == "markdown")
    if malformed:
        return None
    document = PolicyDocument(
        document_id="HR-004",
        title=title,
        format=source_format,
        text=text,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        source_path=source_path,
        content_start=content_start,
    )
    section_ranges = [
        (start, end)
        for label, start, end in _section_ranges(document)
        if label in labels
    ]
    if len(section_ranges) != 1:
        return None
    section_start, section_end = section_ranges[0]

    verified: list[tuple[int, int, PolicyEvidence]] = []
    seen: set[str] = set()
    for chunk in candidates:
        start, end = chunk.get("start"), chunk.get("end")
        snippet, chunk_id = chunk.get("snippet"), chunk.get("chunk_id")
        title, section = chunk.get("title"), chunk.get("section")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or not 0 <= start < end <= len(text)
            or start < section_start
            or end > section_end
            or not isinstance(snippet, str)
            or not snippet.strip()
            or text[start:end] != snippet
            or not isinstance(chunk_id, str)
            or not chunk_id.strip()
            or chunk_id in seen
            or not isinstance(title, str)
            or not title.strip()
            or title != governing["HR-004"].get("title")
            or not isinstance(section, str)
        ):
            return None
        seen.add(chunk_id)
        verified.append(
            (
                start,
                end,
                PolicyEvidence(
                    document_id="HR-004",
                    title=title,
                    section=section,
                    snippet=snippet,
                    chunk_id=chunk_id,
                    generation_id=generation_id,
                ),
            )
        )
    verified.sort(key=lambda item: item[0])
    covered_until = section_start
    for start, end, _ in verified:
        if start > covered_until and text[covered_until:start].strip():
            return None
        covered_until = max(covered_until, end)
    if text[covered_until:section_end].strip():
        return None
    return [item for _, _, item in verified]


def _outcome(
    facts: ApprovalFacts | None,
) -> tuple[Literal["compliant", "noncompliant", "indeterminate"], str]:
    if facts is None:
        return "indeterminate", "Approval facts are missing."
    if facts.status == "not_approved":
        return "noncompliant", "The caller asserts no approval was granted for this trip."
    approval = (
        datetime.fromisoformat(facts.approval_timestamp) if facts.approval_timestamp else None
    )
    travel = (
        datetime.fromisoformat(facts.travel_start_timestamp) if facts.travel_start_timestamp else None
    )
    late = approval is not None and travel is not None and approval >= travel
    if facts.no_other_approvals is True and (
        facts.authority == "other" or facts.format == "verbal" or late
    ):
        return "noncompliant", "The asserted candidate is disqualified and no other approval exists."
    if (
        facts.status == "approved"
        and facts.authority == "people_operations"
        and facts.format == "written"
        and approval is not None
        and travel is not None
        and approval < travel
    ):
        return "compliant", "The asserted approval is written, timely and from People Operations."
    missing = []
    for name in ("status", "authority", "format", "approval_timestamp", "travel_start_timestamp"):
        value = getattr(facts, name)
        if value is None or value == "unknown":
            missing.append(name)
    if facts.no_other_approvals is not True and (
        facts.authority == "other" or facts.format == "verbal" or late
    ):
        missing.append("whether another qualifying approval exists")
    return "indeterminate", f"Insufficient or unknown facts: {', '.join(missing)}."


def _check_policy_compliance(
    check_id: str,
    approval_facts: object,
    *,
    index_dir: Path | str,
    corpus_dir: Path | str,
    baseline_path: Path,
    pin: object,
) -> ComplianceResult:
    request = ComplianceInput.model_validate({"check_id": check_id, "approval_facts": approval_facts})
    generation_id, metadata = _active_snapshot(index_dir)
    baseline = _approved_baseline(baseline_path, pin)
    if baseline is None:
        return ComplianceResult(
            status="indeterminate",
            conclusion="indeterminate",
            evidence=[],
            limitations=[*_LIMITATIONS, "The reviewed baseline or active approval pin is unavailable or invalid."],
        )
    evidence = _verified_evidence(generation_id, metadata, Path(corpus_dir), baseline)
    if not evidence:
        return ComplianceResult(
            status="indeterminate",
            conclusion="indeterminate",
            evidence=[],
            limitations=[*_LIMITATIONS, "Governing documents or indexed citations could not be verified."],
        )
    conclusion, explanation = _outcome(request.approval_facts)
    return ComplianceResult(
        status="indeterminate" if conclusion == "indeterminate" else "found",
        conclusion=conclusion,
        evidence=evidence,
        limitations=[*_LIMITATIONS, explanation],
    )


def check_policy_compliance(
    check_id: str,
    approval_facts: object = None,
    *,
    index_dir: Path | str,
    corpus_dir: Path | str,
) -> ComplianceResult:
    return _check_policy_compliance(
        check_id,
        approval_facts,
        index_dir=index_dir,
        corpus_dir=corpus_dir,
        baseline_path=_BASELINE_PATH,
        pin=_ACTIVE_BASELINE_PIN,
    )


def draft_hr_email(
    recipient_name: str, purpose: str, supporting_details: str = ""
) -> DraftFound:
    request = DraftInput(
        recipient_name=recipient_name, purpose=purpose, supporting_details=supporting_details
    )
    body = f"Hello {request.recipient_name},\n\n{request.purpose}"
    if request.supporting_details:
        body += f"\n\n{request.supporting_details}"
    body += "\n\nBest,\nHR"
    return DraftFound(draft=Draft(subject=request.purpose, body=body))
