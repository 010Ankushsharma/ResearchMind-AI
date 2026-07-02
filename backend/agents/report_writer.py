"""
agents/report_writer.py

Agent #7 — Report Writer Agent

Responsibilities:
  Generate the full structured report:
    - Title
    - Abstract
    - Introduction
    - Key Findings
    - Analysis
    - Recommendations
    - Conclusion

Uses the REASONING-tier LLM since synthesizing many sources into a coherent,
well-structured analytical report benefits from stronger reasoning than the
summarization step.
"""

from __future__ import annotations

import json
import logging

from crewai import Agent, Task

from agents.llm_provider import TaskComplexity, get_llm

logger = logging.getLogger(__name__)

REPORT_OUTPUT_SCHEMA = """
Respond ONLY with valid JSON (no markdown fences):
{
  "title": "string - a clear, specific report title",
  "abstract": "string - ~150 words summarizing the whole report",
  "introduction": "string - context and scope of the research",
  "key_findings": "string - the most important discoveries, organized clearly (use \\n\\n between points)",
  "analysis": "string - deeper interpretation: trends, implications, why findings matter",
  "recommendations": "string - actionable next steps or guidance based on the findings",
  "conclusion": "string - concise wrap-up tying back to the research objective"
}
"""


def build_report_writer_agent() -> Agent:
    llm = get_llm(complexity=TaskComplexity.REASONING, temperature=0.45)

    return Agent(
        role="Senior Report Writer",
        goal=(
            "Synthesize all verified research findings into a polished, "
            "well-structured analytical report that fully addresses the "
            "original research objective."
        ),
        backstory=(
            "You are a senior analyst who has written hundreds of research "
            "reports for executives and technical teams alike. You write with "
            "clarity and precision, structure information logically, and always "
            "ground claims in the evidence gathered — calling out uncertainty "
            "where the evidence is mixed rather than overstating confidence."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_report_writer_task(
    agent: Agent,
    research_plan: dict,
    verified_findings: dict,
    summaries: dict,
) -> Task:
    main_topic = research_plan.get("main_topic", "the research topic")
    objective = research_plan.get("research_objective", "")
    contradictions = verified_findings.get("contradictions", [])
    overall_confidence = verified_findings.get("overall_confidence", "unknown")

    contradictions_block = (
        json.dumps(contradictions, indent=2) if contradictions else "None identified."
    )

    return Task(
        description=(
            f"Write a complete research report on '{main_topic}'.\n\n"
            f"Research objective: {objective}\n\n"
            f"Detailed summary of findings to build on:\n{summaries.get('detailed_summary', '')}\n\n"
            f"Known contradictions between sources (address these candidly in your "
            f"Analysis section rather than ignoring them):\n{contradictions_block}\n\n"
            f"Overall evidence confidence score: {overall_confidence}/100\n\n"
            f"Write each section with appropriate depth — Key Findings and Analysis "
            f"should be the most substantial sections. Recommendations should be "
            f"concrete and actionable, not generic. Do not fabricate sources or "
            f"statistics not present in the research findings provided.\n\n"
            f"{REPORT_OUTPUT_SCHEMA}"
        ),
        expected_output="A single valid JSON object matching the schema, and nothing else.",
        agent=agent,
    )


FOLLOW_UP_OUTPUT_SCHEMA = """
Respond ONLY with valid JSON (no markdown fences) containing ONLY the section keys you
actually revised — omit any key you did not change. Valid keys are exactly:
"title", "abstract", "introduction", "key_findings", "analysis", "recommendations", "conclusion".
Example (if only key_findings was revised):
{
  "key_findings": "the fully revised key findings text..."
}
"""


def build_follow_up_task(agent: Agent, current_sections: dict, instruction: str) -> Task:
    """
    Builds the Task used by `crews.research_crew.apply_follow_up()` to
    actually regenerate report content based on a user's follow-up
    instruction (e.g. "Expand section 3", "Make the recommendations more
    actionable"), rather than just appending a note to the report.
    """
    sections_block = "\n\n".join(
        f"--- {key.upper()} ---\n{value or '(empty)'}" for key, value in current_sections.items()
    )

    return Task(
        description=(
            f"Here is the current research report:\n\n{sections_block}\n\n"
            f"The user has requested the following change:\n\n\"{instruction}\"\n\n"
            f"Revise ONLY the section(s) necessary to satisfy this request. Each revised "
            f"section should be a complete, polished replacement for that section — not a "
            f"diff or a partial addition. Do not fabricate new sources or statistics that "
            f"weren't already implied by the existing report content. If the instruction "
            f"references comparing against 'the previous report', note in your revision "
            f"that a direct prior-report comparison requires re-running research with that "
            f"context, and instead improve the current section as best you can with what's "
            f"available.\n\n{FOLLOW_UP_OUTPUT_SCHEMA}"
        ),
        expected_output="A JSON object containing only the revised section(s), and nothing else.",
        agent=agent,
    )
