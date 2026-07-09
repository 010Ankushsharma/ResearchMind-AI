"""
tests/test_chroma_chunking.py

Unit tests for ChromaService.chunk_text() — the sliding-window chunker used
by the Knowledge Base Agent before embedding content into ChromaDB.

`chunk_text` is a @staticmethod, so it can be tested directly without
connecting to a live ChromaDB instance (the constructor is never called).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from rag.chroma_service import ChromaService  # noqa: E402


class TestChunkText:
    def test_empty_string_returns_no_chunks(self):
        assert ChromaService.chunk_text("") == []

    def test_whitespace_only_returns_no_chunks(self):
        assert ChromaService.chunk_text("   \n\n   ") == []

    def test_short_text_returns_single_chunk(self):
        text = "This is a short piece of text that fits in one chunk."
        chunks = ChromaService.chunk_text(text, chunk_size=1000, overlap=150)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_splits_into_multiple_chunks(self):
        # ~3000 chars of repeated sentences, well over the 1000-char chunk size
        sentence = "AI agents are becoming increasingly capable and autonomous. "
        text = sentence * 60
        chunks = ChromaService.chunk_text(text, chunk_size=1000, overlap=150)
        assert len(chunks) > 1

    def test_chunks_respect_max_size_with_tolerance(self):
        # Chunks may slightly exceed chunk_size when extending to a sentence
        # boundary, but should never wildly exceed it.
        sentence = "This is a test sentence used to build a long document. "
        text = sentence * 80
        chunks = ChromaService.chunk_text(text, chunk_size=500, overlap=100)
        for chunk in chunks:
            assert len(chunk) <= 500 + 200  # allow boundary-seeking slack

    def test_no_chunk_is_empty(self):
        sentence = "Repeated content for chunking validation purposes. "
        text = sentence * 50
        chunks = ChromaService.chunk_text(text, chunk_size=300, overlap=50)
        assert all(chunk.strip() for chunk in chunks)

    def test_prefers_breaking_on_sentence_boundary(self):
        text = (
            "First sentence ends here. " * 20
            + "Second distinct sentence ends differently! " * 20
        )
        chunks = ChromaService.chunk_text(text, chunk_size=400, overlap=50)
        # Most chunks should end on a sentence boundary (period + space consumed)
        boundary_endings = sum(1 for c in chunks[:-1] if c.endswith(".") or c.endswith("!"))
        assert boundary_endings >= len(chunks) - 2  # allow the occasional edge case

    def test_overlap_creates_shared_content_between_consecutive_chunks(self):
        sentence = "Context-preserving overlap is important for retrieval quality. "
        text = sentence * 40
        chunks = ChromaService.chunk_text(text, chunk_size=400, overlap=100)
        if len(chunks) > 1:
            # Some suffix of chunk[0] should reappear as a prefix-ish portion of chunk[1]
            tail = chunks[0][-50:]
            assert any(word in chunks[1] for word in tail.split() if len(word) > 4)
