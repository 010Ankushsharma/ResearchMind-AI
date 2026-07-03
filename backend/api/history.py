"""
api/history.py

Routes:
  GET    /api/history          - combined research history (sessions + report titles)
  DELETE /api/history/{id}     - delete a research session (cascades to sources/report/logs + vectors)
  GET    /api/history/search   - natural language search over past research, e.g.
                                  "what did I research last month?" (RAG-powered)
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.connection import get_db
from models.report import Report
from models.research_session import ResearchSession
from models.user import User
from rag.chroma_service import get_chroma_service
from tools.rag_tool import KnowledgeBaseSearchTool

router = APIRouter(prefix="/history", tags=["history"])


class HistoryItem(BaseModel):
    session_id: uuid.UUID
    query: str
    status: str
    report_id: uuid.UUID | None = None
    report_title: str | None = None
    created_at: str
    completed_at: str | None = None


class HistorySearchResult(BaseModel):
    chroma_vector_id: str
    text: str
    metadata: dict
    relevance_score: float | None = None


@router.get("", response_model=list[HistoryItem])
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    result = await db.execute(
        select(ResearchSession, Report)
        .outerjoin(Report, Report.research_session_id == ResearchSession.id)
        .where(ResearchSession.user_id == current_user.id)
        .order_by(ResearchSession.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    items = []
    for session, report in result.all():
        items.append(
            HistoryItem(
                session_id=session.id,
                query=session.query,
                status=session.status.value,
                report_id=report.id if report else None,
                report_title=report.title if report else None,
                created_at=session.created_at.isoformat(),
                completed_at=session.completed_at.isoformat() if session.completed_at else None,
            )
        )
    return items


@router.delete("/{session_id}", status_code=204)
async def delete_history_item(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Research session not found")

    # Remove vectors first (Postgres cascade handles sources/report/logs/knowledge_documents)
    get_chroma_service().delete_session_vectors(session_id)
    await db.delete(session)
    return None


@router.get("/search", response_model=list[HistorySearchResult])
async def search_history(
    q: str = Query(..., min_length=2, description='e.g. "what did I research last month about AI agents?"'),
    top_k: int = Query(default=8, ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    """
    Powers natural-language recall like "What did I research last month?" by
    semantically searching this user's entire knowledge base across all past
    research sessions (not scoped to a single session).
    """
    search_tool = KnowledgeBaseSearchTool()
    raw_results = search_tool._run(query=q, user_id=str(current_user.id), top_k=top_k)
    return [HistorySearchResult(**r) for r in raw_results]
