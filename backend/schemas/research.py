"""
schemas/research.py

Pydantic schemas for research session creation/status, sources discovered
during research, and the live agent activity log feed.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.agent_log import AgentName, LogLevel
from models.research_session import SessionStatus


# ── Research Session ────────────────────────────────────────────────────

class ResearchSessionCreate(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000, description="Research topic or question")
    max_sources: int | None = Field(default=10, ge=1, le=20)
    citation_style: str | None = Field(default="apa", pattern="^(apa|mla|ieee)$")


class ResearchSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    query: str
    status: SessionStatus
    research_plan: dict | None = None
    progress_percent: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ResearchSessionSummary(BaseModel):
    """Lightweight shape used in research history lists."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    query: str
    status: SessionStatus
    progress_percent: int
    created_at: datetime


# ── Source ───────────────────────────────────────────────────────────────

class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    title: str | None = None
    domain: str | None = None
    snippet: str | None = None
    domain_authority_score: float | None = None
    source_age_score: float | None = None
    citation_count_score: float | None = None
    trustworthiness_score: float | None = None
    published_date: datetime | None = None
    citation_index: int | None = None


# ── Agent Log (live activity feed) ───────────────────────────────────────

class AgentLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_name: AgentName
    level: LogLevel
    message: str
    details: dict | None = None
    duration_ms: float | None = None
    created_at: datetime


class AgentStatusItem(BaseModel):
    """Used by GET /api/agents/status to show each agent's current state."""
    agent_name: AgentName
    is_active: bool
    current_task: str | None = None
    last_updated: datetime | None = None


# ── Follow-up Research ───────────────────────────────────────────────────

class FollowUpRequest(BaseModel):
    research_session_id: uuid.UUID
    instruction: str = Field(
        ..., min_length=3, description='e.g. "Expand section 3" or "Compare with previous report"'
    )
