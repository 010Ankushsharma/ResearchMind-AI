"""
services/pdf_service.py

Renders a finished research report into a branded, multi-section PDF using
ReportLab (free, open-source). Produces:
  - Cover page (title, generated date, branding)
  - Table of contents
  - Report body (abstract, introduction, key findings, analysis,
    recommendations, conclusion)
  - Executive summary page (takeaways / risks / opportunities)
  - Charts (rendered via matplotlib, embedded as images)
  - References (citations in the requested style)
"""

from __future__ import annotations

import io
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")  # headless rendering — no display server needed
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from core.config import settings

# ── Brand palette (matches the platform's dark-mode UI accents) ──────────
BRAND_PRIMARY = colors.HexColor("#3B82F6")
BRAND_ACCENT = colors.HexColor("#8B5CF6")
BRAND_DARK = colors.HexColor("#111827")
BRAND_SUCCESS = colors.HexColor("#22C55E")
BRAND_WARNING = colors.HexColor("#F59E0B")
BRAND_DANGER = colors.HexColor("#EF4444")


@dataclass
class PDFReportRequest:
    report_id: uuid.UUID
    title: str
    sections: dict  # abstract, introduction, key_findings, analysis, recommendations, conclusion
    executive_summary_block: dict  # executive_summary, key_takeaways, risks, opportunities
    citations: dict  # {"apa": [...], "mla": [...], "ieee": [...]}
    chart_data: dict = field(default_factory=dict)  # {"source_distribution": {...}, ...}
    citation_style: str = "apa"
    include_cover_page: bool = True
    include_table_of_contents: bool = True
    include_charts: bool = True


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CoverTitle",
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            textColor=BRAND_DARK,
            spaceAfter=16,
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="CoverSubtitle",
            fontSize=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            fontSize=17,
            leading=22,
            textColor=BRAND_PRIMARY,
            spaceBefore=18,
            spaceAfter=10,
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyText2",
            fontSize=10.5,
            leading=16,
            spaceAfter=10,
            textColor=colors.HexColor("#1F2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="TOCEntry",
            fontSize=12,
            leading=20,
            textColor=BRAND_DARK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CitationEntry",
            fontSize=9.5,
            leading=14,
            spaceAfter=8,
            textColor=colors.HexColor("#374151"),
        )
    )
    return styles


def _build_cover_page(story: list, styles, request: PDFReportRequest) -> None:
    story.append(Spacer(1, 1.8 * inch))
    story.append(Paragraph(request.title, styles["CoverTitle"]))
    story.append(Paragraph("AI Research & Report Generation Platform", styles["CoverSubtitle"]))
    generated = datetime.now(timezone.utc).strftime("%B %d, %Y")
    story.append(Paragraph(f"Generated on {generated}", styles["CoverSubtitle"]))
    story.append(Spacer(1, 0.4 * inch))

    # Thin accent rule under the subtitle block
    rule = Table([[""]], colWidths=[2 * inch], rowHeights=[3])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BRAND_ACCENT)]))
    story.append(rule)
    story.append(PageBreak())


def _build_table_of_contents(story: list, styles, request: PDFReportRequest) -> None:
    story.append(Paragraph("Table of Contents", styles["SectionHeading"]))
    entries = [
        "1. Abstract",
        "2. Introduction",
        "3. Key Findings",
        "4. Analysis",
        "5. Recommendations",
        "6. Conclusion",
        "7. Executive Summary",
    ]
    if request.include_charts and request.chart_data:
        entries.append("8. Research Insights & Charts")
    entries.append(f"{len(entries) + 1}. References ({request.citation_style.upper()})")

    for entry in entries:
        story.append(Paragraph(entry, styles["TOCEntry"]))
    story.append(PageBreak())


