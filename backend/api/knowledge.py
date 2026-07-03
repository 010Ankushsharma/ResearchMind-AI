"""
api/knowledge.py

Routes powering the "Knowledge Base" dashboard page:
  GET /api/knowledge/search   - semantic search across stored documents
  GET /api/knowledge/documents - browse/filter stored documents (paginated)
  GET /api/knowledge/topics    - distinct topic tags for the "topic filters" UI control
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.connection import get_db
from models.knowledge_document import KnowledgeDocument
from models.user import User
from tools.rag_tool import KnowledgeBaseSearchTool

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeSearchResult(BaseModel):
    chroma_vector_id: str
    text: str
    metadata: dict
    relevance_score: float | None = None


class KnowledgeDocumentItem(BaseModel):
    id: uuid.UUID
    research_session_id: uuid.UUID
    source_id: uuid.UUID | None
    chunk_text: str
    chunk_index: int
    token_count: int | None
    metadata_tags: dict | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/search", response_model=list[KnowledgeSearchResult])
async def search_knowledge_base(
    q: str = Query(..., min_length=2),
    research_session_id: uuid.UUID | None = None,
    top_k: int = Query(default=10, ge=1, le=30),
    current_user: User = Depends(get_current_user),
):
    """Free-text semantic search box on the Knowledge Base page."""
    search_tool = KnowledgeBaseSearchTool()
    results = search_tool._run(
        query=q,
        research_session_id=str(research_session_id) if research_session_id else None,
        user_id=str(current_user.id),
        top_k=top_k,
    )
    return [KnowledgeSearchResult(**r) for r in results]


@router.get("/documents", response_model=list[KnowledgeDocumentItem])
async def list_knowledge_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    research_session_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """Browsable list view (with optional session filter) for the Knowledge Base page."""
    stmt = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.user_id == current_user.id)
        .order_by(KnowledgeDocument.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if research_session_id:
        stmt = stmt.where(KnowledgeDocument.research_session_id == research_session_id)

    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        KnowledgeDocumentItem(
            id=d.id,
            research_session_id=d.research_session_id,
            source_id=d.source_id,
            chunk_text=d.chunk_text[:500],  # truncate for list view; full text via search
            chunk_index=d.chunk_index,
            token_count=d.token_count,
            metadata_tags=d.metadata_tags,
            created_at=d.created_at.isoformat(),
        )
        for d in docs
    ]


@router.get("/topics", response_model=list[str])
async def list_knowledge_topics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Distinct topic tags across the user's knowledge base, used to populate
    the "Topic filters" control on the Knowledge Base page.
    """
    result = await db.execute(
        select(KnowledgeDocument.metadata_tags).where(
            KnowledgeDocument.user_id == current_user.id,
            KnowledgeDocument.metadata_tags.isnot(None),
        )
    )
    topics: set[str] = set()
    for (tags,) in result.all():
        if isinstance(tags, dict):
            extracted = tags.get("topics")
            if isinstance(extracted, list):
                topics.update(str(t) for t in extracted)
    return sorted(topics)
