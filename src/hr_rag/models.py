"""Typed values and explicit errors shared across the RAG components."""

from dataclasses import dataclass, field
from typing import Literal


class HRRAGError(Exception):
    """Base class for expected, user-actionable F001 failures."""


class InvalidInputError(HRRAGError):
    """Raised when a public operation receives invalid input."""


class DocumentValidationError(HRRAGError):
    """Raised when a policy source cannot be safely ingested."""


class MetadataValidationError(DocumentValidationError):
    """Raised when source identity or recognized metadata is invalid."""


class OperationalError(HRRAGError):
    """Base class for runtime failures distinct from unsupported answers."""


class EmbeddingError(OperationalError):
    """Raised when document or question embedding fails."""


class IndexError(OperationalError):
    """Raised when a local index cannot be created, loaded, or queried."""


class RetrievalError(OperationalError):
    """Raised when evidence retrieval fails."""


class GenerationError(OperationalError):
    """Raised when answer generation fails."""


class GroundingValidationError(OperationalError):
    """Raised when generated output cannot be validated against evidence."""


@dataclass(frozen=True)
class PolicyDocument:
    document_id: str
    title: str
    format: Literal["markdown", "txt"]
    text: str
    content_hash: str
    source_path: str
    content_start: int


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    document_id: str
    title: str
    section: str | None
    start: int
    end: int
    snippet: str


@dataclass(frozen=True)
class Evidence:
    chunk_id: str
    document_id: str
    title: str
    section: str | None
    start: int
    end: int
    snippet: str
    score: float


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    document_id: str
    title: str
    section: str | None
    snippet: str


@dataclass(frozen=True)
class Claim:
    text: str
    citation_ids: tuple[str, ...]
    kind: Literal["policy_fact", "recommendation"] = "policy_fact"


@dataclass(frozen=True)
class AnswerResult:
    status: Literal["answered", "partial", "unsupported", "conflicting"]
    claims: tuple[Claim, ...] = ()
    limitations: tuple[str, ...] = ()
    citations: tuple[Citation, ...] = ()


@dataclass(frozen=True)
class BuildResult:
    generation_id: str
    document_count: int
    chunk_count: int
    embedding_model: str
    index_dir: str


@dataclass(frozen=True)
class RetrievalResult:
    question: str
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    generation_id: str = ""