def _build_body_sections(story: list, styles, request: PDFReportRequest) -> None:
    section_order = [
        ("Abstract", "abstract"),
        ("Introduction", "introduction"),
        ("Key Findings", "key_findings"),
        ("Analysis", "analysis"),
        ("Recommendations", "recommendations"),
        ("Conclusion", "conclusion"),
    ]
    for heading, key in section_order:
        text = request.sections.get(key) or "Not available."
        story.append(Paragraph(heading, styles["SectionHeading"]))
        for paragraph in str(text).split("\n\n"):
            if paragraph.strip():
                story.append(Paragraph(paragraph.strip(), styles["BodyText2"]))
    story.append(PageBreak())


def _build_executive_summary(story: list, styles, request: PDFReportRequest) -> None:
    block = request.executive_summary_block
    story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
    story.append(Paragraph(block.get("executive_summary") or "Not available.", styles["BodyText2"]))

    def _bullet_section(title: str, items: list[str], hex_color: str):
        if not items:
            return
        story.append(Paragraph(f'<font color="{hex_color}"><b>{title}</b></font>', styles["BodyText2"]))
        for item in items:
            story.append(Paragraph(f"&bull;&nbsp;&nbsp;{item}", styles["BodyText2"]))

    _bullet_section("Key Takeaways", block.get("key_takeaways", []), "#3B82F6")
    _bullet_section("Risks", block.get("risks", []), "#EF4444")
    _bullet_section("Opportunities", block.get("opportunities", []), "#22C55E")
    story.append(PageBreak())


def _render_chart_image(chart_title: str, chart_payload: dict) -> Image | None:
    """Renders a single chart (bar or pie, inferred from payload) to an in-memory PNG."""
    labels = chart_payload.get("labels", [])
    values = chart_payload.get("values", [])
    if not labels or not values:
        return None

    fig, ax = plt.subplots(figsize=(5.5, 3))
    chart_type = chart_payload.get("type", "bar")

    if chart_type == "pie":
        ax.pie(values, labels=labels, autopct="%1.0f%%", colors=plt.cm.Blues_r(
            [i / max(len(values), 1) for i in range(len(values))]
        ))
    else:
        ax.bar(labels, values, color="#3B82F6")
        ax.set_ylabel("Count")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)

    ax.set_title(chart_title, fontsize=11)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=5 * inch, height=2.7 * inch)


def _build_charts_section(story: list, styles, request: PDFReportRequest) -> None:
    if not request.include_charts or not request.chart_data:
        return

    story.append(Paragraph("Research Insights & Charts", styles["SectionHeading"]))
    for chart_title, payload in request.chart_data.items():
        image = _render_chart_image(chart_title.replace("_", " ").title(), payload)
        if image:
            story.append(image)
            story.append(Spacer(1, 12))
    story.append(PageBreak())


def _build_references_section(story: list, styles, request: PDFReportRequest) -> None:
    style_key = request.citation_style.lower()
    entries = request.citations.get(style_key, [])

    story.append(Paragraph(f"References ({style_key.upper()})", styles["SectionHeading"]))
    if not entries:
        story.append(Paragraph("No sources available.", styles["BodyText2"]))
        return

    for entry in entries:
        formatted = entry.get("formatted") if isinstance(entry, dict) else str(entry)
        story.append(Paragraph(formatted, styles["CitationEntry"]))


def build_pdf_report(request: PDFReportRequest) -> str:
    """
    Build the full PDF and save it to REPORTS_STORAGE_PATH.
    Returns the absolute file path of the generated PDF.
    """
    os.makedirs(settings.REPORTS_STORAGE_PATH, exist_ok=True)
    filename = f"report_{request.report_id}.pdf"
    file_path = os.path.join(settings.REPORTS_STORAGE_PATH, filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=LETTER,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        title=request.title,
        author="Multi-Agent Research Platform",
    )

    styles = _build_styles()
    story: list = []

    if request.include_cover_page:
        _build_cover_page(story, styles, request)
    if request.include_table_of_contents:
        _build_table_of_contents(story, styles, request)

    _build_body_sections(story, styles, request)
    _build_executive_summary(story, styles, request)
    _build_charts_section(story, styles, request)
    _build_references_section(story, styles, request)

    doc.build(story)
    return file_path
