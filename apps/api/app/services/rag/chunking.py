"""Deterministic text chunking for RAG ingestion."""

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    """One deterministic text chunk."""

    index: int
    content: str
    content_hash: str
    token_count_estimate: int


def content_hash(content: str) -> str:
    """Return a stable SHA-256 hash for normalized content."""
    normalized = "\n".join(line.rstrip() for line in content.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def chunk_text(content: str, *, chunk_size: int, overlap: int) -> list[TextChunk]:
    """Split content into overlapping deterministic chunks."""
    text = content.strip()
    if not text:
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    chunks: list[TextChunk] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end), text.rfind(" ", start, end))
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=chunk_content,
                    content_hash=content_hash(chunk_content),
                    token_count_estimate=max(1, len(chunk_content.split())),
                )
            )
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks
