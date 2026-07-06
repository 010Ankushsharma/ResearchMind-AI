"""
models/knowledge_document.py

KnowledgeDocument ORM model.

Postgres-side record mirroring each chunk stored in ChromaDB. The actual
vector embedding lives in ChromaDB (BAAI/bge-small-en-v1.5); this row keeps
the relational metadata (which session/source it came from, chunk text,
the Chroma vector id) so we can join, filter, and display results without
round-tripping to the vector store for non-similarity queries.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    research_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Owning user — denormalized for fast "what did I research last month?"
    # queries without joining through research_sessions every time.
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # The id of the corresponding vector inside the ChromaDB collection.
    chroma_vector_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # The raw text chunk that was embedded (kept here for display/debugging
    # without needing to query Chroma).
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)

    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Topic/entity tags extracted for the Knowledge Graph & topic clustering
    metadata_tags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    research_session: Mapped["ResearchSession"] = relationship(back_populates="knowledge_documents")
    source: Mapped["Source | None"] = relationship()

    def __repr__(self) -> str:
        return f"<KnowledgeDocument id={self.id} chunk_index={self.chunk_index}>"
