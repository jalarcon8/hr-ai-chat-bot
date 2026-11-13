"""Public Python interface for the HR policy RAG feature."""

from .answers import GroqGenerator, answer_question
from .config import ChunkingConfig, Settings
from .documents import chunk_documents, ingest_corpus, parse_document
from .index import SentenceTransformerEmbedder, build_index, retrieve
from .models import (
    AnswerResult,
    BuildResult,
    Citation,
    Claim,
    DocumentValidationError,
    Evidence,
    GroundingValidationError,
    HRRAGError,
    IndexError,
    InvalidInputError,
    MetadataValidationError,
    OperationalError,
    PolicyChunk,
    PolicyDocument,
    RetrievalResult,
)

__all__ = [
    "AnswerResult",
    "BuildResult",
    "ChunkingConfig",
    "Citation",
    "Claim",
    "DocumentValidationError",
    "Evidence",
    "GroqGenerator",
    "GroundingValidationError",
    "HRRAGError",
    "IndexError",
    "InvalidInputError",
    "MetadataValidationError",
    "OperationalError",
    "PolicyChunk",
    "PolicyDocument",
    "RetrievalResult",
    "SentenceTransformerEmbedder",
    "Settings",
    "answer_question",
    "build_index",
    "chunk_documents",
    "ingest_corpus",
    "parse_document",
    "retrieve",
]
