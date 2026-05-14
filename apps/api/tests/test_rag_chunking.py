"""Tests for RAG text chunking."""

import pytest

from app.services.rag.chunking import chunk_text, content_hash


def test_content_hash_is_stable_for_trailing_whitespace():
    assert content_hash("Farm souls first.\n") == content_hash("Farm souls first.")


def test_chunk_text_creates_overlapping_chunks():
    text = "Alpha beta gamma delta epsilon zeta eta theta iota kappa lambda."

    chunks = chunk_text(text, chunk_size=24, overlap=6)

    assert len(chunks) > 1
    assert chunks[0].index == 0
    assert chunks[0].content_hash
    assert all(chunk.token_count_estimate > 0 for chunk in chunks)


def test_chunk_text_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=10, overlap=10)
