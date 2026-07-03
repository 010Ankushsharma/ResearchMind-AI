"""
api/research.py

Routes:
  POST /api/research              - start a new research session
  GET  /api/research              - list current user's research history
  GET  /api/research/{id}         - get session status/progress
  GET  /api/research/{id}/sources - list discovered sources + credibility scores
  GET  /api/research/{id}/logs    - live agent activity log feed

Note: research execution is dispatched to a Celery worker
(`tasks.research_tasks.run_research_task.delay(...)`) rather than running
in-process, so a restart of the API process never silently loses an
in-flight research run. The worker is wired up in docker-compose.yml.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import get_current_user
from database.connection import get_db
from main import limiter
from models.agent_log import AgentLog
from models.research_session import ResearchSession, SessionStatus
from models.source import Source
from models.user import User
from schemas.research import (
    AgentLogRead,
    ResearchSessionCreate,
    ResearchSessionRead,
    ResearchSessionSummary,
    SourceRead,
)
from tasks.research_tasks import run_research_task

router = APIRouter(prefix="/research", tags=["research"])

_NON_TERMINAL_STATUSES = [
    s for s in SessionStatus if s not in (SessionStatus.COMPLETED, SessionStatus.FAILED)
]


@router.post("", response_model=ResearchSessionRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # stricter than the global default — this endpoint fires off
                             # 10+ chained LLM/search calls per request, unlike everything else
async def start_research(
    request: Request,  # required by slowapi's @limiter.limit, unused otherwise
    payload: ResearchSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Kick off a new multi-agent research run for the given query.

    Dispatches to a Celery worker (`tasks.research_tasks.run_research_task`)
    rather than running in-process — if the API pod restarts mid-run, the
    worker keeps going independently and the task can be retried, instead
    of the work silently vanishing with the request.
    """
    # ── Abuse / cost guardrail ──────────────────────────────────────────
    # Caps concurrent in-flight sessions per user so one person can't
    # exhaust the platform's shared free-tier LLM/search quotas by firing
    # off many runs at once.
    active_count = await db.scalar(
        select(func.count(ResearchSession.id)).where(
            ResearchSession.user_id == current_user.id,
            ResearchSession.status.in_(_NON_TERMINAL_STATUSES),
        )
    )
    if (active_count or 0) >= settings.MAX_CONCURRENT_RESEARCH_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"You already have {active_count} research session(s) in progress "
                f"(limit: {settings.MAX_CONCURRENT_RESEARCH_SESSIONS}). "
                f"Please wait for one to finish before starting another."
            ),
        )

    session = ResearchSession(user_id=current_user.id, query=payload.query)
    db.add(session)
    await db.flush()
    await db.refresh(session)

    current_user.research_count += 1
    await db.flush()

    run_research_task.delay(
        str(session.id),
        payload.query,
        str(current_user.id),
        payload.max_sources or 10,
        payload.citation_style or "apa",
    )

    return session


@router.get("", response_model=list[ResearchSessionSummary])
async def list_research_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    offset: int = 0,
):
    """Research history — used by the Home page's 'Recent research' panel."""
    result = await db.execute(
        select(ResearchSession)
        .where(ResearchSession.user_id == current_user.id)
        .order_by(ResearchSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=ResearchSessionRead)
async def get_research_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Research session not found")
    return session


@router.get("/{session_id}/sources", response_model=list[SourceRead])
async def get_research_sources(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Research session not found")

    result = await db.execute(
        select(Source)
        .where(Source.research_session_id == session_id)
        .order_by(Source.trustworthiness_score.desc().nullslast())
    )
    return result.scalars().all()


@router.get("/{session_id}/logs", response_model=list[AgentLogRead])
async def get_research_logs(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Powers the live 'Agent logs' panel — poll this endpoint while a session is running."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Research session not found")

    result = await db.execute(
        select(AgentLog)
        .where(AgentLog.research_session_id == session_id)
        .order_by(AgentLog.created_at.asc())
    )
    return result.scalars().all()
