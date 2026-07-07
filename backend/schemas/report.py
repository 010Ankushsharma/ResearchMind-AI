"""
schemas/report.py

Pydantic schemas for the final Report object: structured sections,
3-tier summaries, executive summary, citations, and PDF export requests.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.report import CitationStyle


# ── Summaries ────────────────────────────────────────────────────────────

class SummaryBlock(BaseModel):
    short_summary: str | None = None
    medium_summary: str | None = None
    detailed_summary: str | None = None


# ── Executive Summary ───────────────────────────────────────────────────

class ExecutiveSummaryBlock(BaseModel):
    executive_summary: str | None = None
    key_takeaways: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)


# ── Citations ────────────────────────────────────────────────────────────

class CitationEntry(BaseModel):
    source_id: uuid.UUID
    formatted: str  # the rendered citation string in the requested style


class CitationsBlock(BaseModel):
    apa: list[CitationEntry] = Field(default_factory=list)
    mla: list[CitationEntry] = Field(default_factory=list)
    ieee: list[CitationEntry] = Field(default_factory=list)
    default_style: CitationStyle = CitationStyle.APA


# ── Report ───────────────────────────────────────────────────────────────

class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_session_id: uuid.UUID
    user_id: uuid.UUID
    title: str

    abstract: str | None = None
    introduction: str | None = None
    key_findings: str | None = None
    analysis: str | None = None
    recommendations: str | None = None
    conclusion: str | None = None

    short_summary: str | None = None
    medium_summary: str | None = None
    detailed_summary: str | None = None

    executive_summary: str | None = None
    key_takeaways: list[str] | None = None
    risks: list[str] | None = None
    opportunities: list[str] | None = None

    default_citation_style: CitationStyle
    pdf_file_path: str | None = None
    pdf_generated_at: datetime | None = None
    chart_data: dict | None = None

    version: int
    created_at: datetime
    updated_at: datetime


class ReportSummary(BaseModel):
    """Lightweight shape for report lists / history."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_session_id: uuid.UUID
    title: str
    version: int
    created_at: datetime


# ── PDF Export ───────────────────────────────────────────────────────────

class PDFExportRequest(BaseModel):
    report_id: uuid.UUID
    include_charts: bool = True
    include_cover_page: bool = True
    include_table_of_contents: bool = True
    citation_style: CitationStyle = CitationStyle.APA


class PDFExportResponse(BaseModel):
    report_id: uuid.UUID
    pdf_url: str
    generated_at: datetime
