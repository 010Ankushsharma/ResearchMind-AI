"""
models/report.py

Report ORM model.

Stores the final output of the agent pipeline for a research session:
the structured report body (title, abstract, sections), the executive
summary, generated citations, and the exported PDF file path.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class CitationStyle(str, enum.Enum):
    APA = "apa"
    MLA = "mla"
    IEEE = "ieee"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    research_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(512), nullable=False)

    # ── Report Writer Agent output ───────────────────────────────────────
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    introduction: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Summarization Agent output ───────────────────────────────────────
    short_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    medium_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailed_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Executive Summary Agent output ───────────────────────────────────
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_takeaways: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list[str]
    risks: Mapped[dict | None] = mapped_column(JSONB, nullable=True)          # list[str]
    opportunities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # list[str]

    # ── Citation Agent output ────────────────────────────────────────────
    citations_apa: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    citations_mla: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    citations_ieee: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    default_citation_style: Mapped[CitationStyle] = mapped_column(
        Enum(CitationStyle, name="citation_style"), default=CitationStyle.APA, nullable=False
    )

    # ── PDF Generation Agent output ──────────────────────────────────────
    pdf_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Chart data backing the AI Insights Dashboard for this report
    chart_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    version: Mapped[int] = mapped_column(default=1, nullable=False)  # bumped on "expand section" edits

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────
    research_session: Mapped["ResearchSession"] = relationship(back_populates="report")
    user: Mapped["User"] = relationship(back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} title={self.title[:40]!r} v{self.version}>"
