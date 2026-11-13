"""Deterministic Markdown/TXT ingestion and source-aligned chunking."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Protocol

from .config import ChunkingConfig
from .models import (
    DocumentValidationError,
    MetadataValidationError,
    PolicyChunk,
    PolicyDocument,
)

_METADATA_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):[ \t]*(.*)$")
_MARKDOWN_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*#*\s*$")
_NUMBERED_SECTION = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+(.+?)\s*$")
_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class OffsetTokenizer(Protocol):
    def tokenize_with_offsets(self, text: str) -> list[tuple[int, int]]: ...


def _normalized_filename_id(path: Path, corpus_root: Path) -> str:
    try:
        relative = path.resolve().relative_to(corpus_root.resolve())
        normalized = relative.with_suffix("").as_posix().strip().casefold()
    except (OSError, ValueError) as exc:
        raise MetadataValidationError("Could not derive a corpus-relative document identity.") from exc
    if not normalized or normalized == "." or any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise MetadataValidationError("Could not derive a valid identity from the source filename.")
    return normalized


def _parse_metadata(text: str, *, markdown: bool) -> tuple[dict[str, list[str]], set[str], int]:
    fields: dict[str, list[str]] = {}
    malformed: set[str] = set()
    offset = 0
    metadata_started = False
    lines = text.splitlines(keepends=True)
    frontmatter = markdown and bool(lines) and lines[0].strip() == "---"
    if frontmatter:
        offset = len(lines[0])
        content_offset = offset
        for line in lines[1:]:
            stripped = line.rstrip("\r\n")
            if stripped.strip() == "---":
                return fields, malformed, offset + len(line)
            match = _METADATA_LINE.match(stripped)
            if match:
                key, value = match.groups()
                fields.setdefault(key.casefold(), []).append(value.strip())
                offset += len(line)
                continue
            malformed_match = re.match(r"^(document_id|title)\b", stripped, re.IGNORECASE)
            if malformed_match:
                malformed.add(malformed_match.group(1).casefold())
            offset += len(line)
        malformed.add("front matter")
        return fields, malformed, max(content_offset, offset)

    for line in lines:
        stripped = line.rstrip("\r\n")
        if not stripped.strip():
            offset += len(line)
            break
        match = _METADATA_LINE.match(stripped)
        if match:
            key, value = match.groups()
            fields.setdefault(key.casefold(), []).append(value.strip())
            metadata_started = True
            offset += len(line)
            continue
        malformed_match = re.match(r"^(document_id|title)\b", stripped, re.IGNORECASE)
        if malformed_match:
            malformed.add(malformed_match.group(1).casefold())
            metadata_started = True
            offset += len(line)
        elif metadata_started:
            offset += len(line)
        else:
            break
    return fields, malformed, offset


def parse_document(path: Path | str, corpus_dir: Path | str) -> PolicyDocument:
    source = Path(path)
    root = Path(corpus_dir)
    extension = source.suffix.casefold()
    if extension not in {".md", ".txt"}:
        raise DocumentValidationError(f"Unsupported policy format: {extension or '(none)'}")
    try:
        source_resolved = source.resolve()
        relative = source_resolved.relative_to(root.resolve())
        raw = source.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise DocumentValidationError(f"Could not read supported policy source: {source.name}") from exc
    if not text.strip():
        raise DocumentValidationError(f"Policy source is empty: {source.name}")

    metadata, malformed_fields, content_start = _parse_metadata(
        text, markdown=extension == ".md"
    )
    if malformed_fields:
        raise MetadataValidationError(
            f"Malformed recognized metadata in {source.name}: {', '.join(sorted(malformed_fields))}."
        )
    id_values = metadata.get("document_id", [])
    title_values = metadata.get("title", [])
    if len(id_values) > 1:
        raise MetadataValidationError(f"Duplicate document_id metadata in {source.name}.")
    if id_values:
        document_id = id_values[0]
        if not document_id or "\n" in document_id or "\r" in document_id:
            raise MetadataValidationError(f"Invalid document_id metadata in {source.name}.")
        if (
            document_id.startswith(("/", "\\"))
            or re.match(r"^[A-Za-z]:", document_id)
            or any(part in {"", ".", ".."} for part in re.split(r"[/\\]", document_id))
            or any(ord(char) < 32 for char in document_id)
        ):
            raise MetadataValidationError(f"Invalid document_id metadata in {source.name}.")
    else:
        document_id = _normalized_filename_id(source, root)

    if len(title_values) > 1:
        raise MetadataValidationError(f"Duplicate title metadata in {source.name}.")
    if title_values:
        title = title_values[0]
        if not title:
            raise MetadataValidationError(f"Invalid title metadata in {source.name}.")
    else:
        heading = next(
            (match.group(2).strip() for line in text.splitlines() if (match := _MARKDOWN_HEADING.match(line))),
            "",
        )
        title = heading or source.stem.replace("-", " ").replace("_", " ").strip()
        if not title:
            raise MetadataValidationError(f"Could not derive a title for {source.name}.")

    return PolicyDocument(
        document_id=document_id,
        title=title,
        format="markdown" if extension == ".md" else "txt",
        text=text,
        content_hash=hashlib.sha256(raw).hexdigest(),
        source_path=relative.as_posix(),
        content_start=content_start,
    )


def ingest_corpus(corpus_dir: Path | str) -> list[PolicyDocument]:
    root = Path(corpus_dir)
    if not root.is_dir():
        raise DocumentValidationError(f"Policy corpus directory does not exist: {root}")
    paths = sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.casefold() in {".md", ".txt"}),
        key=lambda item: item.relative_to(root).as_posix().casefold(),
    )
    if not paths:
        raise DocumentValidationError(f"Policy corpus contains no Markdown or TXT files: {root}")
    documents = [parse_document(path, root) for path in paths]
    ids: set[str] = set()
    for document in documents:
        normalized_id = document.document_id.casefold()
        if normalized_id in ids:
            raise MetadataValidationError(f"Duplicate document identity: {document.document_id}")
        ids.add(normalized_id)
    return documents


def _section_ranges(document: PolicyDocument) -> list[tuple[str | None, int, int]]:
    text = document.text
    lines = text.splitlines(keepends=True)
    positions: list[tuple[int, int, str]] = []
    offset = 0
    for line in lines:
        clean = line.rstrip("\r\n")
        if document.format == "markdown":
            match = _MARKDOWN_HEADING.match(clean)
            if match:
                positions.append((offset, offset + len(line), match.group(2).strip()))
        else:
            match = _NUMBERED_SECTION.match(clean)
            if match:
                positions.append((offset, offset + len(line), f"{match.group(1)} {match.group(2).strip()}"))
        offset += len(line)

    if not positions:
        start = document.content_start
        return [(None, start, len(text))] if start < len(text) else []

    ranges: list[tuple[str | None, int, int]] = []
    if positions[0][0] > document.content_start:
        preamble = text[document.content_start:positions[0][0]]
        if preamble.strip():
            ranges.append((None, document.content_start, positions[0][0]))

    heading_stack: list[str] = []
    for index, (heading_start, body_start, label) in enumerate(positions):
        end = positions[index + 1][0] if index + 1 < len(positions) else len(text)
        if document.format == "markdown":
            level_match = _MARKDOWN_HEADING.match(text[heading_start:].splitlines()[0])
            level = len(level_match.group(1)) if level_match else 1
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(label)
            section = " > ".join(heading_stack)
        else:
            section = label
        if text[body_start:end].strip():
            ranges.append((section, body_start, end))
    return ranges


def _token_offsets(tokenizer: OffsetTokenizer | None, text: str) -> list[tuple[int, int]]:
    if tokenizer is not None:
        offsets = tokenizer.tokenize_with_offsets(text)
    else:
        offsets = [(match.start(), match.end()) for match in _TOKEN.finditer(text)]
    previous_end = 0
    for start, end in offsets:
        if start < previous_end or start < 0 or end <= start or end > len(text):
            raise DocumentValidationError("Tokenizer returned invalid source offsets.")
        previous_end = end
    return offsets


def chunk_documents(
    documents: list[PolicyDocument],
    chunking_config: ChunkingConfig,
    tokenizer: OffsetTokenizer | None = None,
) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    for document in documents:
        for section, section_start, section_end in _section_ranges(document):
            source_segment = document.text[section_start:section_end]
            token_offsets = _token_offsets(tokenizer, source_segment)
            if not token_offsets:
                continue
            step = chunking_config.max_tokens - chunking_config.overlap_tokens
            cursor = 0
            while cursor < len(token_offsets):
                last = min(cursor + chunking_config.max_tokens, len(token_offsets)) - 1
                relative_start = token_offsets[cursor][0]
                relative_end = token_offsets[last][1]
                start = section_start + relative_start
                end = section_start + relative_end
                snippet = document.text[start:end]
                if snippet.strip():
                    chunk_id = f"{document.document_id}:{start}:{end}"
                    chunks.append(
                        PolicyChunk(
                            chunk_id=chunk_id,
                            document_id=document.document_id,
                            title=document.title,
                            section=section,
                            start=start,
                            end=end,
                            snippet=snippet,
                        )
                    )
                if last + 1 == len(token_offsets):
                    break
                cursor += step
    return chunks
