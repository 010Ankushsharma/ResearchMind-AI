"""
agents/pdf_generation.py

Agent #10 — PDF Generation Agent

Responsibilities:
  Generate:
    - Branded PDF report
    - Cover page
    - Table of contents
    - Charts
    - References

Like the Knowledge Base Agent, PDF rendering is a deterministic operation
(ReportLab layout, not language generation), so this module is a thin
orchestration wrapper around `services/pdf_service.py`. A CrewAI `Agent`
shell is provided for pipeline/logging consistency, but the actual work
is done by `generate_report_pdf()` — no LLM call needed.
"""

from __future__ import annotations

import logging
import uuid

from crewai import Agent

from agents.llm_provider import TaskComplexity, get_llm
from services.pdf_service import PDFReportRequest, build_pdf_report

logger = logging.getLogger(__name__)


def build_pdf_generation_agent() -> Agent:
    """
    Lightweight CrewAI Agent shell for the PDF export step, kept consistent
    with the rest of the pipeline (e.g. for unified agent-activity logging).
    Prefer calling `generate_report_pdf()` directly for the actual export.
    """
    llm = get_llm(complexity=TaskComplexity.FAST, temperature=0.0)

    return Agent(
        role="PDF Production Specialist",
        goal="Render the finished research report into a polished, branded PDF deliverable.",
        backstory=(
            "You are a meticulous document production specialist who ensures every "
            "exported report looks professional and is correctly paginated — cover "
            "page, table of contents, charts, and references all properly formatted."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


async def generate_report_pdf(
    *,
    report_id: uuid.UUID,
    title: str,
    sections: dict,
    executive_summary_block: dict,
    citations: dict,
    chart_data: dict | None = None,
    citation_style: str = "apa",
    include_cover_page: bool = True,
    include_table_of_contents: bool = True,
    include_charts: bool = True,
) -> str:
    """
    Direct service call (no LLM) that renders the full report into a PDF
    via ReportLab and returns the saved file path.
    """
    request = PDFReportRequest(
        report_id=report_id,
        title=title,
        sections=sections,
        executive_summary_block=executive_summary_block,
        citations=citations,
        chart_data=chart_data or {},
        citation_style=citation_style,
        include_cover_page=include_cover_page,
        include_table_of_contents=include_table_of_contents,
        include_charts=include_charts,
    )

    pdf_path = build_pdf_report(request)
    logger.info("PDF Generation Agent produced report at %s", pdf_path)
    return pdf_path
