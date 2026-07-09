"""
tests/test_research_coordinator.py

Unit tests for parse_research_plan() in agents/research_coordinator.py —
the defensive JSON parsing logic that handles whatever an LLM hands back
(clean JSON, markdown-fenced JSON, or malformed garbage).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.research_coordinator import parse_research_plan  # noqa: E402


class TestParseResearchPlan:
    def test_parses_clean_json(self):
        raw = '{"main_topic": "AI Agents", "subtopics": [], "estimated_source_count": 10}'
        result = parse_research_plan(raw)
        assert result["main_topic"] == "AI Agents"
        assert result["estimated_source_count"] == 10

    def test_strips_markdown_json_fence(self):
        raw = '```json\n{"main_topic": "AI Agents", "subtopics": []}\n```'
        result = parse_research_plan(raw)
        assert result["main_topic"] == "AI Agents"

    def test_strips_plain_markdown_fence_without_json_label(self):
        raw = '```\n{"main_topic": "Quantum Computing", "subtopics": []}\n```'
        result = parse_research_plan(raw)
        assert result["main_topic"] == "Quantum Computing"

    def test_handles_leading_trailing_whitespace(self):
        raw = '\n\n  {"main_topic": "Battery Tech", "subtopics": []}  \n\n'
        result = parse_research_plan(raw)
        assert result["main_topic"] == "Battery Tech"

    def test_malformed_json_returns_safe_fallback(self):
        raw = "This is not JSON at all, the model misbehaved."
        result = parse_research_plan(raw)
        assert result["subtopics"] == []
        assert "parse_error" in result
        assert "suggested_report_sections" in result
        assert len(result["suggested_report_sections"]) > 0

    def test_fallback_includes_standard_report_sections(self):
        result = parse_research_plan("not json")
        expected_sections = {"Introduction", "Key Findings", "Analysis", "Recommendations", "Conclusion"}
        assert expected_sections.issubset(set(result["suggested_report_sections"]))

    def test_preserves_subtopics_structure(self):
        raw = (
            '{"main_topic": "AI Agents", "subtopics": '
            '[{"title": "Frameworks", "search_queries": ["q1"], "rationale": "r1"}]}'
        )
        result = parse_research_plan(raw)
        assert len(result["subtopics"]) == 1
        assert result["subtopics"][0]["title"] == "Frameworks"
