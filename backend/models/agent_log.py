"""
models/agent_log.py

AgentLog ORM model.

Every action taken by an agent in the CrewAI pipeline is recorded here.
Powers the "Live agent activity" / "Agent logs" panel in the Research
Workspace UI, and gives a durable audit trail of the whole run.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class AgentName(str, enum.Enum):
    RESEARCH_COORDINATOR = "research_coordinator"
    WEB_RESEARCH = "web_research"
    CONTENT_EXTRACTION = "content_extraction"
    FACT_VERIFICATION = "fact_verification"
    KNOWLEDGE_BASE = "knowledge_base"
    SUMMARIZATION = "summarization"
    REPORT_WRITER = "report_writer"
    CITATION = "citation"
    EXECUTIVE_SUMMARY = "executive_summary"
    PDF_GENERATION = "pdf_generation"


class LogLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    research_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    agent_name: Mapped[AgentName] = mapped_column(
        Enum(AgentName, name="agent_name"), nullable=False, index=True
    )
    level: Mapped[LogLevel] = mapped_column(
        Enum(LogLevel, name="log_level"), default=LogLevel.INFO, nullable=False
    )

    # Short human-readable action, e.g. "Searching the web for 5 subtopics"
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Free-form structured payload (tool calls, token usage, raw output snippet)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # ── Relationships ─────────────────────────────────────────────────────
    research_session: Mapped["ResearchSession"] = relationship(back_populates="agent_logs")

    def __repr__(self) -> str:
        return f"<AgentLog agent={self.agent_name} level={self.level} msg={self.message[:40]!r}>"
