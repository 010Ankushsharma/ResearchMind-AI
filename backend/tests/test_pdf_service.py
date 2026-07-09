"""
tests/test_pdf_service.py

Unit tests for services/pdf_service.py — verifies the PDF builder produces
a valid, non-trivial PDF file from report data, without needing a DB,
LLM, or network connection (ReportLab + matplotlib run fully offline).
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from services.pdf_service import PDFReportRequest, build_pdf_report  # noqa: E402


@pytest.fixture
def sample_pdf_request(tmp_path, monkeypatch) -> PDFReportRequest:
    # Redirect report storage to a temp directory so the test never touches
    # the real backend/storage/reports folder.
    monkeypatch.setattr("services.pdf_service.settings.REPORTS_STORAGE_PATH", str(tmp_path))

    return PDFReportRequest(
        report_id=uuid.uuid4(),
        title="The State of Autonomous AI Agents in 2026",
        sections={
            "abstract": "A brief overview of recent AI agent advancements.",
            "introduction": "Agents have evolved significantly.\n\nThis report covers key trends.",
            "key_findings": "Multi-agent systems are gaining traction.",
            "analysis": "Coordination remains a key challenge.",
            "recommendations": "Start with narrow, well-scoped use cases.",
            "conclusion": "The field is maturing quickly.",
        },
        executive_summary_block={
            "executive_summary": "AI agents are moving from research to production.",
            "key_takeaways": ["Specialization beats generalization", "Adoption is accelerating"],
            "risks": ["Coordination overhead", "Vendor lock-in"],
            "opportunities": ["Early-mover efficiency gains"],
        },
        citations={
            "apa": [{"source_id": "abc", "formatted": "Nature. (2026). Example Article."}],
            "mla": [{"source_id": "abc", "formatted": '"Example Article." Nature, 2026.'}],
            "ieee": [{"source_id": "abc", "formatted": '[1] Nature, "Example Article," 2026.'}],
        },
        chart_data={
            "source_trustworthiness": {
                "type": "bar",
                "labels": ["nature.com", "arxiv.org"],
                "values": [92, 85],
            }
        },
        citation_style="apa",
    )


class TestBuildPdfReport:
    def test_produces_a_file_at_the_returned_path(self, sample_pdf_request):
        path = build_pdf_report(sample_pdf_request)
        assert Path(path).exists()

    def test_output_is_a_valid_pdf(self, sample_pdf_request):
        path = build_pdf_report(sample_pdf_request)
        with open(path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_file_is_non_trivial_in_size(self, sample_pdf_request):
        path = build_pdf_report(sample_pdf_request)
        assert Path(path).stat().st_size > 2000  # a real multi-page PDF, not an empty stub

    def test_filename_includes_report_id(self, sample_pdf_request):
        path = build_pdf_report(sample_pdf_request)
        assert str(sample_pdf_request.report_id) in path

    def test_handles_missing_optional_sections_gracefully(self, sample_pdf_request, tmp_path, monkeypatch):
        monkeypatch.setattr("services.pdf_service.settings.REPORTS_STORAGE_PATH", str(tmp_path))
        sample_pdf_request.sections["conclusion"] = None
        sample_pdf_request.executive_summary_block["risks"] = []
        path = build_pdf_report(sample_pdf_request)
        assert Path(path).exists()

    def test_can_disable_cover_page_and_toc(self, sample_pdf_request, tmp_path, monkeypatch):
        monkeypatch.setattr("services.pdf_service.settings.REPORTS_STORAGE_PATH", str(tmp_path))
        sample_pdf_request.include_cover_page = False
        sample_pdf_request.include_table_of_contents = False
        path = build_pdf_report(sample_pdf_request)
        assert Path(path).exists()

    def test_handles_empty_citations(self, sample_pdf_request, tmp_path, monkeypatch):
        monkeypatch.setattr("services.pdf_service.settings.REPORTS_STORAGE_PATH", str(tmp_path))
        sample_pdf_request.citations = {"apa": [], "mla": [], "ieee": []}
        path = build_pdf_report(sample_pdf_request)
        assert Path(path).exists()
