"""
tests/conftest.py

Shared pytest fixtures. Kept deliberately lightweight — these tests target
pure functions and deterministic logic (citation formatting, JSON parsing,
text chunking) that don't require a live Postgres/ChromaDB/LLM connection,
so the suite runs fast and free in CI without any API keys configured.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_sources() -> list[dict]:
    """A representative set of source dicts as they'd appear after web research."""
    return [
        {
            "source_id": "11111111-1111-1111-1111-111111111111",
            "url": "https://www.nature.com/articles/ai-agents-2026",
            "title": "The Rise of Autonomous AI Agents",
            "domain": "nature.com",
            "published_date": "2026-03-15T00:00:00Z",
        },
        {
            "source_id": "22222222-2222-2222-2222-222222222222",
            "url": "https://example-blog.com/ai-agents-explained",
            "title": "AI Agents Explained",
            "domain": "example-blog.com",
            "published_date": None,
        },
    ]


@pytest.fixture
def sample_research_plan() -> dict:
    return {
        "main_topic": "Latest advancements in AI Agents",
        "research_objective": "Summarize the current state and near-term trajectory of AI agents.",
        "subtopics": [
            {
                "title": "Autonomous multi-agent frameworks",
                "search_queries": ["multi-agent AI frameworks 2026"],
                "rationale": "Core to understanding current architecture trends.",
            },
            {
                "title": "Enterprise adoption",
                "search_queries": ["enterprise AI agent adoption 2026"],
                "rationale": "Shows real-world traction.",
            },
        ],
        "suggested_report_sections": ["Introduction", "Key Findings", "Analysis", "Conclusion"],
        "estimated_source_count": 10,
    }
