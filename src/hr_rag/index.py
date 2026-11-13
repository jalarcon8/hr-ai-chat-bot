"""Local embedding, FAISS snapshot lifecycle, and top-k retrieval."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid
from typing import Protocol

import numpy as np

from .config import ChunkingConfig
from .documents import OffsetTokenizer, chunk_documents, ingest_corpus
from .models import (
    BuildResult,
    EmbeddingError,
    Evidence,
    IndexError,
    InvalidInputError,
    PolicyChunk,
    RetrievalResult,
)


class Embedder(OffsetTokenizer, Protocol):
    model_id: str
    tokenizer_id: str

    def encode(self, texts: list[str]) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, revision: str | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingError(
                "sentence-transformers is required; install the project requirements."
            ) from exc
        try:
            options = {"revision": revision} if revision else {}
            self._model = SentenceTransformer(model_name, device="cpu", **options)
            self._tokenizer = self._model.tokenizer
        except Exception as exc:
            raise EmbeddingError(f"Could not load embedding model {model_name}.") from exc
        self.model_id = f"{model_name}@{revision or 'default'}"
        self.tokenizer_id = self.model_id

    def encode(self, texts: list[str]) -> np.ndarray:
        try:
            vectors = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise EmbeddingError("Embedding generation failed.") from exc
        return np.asarray(vectors, dtype=np.float32)

    def tokenize_with_offsets(self, text: str) -> list[tuple[int, int]]:
        try:
            result = self._tokenizer(
                text, add_special_tokens=False, return_offsets_mapping=True, truncation=False
            )
            return [(int(start), int(end)) for start, end in result["offset_mapping"] if end > start]
        except Exception as exc:
            raise EmbeddingError("Could not tokenize policy text with the embedding tokenizer.") from exc


def _faiss_module():
    try:
        import faiss
    except ImportError as exc:
        raise IndexError("faiss-cpu is required; install the project requirements.") from exc
    return faiss


def _normalize(vectors: np.ndarray) -> np.ndarray:
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.ndim != 2 or not values.shape[0] or not values.shape[1]:
        raise EmbeddingError("Embedder returned an empty or invalid vector matrix.")
    if not np.isfinite(values).all():
        raise EmbeddingError("Embedder returned non-finite vector values.")
    norms = np.linalg.norm(values, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise EmbeddingError("Embedder returned a zero-length vector.")
    return np.ascontiguousarray(values / norms, dtype=np.float32)


def _chunk_dict(chunk: PolicyChunk) -> dict[str, object]:
    return asdict(chunk)


def _chunk_from_dict(value: dict[str, object]) -> PolicyChunk:
    return PolicyChunk(
        chunk_id=str(value["chunk_id"]),
        document_id=str(value["document_id"]),
        title=str(value["title"]),
        section=str(value["section"]) if value.get("section") is not None else None,
        start=int(value["start"]),
        end=int(value["end"]),
        snippet=str(value["snippet"]),
    )


def _active_metadata(index_root: Path) -> tuple[str, Path, dict[str, object]]:
    pointer_path = index_root / "active.json"
    try:
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        if not isinstance(pointer, dict):
            raise ValueError("invalid active pointer")
        generation_id = str(pointer["generation_id"])
        if not re.fullmatch(r"[a-f0-9]{32}", generation_id):
            raise ValueError("invalid generation id")
        generation_dir = index_root / "generations" / generation_id
        metadata_bytes = (generation_dir / "metadata.json").read_bytes()
        index_bytes = (generation_dir / "index.faiss").read_bytes()
        if hashlib.sha256(metadata_bytes).hexdigest() != pointer["metadata_sha256"]:
            raise ValueError("metadata checksum mismatch")
        if hashlib.sha256(index_bytes).hexdigest() != pointer["index_sha256"]:
            raise ValueError("index checksum mismatch")
        metadata = json.loads(metadata_bytes.decode("utf-8"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise IndexError("Active index snapshot is missing or corrupt.") from exc
    if not isinstance(metadata, dict) or metadata.get("generation_id") != generation_id:
        raise IndexError("Active index snapshot generation does not match its pointer.")
    if (
        metadata.get("schema_version") != 1
        or not isinstance(metadata.get("chunks"), list)
        or not isinstance(metadata.get("documents"), list)
        or not isinstance(metadata.get("dimension"), int)
        or metadata["dimension"] < 1
        or not isinstance(metadata.get("vector_count"), int)
        or metadata["vector_count"] != len(metadata["chunks"])
        or not isinstance(metadata.get("embedding_model"), str)
    ):
        raise IndexError("Active index snapshot metadata is invalid.")
    return generation_id, generation_dir, metadata


def build_index(
    index_dir: Path | str,
    *,
    corpus_dir: Path | str = "corpus",
    embedder: Embedder,
    chunking_config: ChunkingConfig,
) -> BuildResult:
    documents = ingest_corpus(corpus_dir)
    chunks = chunk_documents(documents, chunking_config, tokenizer=embedder)
    if not chunks:
        raise IndexError("The corpus produced no indexable chunks.")
    try:
        vectors = _normalize(embedder.encode([chunk.snippet for chunk in chunks]))
    except EmbeddingError:
        raise
    except Exception as exc:
        raise EmbeddingError("Embedding generation failed.") from exc
    if vectors.shape[0] != len(chunks):
        raise EmbeddingError("Embedder vector count does not match the chunk count.")

    faiss = _faiss_module()
    root = Path(index_dir)
    generations = root / "generations"
    generation_id = uuid.uuid4().hex
    temp_dir: Path | None = None
    try:
        generations.mkdir(parents=True, exist_ok=True)
        temp_dir = Path(tempfile.mkdtemp(prefix=f".{generation_id}-", dir=generations))
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        faiss.write_index(index, str(temp_dir / "index.faiss"))
        metadata = {
            "schema_version": 1,
            "generation_id": generation_id,
            "embedding_model": str(embedder.model_id),
            "dimension": int(vectors.shape[1]),
            "chunking_config": {
                **asdict(chunking_config),
                "tokenizer_id": str(getattr(embedder, "tokenizer_id", chunking_config.tokenizer_id)),
            },
            "documents": [
                {
                    "document_id": doc.document_id,
                    "title": doc.title,
                    "format": doc.format,
                    "source_path": doc.source_path,
                    "content_hash": doc.content_hash,
                }
                for doc in documents
            ],
            "chunks": [_chunk_dict(chunk) for chunk in chunks],
            "vector_count": int(index.ntotal),
        }
        metadata_path = temp_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        if index.ntotal != len(chunks) or len(metadata["chunks"]) != index.ntotal:
            raise IndexError("Candidate index and metadata counts do not match.")

        final_dir = generations / generation_id
        os.replace(temp_dir, final_dir)
        temp_dir = None
        pointer_temp = root / f".active-{generation_id}.tmp"
        pointer = {
            "generation_id": generation_id,
            "metadata_sha256": hashlib.sha256((final_dir / "metadata.json").read_bytes()).hexdigest(),
            "index_sha256": hashlib.sha256((final_dir / "index.faiss").read_bytes()).hexdigest(),
        }
        pointer_temp.write_text(json.dumps(pointer), encoding="utf-8")
        os.replace(pointer_temp, root / "active.json")
    except (EmbeddingError, IndexError):
        raise
    except Exception as exc:
        raise IndexError("Could not build or activate the FAISS index snapshot.") from exc
    finally:
        if temp_dir is not None and temp_dir.exists():
            shutil.rmtree(temp_dir)

    return BuildResult(
        generation_id=generation_id,
        document_count=len(documents),
        chunk_count=len(chunks),
        embedding_model=str(embedder.model_id),
        index_dir=str(root),
    )


def retrieve(
    question: str,
    index_dir: Path | str,
    *,
    embedder: Embedder,
    k: int = 5,
) -> RetrievalResult:
    if not isinstance(question, str) or not question.strip():
        raise InvalidInputError("Question must not be blank.")
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise InvalidInputError("k must be an integer greater than zero.")
    root = Path(index_dir)
    generation_id, generation_dir, metadata = _active_metadata(root)
    if metadata.get("embedding_model") != str(embedder.model_id):
        raise IndexError("Active index uses a different embedding model.")
    try:
        faiss = _faiss_module()
        index = faiss.read_index(str(generation_dir / "index.faiss"))
        chunks_raw = metadata["chunks"]
        chunks = [_chunk_from_dict(item) for item in chunks_raw]  # type: ignore[arg-type]
        dimension = int(metadata["dimension"])
        if index.d != dimension or index.ntotal != len(chunks) or index.ntotal != metadata["vector_count"]:
            raise IndexError("Index dimensions or metadata count do not match the snapshot.")
        query_vectors = _normalize(embedder.encode([question]))
        if query_vectors.shape[0] != 1:
            raise EmbeddingError("Question embedder must return exactly one vector.")
        if query_vectors.shape[1] != dimension:
            raise IndexError("Question embedding dimension does not match the active index.")
        scores, indices = index.search(query_vectors, min(k, index.ntotal))
    except (IndexError, EmbeddingError):
        raise
    except Exception as exc:
        raise IndexError("Could not query the active FAISS snapshot.") from exc

    evidence = tuple(
        Evidence(
            chunk_id=chunks[int(position)].chunk_id,
            document_id=chunks[int(position)].document_id,
            title=chunks[int(position)].title,
            section=chunks[int(position)].section,
            start=chunks[int(position)].start,
            end=chunks[int(position)].end,
            snippet=chunks[int(position)].snippet,
            score=float(score),
        )
        for score, position in zip(scores[0], indices[0])
        if int(position) >= 0
    )
    return RetrievalResult(question=question, evidence=evidence, generation_id=generation_id)
