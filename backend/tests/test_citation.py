"""
tests/test_citation.py

Unit tests for the deterministic citation formatters in agents/citation.py.
No LLM, DB, or network access required — pure function tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.citation import (  # noqa: E402
    _publisher_from_domain,
    _safe_year,
    format_apa,
    format_ieee,
    format_mla,
    generate_all_citations,
)


class TestSafeYear:
    def test_valid_iso_date_returns_year(self):
        assert _safe_year("2026-03-15T00:00:00Z") == "2026"

    def test_none_returns_no_date_marker(self):
        assert _safe_year(None) == "n.d."

    def test_malformed_date_returns_no_date_marker(self):
        assert _safe_year("not-a-date") == "n.d."


class TestPublisherFromDomain:
    def test_extracts_and_titlecases_name(self):
        assert _publisher_from_domain("nature.com") == "Nature"

    def test_handles_hyphenated_domain(self):
        assert _publisher_from_domain("example-blog.com") == "Example Blog"

    def test_none_domain_returns_unknown(self):
        assert _publisher_from_domain(None) == "Unknown Publisher"


class TestFormatters:
    def test_apa_includes_publisher_year_title_url(self, sample_sources):
        source = sample_sources[0]
        result = format_apa(source)
        assert "Nature" in result
        assert "2026" in result
        assert source["title"] in result
        assert source["url"] in result

    def test_apa_handles_missing_date_as_no_date(self, sample_sources):
        result = format_apa(sample_sources[1])
        assert "n.d." in result

    def test_mla_wraps_title_in_quotes(self, sample_sources):
        result = format_mla(sample_sources[0])
        assert f'"{sample_sources[0]["title"]}."' in result

    def test_ieee_includes_bracketed_index(self, sample_sources):
        result = format_ieee(sample_sources[0], index=3)
        assert result.startswith("[3]")


class TestGenerateAllCitations:
    def test_generates_all_three_styles_for_every_source(self, sample_sources):
        result = generate_all_citations(sample_sources)
        assert set(result.keys()) == {"apa", "mla", "ieee"}
        assert len(result["apa"]) == len(sample_sources)
        assert len(result["mla"]) == len(sample_sources)
        assert len(result["ieee"]) == len(sample_sources)

    def test_each_entry_includes_source_id(self, sample_sources):
        result = generate_all_citations(sample_sources)
        for entry in result["apa"]:
            assert entry["source_id"] is not None

    def test_ieee_indices_are_sequential_starting_at_one(self, sample_sources):
        result = generate_all_citations(sample_sources)
        assert result["ieee"][0]["formatted"].startswith("[1]")
        assert result["ieee"][1]["formatted"].startswith("[2]")

    def test_empty_source_list_returns_empty_lists(self):
        result = generate_all_citations([])
        assert result == {"apa": [], "mla": [], "ieee": []}
