"""
agents/research_coordinator.py

Agent #1 — Research Coordinator Agent

Responsibilities:
  - Understand the user's query
  - Break it into focused subtasks / subtopics
  - Produce a structured research plan that downstream agents follow
  - (Conceptually) monitor overall workflow progress

This agent makes no tool calls — it's a pure reasoning/planning step, so it
uses the REASONING-tier LLM (DeepSeek R1 on OpenRouter) for higher-quality
decomposition of ambiguous or broad topics.
"""

from __future__ import annotations

import json
import logging

from crewai import Agent, Task

from agents.llm_provider import TaskComplexity, get_llm

logger = logging.getLogger(__name__)


RESEARCH_PLAN_OUTPUT_SCHEMA = """
Respond ONLY with valid JSON in this exact shape (no markdown fences, no prose):
{
  "main_topic": "string",
  "research_objective": "string - what the final report should accomplish",
  "subtopics": [
    {
      "title": "string",
      "search_queries": ["string", "string"],
      "rationale": "string - why this subtopic matters to the overall objective"
    }
  ],
  "suggested_report_sections": ["Introduction", "Key Findings", "..."],
  "estimated_source_count": 10
}
"""


def build_research_coordinator_agent() -> Agent:
    llm = get_llm(complexity=TaskComplexity.REASONING, temperature=0.4)

    return Agent(
        role="Research Coordinator",
        goal=(
            "Deeply understand the user's research query and produce a clear, "
            "actionable research plan that breaks it into well-scoped subtopics "
            "the rest of the research team can execute against."
        ),
        backstory=(
            "You are a senior research strategist who has led hundreds of analyst "
            "teams. You excel at taking a broad or ambiguous question and breaking "
            "it into the smallest set of subtopics that, together, fully cover the "
            "objective without redundant overlap. You think about what a reader of "
            "the final report would actually need to know."
        ),
        llm=llm,
        allow_delegation=True,
        verbose=True,
    )


def build_planning_task(agent: Agent, query: str, max_sources: int = 10) -> Task:
    return Task(
        description=(
            f"The user wants a research report on the following topic/question:\n\n"
            f'"{query}"\n\n'
            f"Break this down into 3-5 focused subtopics that together fully cover "
            f"what the final report needs to address. For each subtopic, write 1-3 "
            f"concrete web search queries that the Web Research Agent should run. "
            f"Keep the total estimated source count around {max_sources}.\n\n"
            f"{RESEARCH_PLAN_OUTPUT_SCHEMA}"
        ),
        expected_output="A single valid JSON object matching the schema, and nothing else.",
        agent=agent,
    )


def parse_research_plan(raw_output: str) -> dict:
    """
    Defensively parse the coordinator's JSON output, stripping markdown
    fences the LLM sometimes adds despite instructions.
    """
    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse research plan JSON: %s\nRaw output: %s", exc, raw_output)
        # Minimal safe fallback so the pipeline can still proceed
        return {
            "main_topic": "",
            "research_objective": "",
            "subtopics": [],
            "suggested_report_sections": [
                "Introduction", "Key Findings", "Analysis", "Recommendations", "Conclusion"
            ],
            "estimated_source_count": 10,
            "parse_error": str(exc),
        }
