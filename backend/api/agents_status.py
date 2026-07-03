"""
api/agents_status.py

Routes:
  GET /api/agents/status?research_session_id=...
    Returns the current state of all 10 agents in the pipeline for a given
    research session, derived from the session's current SessionStatus and
    its most recent AgentLog entries. Powers the "Live agent activity" /
    "Task progress" panel in the Research Workspace UI.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.connection import get_db
from models.agent_log import AgentLog, AgentName
from models.research_session import ResearchSession, SessionStatus
from models.user import User
from schemas.research import AgentStatusItem

router = APIRouter(prefix="/agents", tags=["agents"])

# Maps each SessionStatus to the AgentName that is actively running during it.
# Used to mark exactly one agent "active" at a time in the pipeline view.
_STATUS_TO_ACTIVE_AGENT: dict[SessionStatus, AgentName] = {
    SessionStatus.PLANNING: AgentName.RESEARCH_COORDINATOR,
    SessionStatus.RESEARCHING: AgentName.WEB_RESEARCH,
    SessionStatus.EXTRACTING: AgentName.CONTENT_EXTRACTION,
    SessionStatus.VERIFYING: AgentName.FACT_VERIFICATION,
    SessionStatus.SUMMARIZING: AgentName.KNOWLEDGE_BASE,  # knowledge storage happens just before summarization
    SessionStatus.WRITING_REPORT: AgentName.REPORT_WRITER,
    SessionStatus.GENERATING_EXECUTIVE_SUMMARY: AgentName.EXECUTIVE_SUMMARY,
    SessionStatus.GENERATING_CITATIONS: AgentName.CITATION,
    SessionStatus.EXPORTING_PDF: AgentName.PDF_GENERATION,
}

# Defines the pipeline order so agents that have already finished show as
# inactive-but-complete rather than perpetually "not started".
_AGENT_PIPELINE_ORDER = [
    AgentName.RESEARCH_COORDINATOR,
    AgentName.WEB_RESEARCH,
    AgentName.CONTENT_EXTRACTION,
    AgentName.FACT_VERIFICATION,
    AgentName.KNOWLEDGE_BASE,
    AgentName.SUMMARIZATION,
    AgentName.REPORT_WRITER,
    AgentName.EXECUTIVE_SUMMARY,
    AgentName.CITATION,
    AgentName.PDF_GENERATION,
]


@router.get("/status", response_model=list[AgentStatusItem])
async def get_agents_status(
    research_session_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ResearchSession, research_session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Research session not found")

    # Most recent log entry per agent, used for "current_task" text + timestamps.
    result = await db.execute(
        select(AgentLog)
        .where(AgentLog.research_session_id == research_session_id)
        .order_by(AgentLog.created_at.desc())
    )
    logs = result.scalars().all()

    latest_by_agent: dict[AgentName, AgentLog] = {}
    for log in logs:
        if log.agent_name not in latest_by_agent:
            latest_by_agent[log.agent_name] = log

    active_agent = _STATUS_TO_ACTIVE_AGENT.get(session.status)
    is_terminal = session.status in (SessionStatus.COMPLETED, SessionStatus.FAILED)
    active_index = _AGENT_PIPELINE_ORDER.index(active_agent) if active_agent else (
        len(_AGENT_PIPELINE_ORDER) if is_terminal and session.status == SessionStatus.COMPLETED else -1
    )

    items: list[AgentStatusItem] = []
    for idx, agent_name in enumerate(_AGENT_PIPELINE_ORDER):
        log = latest_by_agent.get(agent_name)
        has_run = idx < active_index or (log is not None and session.status == SessionStatus.COMPLETED)
        is_active = agent_name == active_agent and not is_terminal

        if is_active:
            current_task = log.message if log else f"{agent_name.value.replace('_', ' ').title()} in progress..."
        elif has_run:
            current_task = log.message if log else "Completed"
        else:
            current_task = None

        items.append(
            AgentStatusItem(
                agent_name=agent_name,
                is_active=is_active,
                current_task=current_task,
                last_updated=log.created_at if log else None,
            )
        )

    return items
