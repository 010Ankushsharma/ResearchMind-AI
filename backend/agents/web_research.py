"""
agents/web_research.py

Agent #2 — Web Research Agent

Responsibilities:
  - Take the subtopics/search queries from the Research Coordinator's plan
  - Search the internet for relevant articles via the web_search tool
    (Tavily primary, DuckDuckGo fallback)
  - Collect and de-duplicate candidate URLs/sources

Uses the FAST-tier LLM since this agent mostly orchestrates tool calls
rather than doing heavy reasoning.
"""

from __future__ import annotations

import logging

from crewai import Agent, Task

from agents.llm_provider import TaskComplexity, get_llm
from tools.web_search_tool import web_search_tool

logger = logging.getLogger(__name__)


def build_web_research_agent() -> Agent:
    llm = get_llm(complexity=TaskComplexity.FAST, temperature=0.2)

    return Agent(
        role="Web Research Specialist",
        goal=(
            "Execute the search queries provided by the research plan and "
            "compile a clean, de-duplicated list of the most relevant, "
            "credible-looking sources for each subtopic."
        ),
        backstory=(
            "You are a meticulous research librarian and OSINT specialist. "
            "You know how to phrase search queries to surface authoritative "
            "sources (official docs, reputable news, academic/industry "
            "publications) rather than SEO spam, and you avoid returning "
            "near-duplicate articles from the same outlet."
        ),
        tools=[web_search_tool],
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def build_web_research_task(agent: Agent, research_plan: dict, max_sources: int = 10) -> Task:
    subtopics = research_plan.get("subtopics", [])
    queries_block = "\n".join(
        f"- Subtopic: {st.get('title')}\n  Queries: {', '.join(st.get('search_queries', []))}"
        for st in subtopics
    ) or "- No subtopics provided; derive 2-3 sensible queries from the main topic."

    main_topic = research_plan.get("main_topic", "the research topic")

    return Task(
        description=(
            f"Using the `web_search` tool, run searches for each of the following "
            f"subtopics of '{main_topic}':\n\n{queries_block}\n\n"
            f"For each subtopic, run its search queries and collect the top results. "
            f"Remove duplicate URLs and near-duplicate articles from the same domain "
            f"covering the same story. Aim for a final de-duplicated list of around "
            f"{max_sources} of the most relevant and authoritative sources overall, "
            f"prioritizing primary sources, official documentation, reputable news "
            f"outlets, and well-known industry/academic publications over low-quality "
            f"or SEO-farm content."
        ),
        expected_output=(
            "A JSON array of source objects, each with: title, url, domain, snippet, "
            "published_date (if known), and the subtopic it relates to. No prose, JSON only."
        ),
        agent=agent,
    )
