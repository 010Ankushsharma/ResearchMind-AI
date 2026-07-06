"""
models/source.py

Source ORM model.

Represents a single web source discovered by the Web Research Agent
(via Tavily / DuckDuckGo). Tracks credibility scoring computed by the
Fact Verification Agent (domain authority, source age, citation count,
overall trustworthiness 0-100).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    research_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Raw snippet returned by the search tool (Tavily / DuckDuckGo)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Cleaned full-text content extracted by the Content Extraction Agent
    extracted_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Credibility Scoring (Fact Verification Agent) ───────────────────
    domain_authority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_age_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    citation_count_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trustworthiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100 overall

    # Any contradictions found vs. other sources, stored as structured notes
    verification_notes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Order in which this source was used/cited in the final report
    citation_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    research_session: Mapped["ResearchSession"] = relationship(back_populates="sources")

    def __repr__(self) -> str:
        return f"<Source id={self.id} domain={self.domain} trust={self.trustworthiness_score}>"
