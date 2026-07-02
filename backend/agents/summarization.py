"""
agents/summarization.py

Agent #6 — Summarization Agent

Responsibilities:
  - Generate three tiers of summary from the verified research findings:
      * short_summary    (~2-3 sentences — for cards/previews)
      * medium_summary   (~1-2 paragraphs — for quick reading)
      * detailed_summary (~4-6 paragraphs — comprehensive but still condensed)

Uses the STANDARD-tier LLM (DeepSeek V3) — good general writing quality
without the latency/cost of the reasoning-tier model.
"""

from __future__ import annotations

import json
import logging

from crewai import Agent, Task

from agents.llm_provider import TaskComplexity, get_llm

logger = logging.getLogger(__name__)

SUMMARY_OUTPUT_SCHEMA = """
Respond ONLY with valid JSON (no markdown fences):
{
  "short_summary": "string - 2-3 sentences, the absolute essence",
  "medium_summary": "string - 1-2 paragraphs, key points for a quick read",
  "detailed_summary": "string - 4-6 paragraphs, comprehensive coverage of all major findings"
}
"""


def build_summarization_agent() -> Agent:
    llm = get_llm(complexity=TaskComplexity.STANDARD, temperature=0.4)

    return Agent(
        role="Research Summarization Specialist",
        goal=(
            "Distill verified research findings into three clear summary tiers — "
            "short, medium, and detailed — each accurate to the source material "
            "and free of unsupported claims."
        ),
        backstory=(
            "You are an expert science and technology writer known for making "
            "complex findings accessible without oversimplifying or distorting "
            "them. You write in plain, confident prose and never pad with filler."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_summarization_task(
    agent: Agent,
    research_plan: dict,
    verified_findings: dict,
) -> Task:
    main_topic = research_plan.get("main_topic", "the research topic")
    contradictions = verified_findings.get("contradictions", [])
    contradictions_note = (
        f"\n\nNote: the following contradictions were found between sources and "
        f"should be reflected as open questions rather than resolved one way:\n"
        f"{json.dumps(contradictions, indent=2)}"
        if contradictions
        else ""
    )

    return Task(
        description=(
            f"Write three tiers of summary for research on '{main_topic}', based on "
            f"the verified findings and sources gathered by the research team. "
            f"Ground every statement in the gathered evidence — do not introduce "
            f"facts not supported by the research.{contradictions_note}\n\n"
            f"{SUMMARY_OUTPUT_SCHEMA}"
        ),
        expected_output="A single valid JSON object matching the schema, and nothing else.",
        agent=agent,
    )
