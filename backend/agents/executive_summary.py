"""
agents/executive_summary.py

Agent #9 — Executive Summary Agent

Responsibilities:
  Generate:
    - A 1-page business-oriented summary
    - Key takeaways
    - Risks
    - Opportunities

Audience is assumed to be a busy executive/decision-maker who has not read
the full report — so this agent writes for that lens specifically, distinct
from the more academic/analytical tone of the Report Writer Agent.

Uses the STANDARD-tier LLM (DeepSeek V3) — strong business-writing quality
at low cost/latency.
"""

from __future__ import annotations

import logging

from crewai import Agent, Task

from agents.llm_provider import TaskComplexity, get_llm

logger = logging.getLogger(__name__)

EXECUTIVE_SUMMARY_OUTPUT_SCHEMA = """
Respond ONLY with valid JSON (no markdown fences):
{
  "executive_summary": "string - a 1-page (300-450 word) business-oriented summary",
  "key_takeaways": ["string", "string", "string"],
  "risks": ["string", "string"],
  "opportunities": ["string", "string"]
}
"""


def build_executive_summary_agent() -> Agent:
    llm = get_llm(complexity=TaskComplexity.STANDARD, temperature=0.4)

    return Agent(
        role="Executive Communications Specialist",
        goal=(
            "Translate detailed research findings into a concise, decision-ready "
            "executive brief that a busy stakeholder can act on without reading "
            "the full report."
        ),
        backstory=(
            "You are a strategy consultant who has briefed C-suite executives for "
            "years. You write in plain, confident business language, lead with the "
            "'so what,' and always separate what's a known risk from what's a "
            "speculative opportunity — never blurring the two."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_executive_summary_task(
    agent: Agent,
    research_plan: dict,
    report_sections: dict,
) -> Task:
    main_topic = research_plan.get("main_topic", "the research topic")

    return Task(
        description=(
            f"Based on the full research report on '{main_topic}' below, write a "
            f"business-oriented executive brief for a decision-maker who has not "
            f"read the full report.\n\n"
            f"Key Findings:\n{report_sections.get('key_findings', '')}\n\n"
            f"Analysis:\n{report_sections.get('analysis', '')}\n\n"
            f"Recommendations:\n{report_sections.get('recommendations', '')}\n\n"
            f"Write 3-5 key_takeaways (the most important things to remember), "
            f"2-4 risks (real, specific risks suggested by the findings — not "
            f"generic boilerplate), and 2-4 opportunities (concrete, actionable "
            f"opportunities suggested by the findings).\n\n"
            f"{EXECUTIVE_SUMMARY_OUTPUT_SCHEMA}"
        ),
        expected_output="A single valid JSON object matching the schema, and nothing else.",
        agent=agent,
    )
