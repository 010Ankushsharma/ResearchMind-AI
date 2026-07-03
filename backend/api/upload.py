"""
api/upload.py

Routes:
  POST /api/upload  - upload a document (PDF / TXT / Markdown) to seed or
                       augment a research session's knowledge base

Supported formats: .pdf, .txt, .md
Extracted text is chunked + embedded + stored in ChromaDB exactly like
web-sourced content, so uploaded documents are retrievable by the
Summarization / Report Writer agents and by knowledge base search.
"""

from __future__ import annotations

import io
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.connection import get_db
from models.research_session import ResearchSession
from models.source import Source
from models.user import User
from rag.chroma_service import get_chroma_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB


class UploadResponse(BaseModel):
    source_id: uuid.UUID
    filename: str
    chunks_stored: int
    characters_extracted: int


def _extract_text(filename: str, raw_bytes: bytes) -> str:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix in {".txt", ".md"}:
        return raw_bytes.decode("utf-8", errors="ignore")

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
    )


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    research_session_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ResearchSession, research_session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Research session not found")

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB limit",
        )

    text = _extract_text(file.filename or "upload", raw_bytes)
    if not text.strip():
        raise HTTPException(status_code=422, detail="No extractable text found in the uploaded file")

    # Record it as a Source so it shows up alongside web sources, citations, etc.
    source = Source(
        research_session_id=research_session_id,
        url=f"upload://{file.filename}",
        title=file.filename,
        domain="user-upload",
        extracted_content=text,
        trustworthiness_score=100.0,  # user-provided documents are treated as fully trusted
    )
    db.add(source)
    await db.flush()
    await db.refresh(source)

    chroma = get_chroma_service()
    vector_ids = await chroma.store_source_content(
        research_session_id=research_session_id,
        user_id=current_user.id,
        source_id=source.id,
        text=text,
        extra_metadata={"url": source.url, "trustworthiness_score": 100.0, "is_user_upload": True},
    )

    logger.info("Ingested uploaded file %s into %d chunks", file.filename, len(vector_ids))

    return UploadResponse(
        source_id=source.id,
        filename=file.filename or "upload",
        chunks_stored=len(vector_ids),
        characters_extracted=len(text),
    )
