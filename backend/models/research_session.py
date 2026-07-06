"""
models/research_session.py

ResearchSession ORM model.

Represents a single research run initiated by a user (e.g. "Latest
advancements in AI Agents"). Tracks the overall workflow status across
all agents, and links to sources, knowledge documents, and the final report.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class SessionStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RESEARCHING = "researching"
    EXTRACTING = "extracting"
    VERIFYING = "verifying"
    SUMMARIZING = "summarizing"
    WRITING_REPORT = "writing_report"
    GENERATING_EXECUTIVE_SUMMARY = "generating_executive_summary"
    GENERATING_CITATIONS = "generating_citations"
    EXPORTING_PDF = "exporting_pdf"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    query: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        default=SessionStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Structured plan produced by the Research Coordinator Agent
    research_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 0-100 progress indicator for the live "agent activity" UI
    progress_percent: Mapped[int] = mapped_column(default=0, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(back_populates="research_sessions")

    sources: Mapped[list["Source"]] = relationship(
        back_populates="research_session", cascade="all, delete-orphan"
    )
    knowledge_documents: Mapped[list["KnowledgeDocument"]] = relationship(
        back_populates="research_session", cascade="all, delete-orphan"
    )
    agent_logs: Mapped[list["AgentLog"]] = relationship(
        back_populates="research_session", cascade="all, delete-orphan", order_by="AgentLog.created_at"
    )
    report: Mapped["Report | None"] = relationship(
        back_populates="research_session", cascade="all, delete-orphan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<ResearchSession id={self.id} status={self.status} query={self.query[:40]!r}>"
