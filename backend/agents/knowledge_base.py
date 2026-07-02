"""
agents/knowledge_base.py

Agent #5 — Knowledge Base Agent

Responsibilities:
  - Take verified, extracted content from upstream agents
  - Create embeddings (BAAI/bge-small-en-v1.5, local + free)
  - Store documents/chunks in ChromaDB for retrieval (RAG)
  - Enable later semantic search (current session, follow-ups, and
    cross-session recall like "what did I research last month?")

Unlike the other agents, this one is implemented as a direct service call
rather than a tool-using LLM agent — storage is a deterministic operation,
not a reasoning task, so we skip an unnecessary LLM round-trip and call
`ChromaService` directly from the orchestrating crew/workflow. A thin
CrewAI `Agent` wrapper is still provided for consistency with the rest of
the pipeline (e.g. if delegation/logging via CrewAI is desired later).
"""

from __future__ import annotations

import logging
import uuid

from crewai import Agent

from agents.llm_provider import TaskComplexity, get_llm
from rag.chroma_service import get_chroma_service

logger = logging.getLogger(__name__)


def build_knowledge_base_agent() -> Agent:
    """
    Lightweight CrewAI Agent shell for the Knowledge Base step, used when this
    stage needs to participate in a CrewAI Crew (e.g. for unified logging).
    For the actual store operation, prefer calling `store_verified_content()`
    directly — it's faster and deterministic.
    """
    llm = get_llm(complexity=TaskComplexity.FAST, temperature=0.0)

    return Agent(
        role="Knowledge Base Manager",
        goal="Organize verified research content into the vector knowledge base for retrieval.",
        backstory=(
            "You are a meticulous knowledge engineer who ensures every piece of "
            "verified research is properly indexed and retrievable, with accurate "
            "metadata linking it back to its source and research session."
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


async def store_verified_content(
    *,
    research_session_id: uuid.UUID,
    user_id: uuid.UUID,
    verified_sources: list[dict],
) -> dict:
    """
    Direct service call (no LLM) that chunks + embeds + stores each verified
    source's extracted content, and mirrors metadata to Postgres.

    `verified_sources` items are expected to have at least:
      { "source_id": uuid, "url": str, "extracted_content": str,
        "trustworthiness_score": float, ... }
    """
    chroma = get_chroma_service()
    stored_counts: dict[str, int] = {}
    total_chunks = 0

    for source in verified_sources:
        content = source.get("extracted_content") or ""
        if not content.strip():
            continue

        vector_ids = await chroma.store_source_content(
            research_session_id=research_session_id,
            user_id=user_id,
            source_id=source.get("source_id"),
            text=content,
            extra_metadata={
                "url": source.get("url", ""),
                "trustworthiness_score": source.get("trustworthiness_score", 0),
            },
        )
        stored_counts[source.get("url", "unknown")] = len(vector_ids)
        total_chunks += len(vector_ids)

    logger.info(
        "Knowledge Base Agent stored %d chunks across %d sources for session %s",
        total_chunks,
        len(stored_counts),
        research_session_id,
    )

    return {
        "total_chunks_stored": total_chunks,
        "sources_indexed": len(stored_counts),
        "per_source_chunk_counts": stored_counts,
    }
