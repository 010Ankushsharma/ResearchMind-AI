"""
rag/chroma_service.py

Write-path RAG service used by the Knowledge Base Agent.

Responsibilities:
  - Chunk extracted source content into overlapping windows
  - Embed each chunk locally (BAAI/bge-small-en-v1.5, via embedding_service)
  - Store vectors + metadata in ChromaDB
  - Mirror each chunk as a `KnowledgeDocument` row in Postgres (relational metadata)

This is the counterpart to `tools/rag_tool.py` (read-path / agent retrieval).
"""

from __future__ import annotations

import logging
import uuid

import chromadb

from core.config import settings
from database.connection import get_db_context
from models.knowledge_document import KnowledgeDocument
from rag.embedding_service import get_embedding_function

logger = logging.getLogger(__name__)

CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150


class ChromaService:
    """High-level interface over a single ChromaDB collection for the platform."""

    def __init__(self):
        self._client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        self._collection = self._client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=get_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )

    # ── Chunking ─────────────────────────────────────────────────────────

    @staticmethod
    def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
        """Simple sliding-window character chunker with overlap to preserve context across boundaries."""
        text = text.strip()
        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)
        # Any of these followed by a space counts as a sentence boundary —
        # searching only for ". " (as an earlier version did) missed "! "
        # and "? " entirely, silently cutting chunks mid-word whenever a
        # sentence happened to end in an exclamation or question mark.
        sentence_enders = (". ", "! ", "? ")

        while start < text_length:
            end = min(start + chunk_size, text_length)

            # Try to break on whichever sentence boundary sits closest to
            # the natural cutoff, for cleaner chunks.
            best_boundary = max(
                (text.rfind(ender, start, end) for ender in sentence_enders),
                default=-1,
            )
            if best_boundary != -1 and best_boundary > start + (chunk_size // 2):
                end = best_boundary + 1  # include the punctuation, drop the trailing space into the next chunk

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap if end - overlap > start else end

        return chunks

    # ── Write path ───────────────────────────────────────────────────────

    async def store_source_content(
        self,
        *,
        research_session_id: uuid.UUID,
        user_id: uuid.UUID,
        source_id: uuid.UUID | None,
        text: str,
        extra_metadata: dict | None = None,
    ) -> list[str]:
        """
        Chunk + embed + store a source's extracted content.
        Returns the list of Chroma vector ids created.
        """
        chunks = self.chunk_text(text)
        if not chunks:
            return []

        vector_ids = [f"{research_session_id}_{uuid.uuid4().hex[:8]}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "research_session_id": str(research_session_id),
                "user_id": str(user_id),
                "source_id": str(source_id) if source_id else "",
                "chunk_index": i,
                **(extra_metadata or {}),
            }
            for i in range(len(chunks))
        ]

        try:
            self._collection.add(ids=vector_ids, documents=chunks, metadatas=metadatas)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to add chunks to ChromaDB: %s", exc)
            raise

        await self._mirror_to_postgres(
            research_session_id=research_session_id,
            user_id=user_id,
            source_id=source_id,
            chunks=chunks,
            vector_ids=vector_ids,
        )

        logger.info("Stored %d chunks for session %s", len(chunks), research_session_id)
        return vector_ids

    async def _mirror_to_postgres(
        self,
        *,
        research_session_id: uuid.UUID,
        user_id: uuid.UUID,
        source_id: uuid.UUID | None,
        chunks: list[str],
        vector_ids: list[str],
    ) -> None:
        async with get_db_context() as db:
            for idx, (chunk, vec_id) in enumerate(zip(chunks, vector_ids)):
                db.add(
                    KnowledgeDocument(
                        research_session_id=research_session_id,
                        source_id=source_id,
                        user_id=user_id,
                        chroma_vector_id=vec_id,
                        chunk_text=chunk,
                        chunk_index=idx,
                        token_count=len(chunk.split()),
                    )
                )

    # ── Maintenance ──────────────────────────────────────────────────────

    def delete_session_vectors(self, research_session_id: uuid.UUID) -> None:
        """Remove all vectors for a session (used on session deletion)."""
        try:
            self._collection.delete(where={"research_session_id": str(research_session_id)})
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to delete vectors for session %s: %s", research_session_id, exc)


_chroma_service: ChromaService | None = None


def get_chroma_service() -> ChromaService:
    """Lazily-initialized singleton — avoids connecting to Chroma at import time."""
    global _chroma_service
    if _chroma_service is None:
        _chroma_service = ChromaService()
    return _chroma_service
