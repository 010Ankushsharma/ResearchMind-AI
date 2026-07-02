"""
agents/fact_verification.py

Agent #4 — Fact Verification Agent

Responsibilities:
  - Compare information across multiple extracted sources
  - Identify contradictions between sources
  - Calculate a confidence/trustworthiness score (0-100) per source, based on:
      * Domain Authority   - is this a known reputable outlet/org?
      * Source Age         - how recent is the content?
      * Citation Count     - how often is this claim corroborated by others?
      * Overall Trustworthiness - weighted composite

Uses the REASONING-tier LLM since cross-referencing claims across many
sources and spotting contradictions is a non-trivial reasoning task.
"""

from __future__ import annotations

import logging

from crewai import Agent, Task

from agents.llm_provider import TaskComplexity, get_llm

logger = logging.getLogger(__name__)

# A small, illustrative set of generally high-authority domain patterns used
# to seed the LLM's domain-authority judgment (it can still reason beyond this).
KNOWN_HIGH_AUTHORITY_HINTS = [
    ".gov", ".edu", "reuters.com", "apnews.com", "nature.com", "arxiv.org",
    "ieee.org", "acm.org", "bbc.com", "nytimes.com", "wsj.com", "bloomberg.com",
]

SCORING_OUTPUT_SCHEMA = """
Respond ONLY with valid JSON (no markdown fences):
{
  "verified_sources": [
    {
      "url": "string",
      "domain_authority_score": 0-100,
      "source_age_score": 0-100,
      "citation_count_score": 0-100,
      "trustworthiness_score": 0-100,
      "notes": "string - brief rationale"
    }
  ],
  "contradictions": [
    {
      "claim": "string - the disputed claim",
      "supporting_sources": ["url1"],
      "conflicting_sources": ["url2"],
      "explanation": "string"
    }
  ],
  "overall_confidence": 0-100
}
"""


def build_fact_verification_agent() -> Agent:
    llm = get_llm(complexity=TaskComplexity.REASONING, temperature=0.2)

    return Agent(
        role="Fact Verification Analyst",
        goal=(
            "Cross-reference claims across all extracted sources, surface any "
            "contradictions, and assign each source a credibility score so the "
            "report writer can weight evidence appropriately."
        ),
        backstory=(
            "You are a rigorous fact-checker trained in journalistic verification "
            "standards. You corroborate claims across independent sources before "
            "trusting them, you are skeptical of single-source claims, and you "
            "always note when sources disagree rather than silently picking a side."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_fact_verification_task(agent: Agent, extracted_sources: list[dict]) -> Task:
    sources_block = "\n\n".join(
        f"URL: {s.get('url')}\nTitle: {s.get('title')}\nPublished: {s.get('published_date')}\n"
        f"Content excerpt: {(s.get('extracted_content') or '')[:1500]}"
        for s in extracted_sources
        if not s.get("extraction_failed")
    ) or "(no successfully extracted sources)"

    return Task(
        description=(
            f"Review the following extracted sources:\n\n{sources_block}\n\n"
            f"For each source, estimate four scores from 0-100:\n"
            f"- domain_authority_score: based on the reputation of the publishing domain "
            f"(known reputable outlets/orgs like {', '.join(KNOWN_HIGH_AUTHORITY_HINTS[:6])}, etc. "
            f"score higher; unknown blogs/SEO-farm sites score lower)\n"
            f"- source_age_score: based on how recent the published_date is relative to today "
            f"(more recent generally scores higher for fast-moving topics)\n"
            f"- citation_count_score: based on how many *other* sources in this set corroborate "
            f"its key claims (more independent corroboration scores higher)\n"
            f"- trustworthiness_score: an overall weighted composite of the above\n\n"
            f"Then identify any contradictions between sources — claims where two or more "
            f"sources disagree on a fact. Finally give an overall_confidence (0-100) for the "
            f"combined evidence base.\n\n{SCORING_OUTPUT_SCHEMA}"
        ),
        expected_output="A single valid JSON object matching the schema, and nothing else.",
        agent=agent,
    )
