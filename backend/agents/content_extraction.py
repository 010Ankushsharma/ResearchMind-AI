"""
agents/content_extraction.py

Agent #3 — Content Extraction Agent

Responsibilities:
  - Visit each candidate source URL
  - Strip boilerplate (nav, ads, footers) via the extract_page_content tool
  - Produce clean, structured knowledge ready for fact verification and
    downstream summarization/RAG storage

Uses the FAST-tier LLM — the heavy lifting here is the scraping tool itself;
the LLM's job is mainly to clean up/structure what the tool returns.
"""

from __future__ import annotations

import logging

from crewai import Agent, Task

from agents.llm_provider import TaskComplexity, get_llm
from tools.scraping_tool import content_extraction_tool

logger = logging.getLogger(__name__)


def build_content_extraction_agent() -> Agent:
    llm = get_llm(complexity=TaskComplexity.FAST, temperature=0.1)

    return Agent(
        role="Content Extraction Specialist",
        goal=(
            "Retrieve the full content of each source URL and distill it into "
            "clean, well-structured knowledge — removing ads, navigation, and "
            "other boilerplate while preserving every factually relevant detail."
        ),
        backstory=(
            "You are a meticulous data engineer who specializes in turning messy "
            "raw web pages into clean structured text. You never invent content "
            "that wasn't in the source, and you flag pages that failed to load or "
            "had too little usable content instead of fabricating a summary."
        ),
        tools=[content_extraction_tool],
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_content_extraction_task(agent: Agent, sources: list[dict]) -> Task:
    urls_block = "\n".join(f"- {s.get('url')}" for s in sources) or "- (no sources provided)"

    return Task(
        description=(
            f"For each of the following URLs, use the `extract_page_content` tool "
            f"to fetch and clean its main content:\n\n{urls_block}\n\n"
            f"For each URL, return the cleaned content along with the page title and "
            f"publish date if the tool found one. If extraction fails or returns very "
            f"little usable content (e.g. a paywall or JS-only page), mark that source "
            f"as `extraction_failed: true` rather than guessing at its content. "
            f"Do not summarize yet — preserve the full extracted text for the Fact "
            f"Verification and Summarization agents downstream."
        ),
        expected_output=(
            "A JSON array, one object per URL, each with: url, title, published_date, "
            "extracted_content (full cleaned text or empty string), and extraction_failed "
            "(boolean). JSON only, no prose."
        ),
        agent=agent,
    )
