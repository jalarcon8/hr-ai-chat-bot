"""Adapters for F001 ranked retrieval and indexed section evidence."""

import math
from pathlib import Path

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from hr_rag import retrieve
from hr_rag.index import Embedder, _active_metadata, _faiss_module
from hr_rag.models import IndexError, OperationalError

from .models import (
    EvidenceNotFound,
    NonBlank,
    PolicyEvidence,
    RankedPolicyEvidence,
    SearchFound,
    SearchInput,
    SectionFound,
    SectionInput,
)


class InvalidCitationMetadataError(OperationalError):
    """Indexed citation offsets cannot be used to reconstruct source evidence."""


class _Document(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    document_id: NonBlank
    title: NonBlank


class _Chunk(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    chunk_id: NonBlank
    document_id: NonBlank
    title: NonBlank
    section: NonBlank | None
    snippet: NonBlank
    start: object = None
    end: object = None


def _active_snapshot(index_dir: Path | str) -> tuple[str, dict[str, object]]:
    generation_id, generation_dir, metadata = _active_metadata(Path(index_dir))
    # F001's metadata check verifies checksums but does not parse the FAISS file.
    try:
        index = _faiss_module().read_index(str(generation_dir / "index.faiss"))
    except (OSError, RuntimeError) as exc:
        raise IndexError("Policy snapshot has an invalid FAISS index.") from exc
    if index.d != metadata["dimension"] or index.ntotal != metadata["vector_count"]:
        raise IndexError("Policy snapshot index and metadata do not match.")
    return generation_id, metadata


def _snapshot(index_dir: Path | str) -> tuple[str, list[_Chunk]]:
    generation_id, metadata = _active_snapshot(index_dir)
    try:
        documents = TypeAdapter(list[_Document]).validate_python(metadata["documents"])
        chunks = TypeAdapter(list[_Chunk]).validate_python(metadata["chunks"])
    except ValidationError as exc:
        raise IndexError("Policy snapshot has invalid document or chunk metadata.") from exc

    documents_by_id = {document.document_id: document for document in documents}
    if len(documents_by_id) != len(documents):
        raise IndexError("Policy snapshot has duplicate document identifiers.")
    if len({chunk.chunk_id for chunk in chunks}) != len(chunks):
        raise IndexError("Policy snapshot has duplicate chunk identifiers.")
    for chunk in chunks:
        document = documents_by_id.get(chunk.document_id)
        if document is None or document.title != chunk.title:
            raise IndexError("Policy snapshot has invalid chunk associations.")
    return generation_id, chunks


def _offsets(chunk: _Chunk) -> tuple[int, int]:
    start, end = chunk.start, chunk.end
    if (
        not isinstance(start, int)
        or isinstance(start, bool)
        or not isinstance(end, int)
        or isinstance(end, bool)
        or start < 0
        or end <= start
        or end - start != len(chunk.snippet)
    ):
        raise InvalidCitationMetadataError("Indexed citation offsets are invalid.")
    return start, end


def search_policy_documents(
    question: str, index_dir: Path | str, *, embedder: Embedder, k: int = 5
) -> SearchFound | EvidenceNotFound:
    request = SearchInput(question=question, k=k)
    generation_id, chunks = _snapshot(index_dir)
    try:
        for chunk in chunks:
            _offsets(chunk)
    except InvalidCitationMetadataError as exc:
        raise IndexError("Policy snapshot has invalid chunk offsets.") from exc
    result = retrieve(request.question, index_dir, embedder=embedder, k=request.k)
    if result.generation_id != generation_id:
        raise IndexError("Policy index generation changed during retrieval.")
    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    for item in result.evidence:
        chunk = chunks_by_id.get(item.chunk_id)
        if chunk is None or (
            item.document_id,
            item.title,
            item.section,
            item.snippet,
            item.start,
            item.end,
        ) != (
            chunk.document_id,
            chunk.title,
            chunk.section,
            chunk.snippet,
            chunk.start,
            chunk.end,
        ):
            raise IndexError("Retrieved policy evidence does not match the snapshot.")
    try:
        evidence = [
            RankedPolicyEvidence(
                document_id=item.document_id,
                title=item.title,
                section=item.section,
                snippet=item.snippet,
                chunk_id=item.chunk_id,
                generation_id=result.generation_id,
                score=item.score,
            )
            for item in result.evidence
        ]
        if any(not item.snippet.strip() or not math.isfinite(item.score) for item in evidence):
            raise IndexError("Retrieved policy evidence has invalid metadata.")
        if not evidence:
            return EvidenceNotFound(generation_id=result.generation_id)
        return SearchFound(evidence=evidence, generation_id=result.generation_id)
    except ValidationError as exc:
        raise IndexError("Retrieved policy evidence has invalid metadata.") from exc


def get_policy_section(
    document_id: str, section: str, index_dir: Path | str
) -> SectionFound | EvidenceNotFound:
    request = SectionInput(document_id=document_id, section=section)
    generation_id, chunks = _snapshot(index_dir)
    selected = [
        chunk
        for chunk in chunks
        if chunk.document_id == request.document_id and chunk.section == request.section
    ]
    ordered = sorted(((_offsets(chunk)[0], chunk) for chunk in selected), key=lambda item: item[0])
    if not selected:
        return EvidenceNotFound(generation_id=generation_id)
    return SectionFound(
        evidence=[
            PolicyEvidence(
                document_id=chunk.document_id,
                title=chunk.title,
                section=chunk.section,
                snippet=chunk.snippet,
                chunk_id=chunk.chunk_id,
                generation_id=generation_id,
            )
            for _, chunk in ordered
        ],
        generation_id=generation_id,
    )
