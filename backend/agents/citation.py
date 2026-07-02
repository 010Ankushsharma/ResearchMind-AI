"""
agents/citation.py

Agent #8 — Citation Agent

Responsibilities:
  Generate properly formatted references in:
    - APA
    - MLA
    - IEEE

Citation formatting is largely deterministic given clean metadata (author,
title, domain/publisher, date, URL), so this module implements rule-based
formatters as the primary path — fast, free, and consistent — with a thin
CrewAI `Agent` available for cases where metadata is messy and a bit of
LLM judgment helps (e.g. inferring a publisher name from a domain).
"""

from __future__ import annotations

import logging
from datetime import datetime

from crewai import Agent

from agents.llm_provider import TaskComplexity, get_llm

logger = logging.getLogger(__name__)


def build_citation_agent() -> Agent:
    """Thin agent used only as a fallback when rule-based formatting metadata is too sparse."""
    llm = get_llm(complexity=TaskComplexity.FAST, temperature=0.1)

    return Agent(
        role="Citation Specialist",
        goal="Produce accurate, properly formatted APA, MLA, and IEEE citations for every source.",
        backstory=(
            "You are a meticulous academic librarian who knows the APA 7th edition, "
            "MLA 9th edition, and IEEE citation styles by heart. When metadata is "
            "incomplete, you make the most reasonable inference (e.g. treating the "
            "domain owner as the publisher) and never invent an author name."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


# ── Rule-based formatters (primary path) ────────────────────────────────

def _safe_year(published_date: str | datetime | None) -> str:
    if not published_date:
        return "n.d."
    if isinstance(published_date, datetime):
        return str(published_date.year)
    try:
        return str(datetime.fromisoformat(str(published_date).replace("Z", "+00:00")).year)
    except (ValueError, TypeError):
        return "n.d."


def _publisher_from_domain(domain: str | None) -> str:
    if not domain:
        return "Unknown Publisher"
    name = domain.split(".")[0]
    return name.replace("-", " ").title()


def format_apa(source: dict) -> str:
    title = source.get("title") or "Untitled"
    domain = source.get("domain")
    publisher = _publisher_from_domain(domain)
    year = _safe_year(source.get("published_date"))
    url = source.get("url", "")
    return f"{publisher}. ({year}). {title}. Retrieved from {url}"


def format_mla(source: dict) -> str:
    title = source.get("title") or "Untitled"
    domain = source.get("domain")
    publisher = _publisher_from_domain(domain)
    year = _safe_year(source.get("published_date"))
    url = source.get("url", "")
    return f'"{title}." {publisher}, {year}, {url}.'


def format_ieee(source: dict, index: int) -> str:
    title = source.get("title") or "Untitled"
    domain = source.get("domain")
    publisher = _publisher_from_domain(domain)
    year = _safe_year(source.get("published_date"))
    url = source.get("url", "")
    return f'[{index}] {publisher}, "{title}," {year}. [Online]. Available: {url}'


def generate_all_citations(sources: list[dict]) -> dict:
    """
    Build APA, MLA, and IEEE citation lists for a list of source dicts.
    Each source dict should have: url, title, domain, published_date, source_id.
    """
    apa, mla, ieee = [], [], []

    for idx, source in enumerate(sources, start=1):
        source_id = source.get("source_id") or source.get("id")
        apa.append({"source_id": source_id, "formatted": format_apa(source)})
        mla.append({"source_id": source_id, "formatted": format_mla(source)})
        ieee.append({"source_id": source_id, "formatted": format_ieee(source, idx)})

    logger.info("Generated %d citations in each of APA/MLA/IEEE styles", len(sources))

    return {"apa": apa, "mla": mla, "ieee": ieee}
