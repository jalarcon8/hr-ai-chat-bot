"""Validated configuration with environment-based provider secrets."""

from dataclasses import dataclass
import os
from pathlib import Path

from .models import InvalidInputError


@dataclass(frozen=True)
class ChunkingConfig:
    max_tokens: int = 200
    overlap_tokens: int = 30
    tokenizer_id: str = "sentence-transformers/all-MiniLM-L6-v2"

    def __post_init__(self) -> None:
        if self.max_tokens < 1:
            raise InvalidInputError("max_tokens must be at least 1.")
        if self.overlap_tokens < 0 or self.overlap_tokens >= self.max_tokens:
            raise InvalidInputError("overlap_tokens must be nonnegative and less than max_tokens.")
        if not self.tokenizer_id.strip():
            raise InvalidInputError("tokenizer_id must not be blank.")


@dataclass(frozen=True)
class Settings:
    corpus_dir: Path = Path("corpus")
    index_dir: Path = Path(".hr_rag_index")
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_revision: str | None = None
    answer_model: str = "llama-3.3-70b-versatile"
    top_k: int = 5
    chunking: ChunkingConfig = ChunkingConfig()

    def __post_init__(self) -> None:
        if self.top_k < 1:
            raise InvalidInputError("top_k must be at least 1.")
        if not self.embedding_model.strip() or not self.answer_model.strip():
            raise InvalidInputError("Model identifiers must not be blank.")

    @classmethod
    def from_environment(cls) -> "Settings":
        """Read nonsecret settings from the environment; API keys remain provider-owned."""
        try:
            top_k = int(os.getenv("HR_RAG_TOP_K", "5"))
            max_tokens = int(os.getenv("HR_RAG_CHUNK_TOKENS", "200"))
            overlap_tokens = int(os.getenv("HR_RAG_CHUNK_OVERLAP", "30"))
        except ValueError as exc:
            raise InvalidInputError("RAG numeric environment settings must be integers.") from exc
        return cls(
            corpus_dir=Path(os.getenv("HR_RAG_CORPUS_DIR", "corpus")),
            index_dir=Path(os.getenv("HR_RAG_INDEX_DIR", ".hr_rag_index")),
            embedding_model=os.getenv(
                "HR_RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
            ),
            embedding_revision=os.getenv("HR_RAG_EMBEDDING_REVISION") or None,
            answer_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            top_k=top_k,
            chunking=ChunkingConfig(
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
                tokenizer_id=os.getenv(
                    "HR_RAG_TOKENIZER_ID", "sentence-transformers/all-MiniLM-L6-v2"
                ),
            ),
        )
