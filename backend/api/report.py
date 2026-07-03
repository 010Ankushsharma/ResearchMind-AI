"""
api/report.py

Routes:
  GET  /api/report/{report_id}            - full report content
  GET  /api/report/by-session/{session_id} - lookup a report by its research session
  POST /api/report/{report_id}/follow-up   - "Expand section 3" / "Compare with previous report"
  POST /api/export/pdf                     - (re)export a report to PDF and get a download URL
  GET  /api/export/pdf/{report_id}/download - stream the generated PDF file
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.pdf_generation import generate_report_pdf
from core.security import get_current_user
from crews.research_crew import apply_follow_up
from database.connection import get_db
from models.report import Report
from models.research_session import ResearchSession
from models.user import User
from schemas.report import PDFExportRequest, PDFExportResponse, ReportRead

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report"])


async def _get_owned_report(report_id: uuid.UUID, db: AsyncSession, current_user: User) -> Report:
    report = await db.get(Report, report_id)
    if not report or report.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/report/{report_id}", response_model=ReportRead)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_owned_report(report_id, db, current_user)


@router.get("/report/by-session/{session_id}", response_model=ReportRead)
async def get_report_by_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Research session not found")

    result = await db.execute(select(Report).where(Report.research_session_id == session_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not yet generated for this session")
    return report


@router.post("/report/{report_id}/follow-up", response_model=ReportRead)
async def follow_up_on_report(
    report_id: uuid.UUID,
    instruction: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Follow-up editing — e.g. "Expand section 3" or "Make the recommendations
    more actionable". Re-invokes the Report Writer agent with the
    instruction and the report's current content as context, and persists
    whichever section(s) the model actually revised.

    Note: this runs the LLM call synchronously within the request (a single
    revision is typically one call, ~5-20s) rather than dispatching to
    Celery — if your deployment sees heavy follow-up traffic, move this to
    `tasks.research_tasks` like the main pipeline.
    """
    # Ownership check up front, before doing any LLM work.
    await _get_owned_report(report_id, db, current_user)

    try:
        await apply_follow_up(report_id, instruction)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Re-fetch to return the freshly committed state.
    refreshed = await db.get(Report, report_id)
    await db.refresh(refreshed)
    return refreshed


@router.post("/export/pdf", response_model=PDFExportResponse)
async def export_report_pdf(
    payload: PDFExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-generate (or generate for the first time) the PDF for a report with custom export options."""
    report = await _get_owned_report(payload.report_id, db, current_user)

    sections = {
        "title": report.title,
        "abstract": report.abstract,
        "introduction": report.introduction,
        "key_findings": report.key_findings,
        "analysis": report.analysis,
        "recommendations": report.recommendations,
        "conclusion": report.conclusion,
    }
    exec_block = {
        "executive_summary": report.executive_summary,
        "key_takeaways": report.key_takeaways or [],
        "risks": report.risks or [],
        "opportunities": report.opportunities or [],
    }
    citations = {
        "apa": report.citations_apa or [],
        "mla": report.citations_mla or [],
        "ieee": report.citations_ieee or [],
    }

    pdf_path = await generate_report_pdf(
        report_id=report.id,
        title=report.title,
        sections=sections,
        executive_summary_block=exec_block,
        citations=citations,
        chart_data=report.chart_data or {},
        citation_style=payload.citation_style.value,
        include_cover_page=payload.include_cover_page,
        include_table_of_contents=payload.include_table_of_contents,
        include_charts=payload.include_charts,
    )

    report.pdf_file_path = pdf_path
    report.pdf_generated_at = datetime.now(timezone.utc)
    await db.flush()

    return PDFExportResponse(
        report_id=report.id,
        pdf_url=f"/api/export/pdf/{report.id}/download",
        generated_at=report.pdf_generated_at,
    )


@router.get("/export/pdf/{report_id}/download")
async def download_report_pdf(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = await _get_owned_report(report_id, db, current_user)
    if not report.pdf_file_path:
        raise HTTPException(status_code=404, detail="PDF has not been generated yet for this report")

    return FileResponse(
        path=report.pdf_file_path,
        media_type="application/pdf",
        filename=f"{report.title[:60].strip().replace(' ', '_') or 'report'}.pdf",
    )
