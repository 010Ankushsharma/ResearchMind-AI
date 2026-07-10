"""
tools/scraping_tool.py

Page scraping / content extraction tool used by the Content Extraction Agent.

Strategy:
  1. PRIMARY  -> trafilatura (purpose-built for clean main-content extraction,
                 strips nav/ads/boilerplate, also recovers metadata)
  2. FALLBACK -> requests + BeautifulSoup with a heuristic text extraction
                 if trafilatura fails or returns too little content.
"""

from __future__ import annotations

import logging

import requests
import trafilatura
from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MIN_USEFUL_CONTENT_CHARS = 200
REQUEST_TIMEOUT_SECONDS = 15
USER_AGENT = (
    "Mozilla/5.0 (compatible; ResearchPlatformBot/1.0; "
    "+https://research-platform.local/bot)"
)


class ScrapeInput(BaseModel):
    url: str = Field(..., description="The URL of the web page to extract clean content from")


class ContentExtractionTool(BaseTool):
    name: str = "extract_page_content"
    description: str = (
        "Fetch a web page by URL and return clean, readable article text with "
        "boilerplate (nav, ads, footers) removed, along with title and publish "
        "date metadata when available. Use this after web_search to read full "
        "source content rather than relying on the short snippet."
    )
    args_schema: type[BaseModel] = ScrapeInput

    def _run(self, url: str) -> dict:
        result = self._extract_with_trafilatura(url)
        if result and len(result.get("content", "")) >= MIN_USEFUL_CONTENT_CHARS:
            return result

        logger.warning("trafilatura extraction insufficient for %s — falling back to BeautifulSoup", url)
        fallback = self._extract_with_bs4(url)
        return fallback or {"url": url, "title": None, "content": "", "published_date": None, "error": "extraction_failed"}

    # ── Providers ────────────────────────────────────────────────────────

    def _extract_with_trafilatura(self, url: str) -> dict | None:
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None

            content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            metadata = trafilatura.extract_metadata(downloaded)

            return {
                "url": url,
                "title": getattr(metadata, "title", None) if metadata else None,
                "content": content or "",
                "published_date": getattr(metadata, "date", None) if metadata else None,
                "author": getattr(metadata, "author", None) if metadata else None,
                "provider": "trafilatura",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("trafilatura failed for %s: %s", url, exc)
            return None

    def _extract_with_bs4(self, url: str) -> dict | None:
        try:
            response = requests.get(
                url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Strip obvious boilerplate elements before extracting text
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                tag.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else None

            # Prefer <article> if present, otherwise fall back to <body>
            main = soup.find("article") or soup.body or soup
            paragraphs = [p.get_text(strip=True) for p in main.find_all("p")]
            content = "\n\n".join(p for p in paragraphs if len(p) > 40)

            return {
                "url": url,
                "title": title,
                "content": content,
                "published_date": None,
                "author": None,
                "provider": "beautifulsoup",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("BeautifulSoup fallback failed for %s: %s", url, exc)
            return None


# Singleton instance attached to the Content Extraction Agent
content_extraction_tool = ContentExtractionTool()
