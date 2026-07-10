"""
tools/web_search_tool.py

Web search tool used by the Web Research Agent.

Strategy:
  1. PRIMARY  -> Tavily Search API (free tier, AI-optimized search results)
  2. FALLBACK -> DuckDuckGo Search (no API key required at all)

Exposed as a CrewAI `BaseTool` so it can be attached directly to an Agent's
`tools=[...]` list.
"""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from crewai.tools import BaseTool
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field
from tavily import TavilyClient

from core.config import settings
from core.request_context import get_llm_overrides

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    query: str = Field(..., description="The search query to look up on the web")
    max_results: int = Field(default=8, ge=1, le=20, description="Max number of results to return")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the live web for a query and return a list of relevant sources "
        "(title, url, domain, snippet, published_date when available). "
        "Use this to find up-to-date articles, papers, and news related to the research topic."
    )
    args_schema: type[BaseModel] = WebSearchInput

    def _run(self, query: str, max_results: int = 8) -> list[dict]:
        results = self._search_tavily(query, max_results)
        if results:
            return results

        logger.warning("Tavily returned no results for %r — falling back to DuckDuckGo", query)
        return self._search_duckduckgo(query, max_results)

    # ── Providers ────────────────────────────────────────────────────────

    def _search_tavily(self, query: str, max_results: int) -> list[dict]:
        overrides = get_llm_overrides()
        api_key = (overrides.tavily_api_key if overrides else None) or settings.TAVILY_API_KEY
        if not api_key:
            return []
        try:
            client = TavilyClient(api_key=api_key)
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="advanced",
                include_answer=False,
            )
            return [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "domain": self._domain_from_url(item.get("url", "")),
                    "snippet": item.get("content"),
                    "published_date": item.get("published_date"),
                    "score": item.get("score"),
                    "provider": "tavily",
                }
                for item in response.get("results", [])
            ]
        except Exception as exc:  # noqa: BLE001
            logger.error("Tavily search failed: %s", exc)
            return []

    def _search_duckduckgo(self, query: str, max_results: int) -> list[dict]:
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=max_results))
            return [
                {
                    "title": item.get("title"),
                    "url": item.get("href"),
                    "domain": self._domain_from_url(item.get("href", "")),
                    "snippet": item.get("body"),
                    "published_date": None,
                    "score": None,
                    "provider": "duckduckgo",
                }
                for item in raw_results
            ]
        except Exception as exc:  # noqa: BLE001
            logger.error("DuckDuckGo search failed: %s", exc)
            return []

    @staticmethod
    def _domain_from_url(url: str) -> str:
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:  # noqa: BLE001
            return ""


# Singleton instance attached to the Web Research Agent
web_search_tool = WebSearchTool()
