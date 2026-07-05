"""
crews/research_crew.py

The master orchestrator: wires all 10 agents into the full research →
report pipeline described in the platform spec:

  Research Coordinator → Web Research → Content Extraction →
  Fact Verification → Knowledge Base → Summarization → Report Writer →
  Executive Summary → Citation → PDF Generation

Because several stages need to parse the previous stage's structured JSON
output before deciding what to feed the next stage (and persist progress
to Postgres along the way for the live "agent activity" UI), this is
implemented as an explicit async orchestrator (`ResearchCrewRunner`) that
runs each agent as a single-task CrewAI `Crew`, rather than one giant
chained Crew — giving us full control over persistence, error handling,
and progress reporting between every step.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from crewai import Crew, Process
from sqlalchemy import select

from agents.citation import build_citation_agent, generate_all_citations
from agents.content_extraction import build_content_extraction_agent, build_content_extraction_task
from agents.executive_summary import build_executive_summary_agent, build_executive_summary_task
from agents.fact_verification import build_fact_verification_agent, build_fact_verification_task
from agents.knowledge_base import store_verified_content
from agents.pdf_generation import generate_report_pdf
from agents.report_writer import (
    build_follow_up_task,
    build_report_writer_agent,
    build_report_writer_task,
)
from agents.research_coordinator import (
    build_planning_task,
    build_research_coordinator_agent,
    parse_research_plan,
)
from agents.summarization import build_summarization_agent, build_summarization_task
from agents.web_research import build_web_research_agent, build_web_research_task
from core.crypto import decrypt_secret
from core.request_context import LLMKeyOverrides, clear_llm_overrides, set_llm_overrides
from database.connection import get_db_context
from models.agent_log import AgentLog, AgentName, LogLevel
from models.report import Report
from models.research_session import ResearchSession, SessionStatus
from models.source import Source
from models.user_settings import UserSettings

logger = logging.getLogger(__name__)


def _safe_json_parse(raw: str, fallback):
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed: %s\nRaw: %s", exc, raw[:500])
        return fallback


class ResearchCrewRunner:
    """Runs the full multi-agent pipeline for a single ResearchSession."""

    def __init__(self, research_session_id: uuid.UUID):
        self.research_session_id = research_session_id

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _update_session(self, **fields) -> None:
        async with get_db_context() as db:
            session = await db.get(ResearchSession, self.research_session_id)
            if session:
                for key, value in fields.items():
                    setattr(session, key, value)

    async def _log(
        self, agent_name: AgentName, message: str, level: LogLevel = LogLevel.INFO,
        details: dict | None = None, duration_ms: float | None = None,
    ) -> None:
        async with get_db_context() as db:
            db.add(
                AgentLog(
                    research_session_id=self.research_session_id,
                    agent_name=agent_name,
                    level=level,
                    message=message,
                    details=details,
                    duration_ms=duration_ms,
                )
            )

    @staticmethod
    def _run_single_task(agent, task) -> str:
        """Runs a single agent/task pair as its own sequential Crew and returns the raw text output."""
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=True)
        result = crew.kickoff()
        return str(result)

    # ── Main entrypoint ──────────────────────────────────────────────────

    async def run(self, query: str, user_id: uuid.UUID, max_sources: int = 10, citation_style: str = "apa") -> uuid.UUID:
        await ResearchCrewRunner._apply_user_key_overrides(user_id)
        try:
            research_plan = await self._stage_planning(query, max_sources)
            raw_sources = await self._stage_web_research(research_plan, max_sources)
            source_rows = await self._persist_sources(raw_sources)
            extracted = await self._stage_content_extraction(source_rows)
            verified = await self._stage_fact_verification(extracted)
            await self._apply_verification_scores(source_rows, verified)
            await self._stage_knowledge_storage(source_rows, extracted, verified, user_id)
            summaries = await self._stage_summarization(research_plan, verified)
            report_sections = await self._stage_report_writing(research_plan, verified, summaries)
            exec_summary_block = await self._stage_executive_summary(research_plan, report_sections)
            citations = await self._stage_citations(source_rows)
            report_id = await self._persist_report(
                user_id, report_sections, summaries, exec_summary_block, citations, citation_style
            )
            await self._stage_pdf_export(report_id, report_sections, exec_summary_block, citations, citation_style)

            await self._update_session(
                status=SessionStatus.COMPLETED,
                progress_percent=100,
                completed_at=datetime.now(timezone.utc),
            )
            return report_id

        except Exception as exc:  # noqa: BLE001
            logger.exception("Research pipeline failed for session %s", self.research_session_id)
            await self._update_session(status=SessionStatus.FAILED, error_message=str(exc))
            await self._log(AgentName.RESEARCH_COORDINATOR, f"Pipeline failed: {exc}", level=LogLevel.ERROR)
            raise
        finally:
            # Always clear the per-task contextvar override — Celery worker
            # processes can reuse the same OS thread/event loop across many
            # users' tasks, so a stale override must never leak forward.
            clear_llm_overrides()

    @staticmethod
    async def _apply_user_key_overrides(user_id: uuid.UUID) -> None:
        """
        If the user has saved their own free-tier API keys in Settings, use
        those for this pipeline run instead of the platform's shared
        defaults — set via a contextvar (core.request_context) so it's
        isolated to this task and never leaks to other concurrent users.
        """
        async with get_db_context() as db:
            result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            row = result.scalar_one_or_none()

        if row is None:
            clear_llm_overrides()
            return

        set_llm_overrides(
            LLMKeyOverrides(
                openrouter_api_key=decrypt_secret(row.openrouter_key_encrypted),
                groq_api_key=decrypt_secret(row.groq_key_encrypted),
                tavily_api_key=decrypt_secret(row.tavily_key_encrypted),
            )
        )

    # ── Stage 1: Planning ────────────────────────────────────────────────

    async def _stage_planning(self, query: str, max_sources: int) -> dict:
        await self._update_session(status=SessionStatus.PLANNING, progress_percent=5)
        t0 = time.monotonic()
        agent = build_research_coordinator_agent()
        task = build_planning_task(agent, query, max_sources)
        raw = self._run_single_task(agent, task)
        plan = parse_research_plan(raw)
        await self._update_session(research_plan=plan, progress_percent=10)
        await self._log(
            AgentName.RESEARCH_COORDINATOR,
            f"Created research plan with {len(plan.get('subtopics', []))} subtopics",
            details={"plan": plan},
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return plan

    # ── Stage 2: Web Research ────────────────────────────────────────────

    async def _stage_web_research(self, research_plan: dict, max_sources: int) -> list:
        await self._update_session(status=SessionStatus.RESEARCHING, progress_percent=15)
        t0 = time.monotonic()
        agent = build_web_research_agent()
        task = build_web_research_task(agent, research_plan, max_sources)
        raw = self._run_single_task(agent, task)
        sources = _safe_json_parse(raw, fallback=[])
        if not isinstance(sources, list):
            sources = []
        await self._update_session(progress_percent=30)
        await self._log(
            AgentName.WEB_RESEARCH,
            f"Found {len(sources)} candidate sources",
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return sources

    async def _persist_sources(self, raw_sources: list) -> list:
        rows = []
        async with get_db_context() as db:
            for s in raw_sources:
                row = Source(
                    research_session_id=self.research_session_id,
                    url=s.get("url", ""),
                    title=s.get("title"),
                    domain=s.get("domain"),
                    snippet=s.get("snippet"),
                )
                db.add(row)
                rows.append(row)
            await db.flush()
            for row in rows:
                await db.refresh(row)
        return rows

    # ── Stage 3: Content Extraction ──────────────────────────────────────

    async def _stage_content_extraction(self, source_rows: list) -> list:
        await self._update_session(status=SessionStatus.EXTRACTING, progress_percent=35)
        t0 = time.monotonic()
        agent = build_content_extraction_agent()
        sources_payload = [{"source_id": str(r.id), "url": r.url} for r in source_rows]
        task = build_content_extraction_task(agent, sources_payload)
        raw = self._run_single_task(agent, task)
        extracted = _safe_json_parse(raw, fallback=[])
        if not isinstance(extracted, list):
            extracted = []

        url_to_id = {r.url: r.id for r in source_rows}
        async with get_db_context() as db:
            for item in extracted:
                source_id = url_to_id.get(item.get("url"))
                if source_id:
                    row = await db.get(Source, source_id)
                    if row:
                        row.extracted_content = item.get("extracted_content") or ""
                        item["source_id"] = str(source_id)

        await self._update_session(progress_percent=50)
        await self._log(
            AgentName.CONTENT_EXTRACTION,
            f"Extracted content from {len(extracted)} pages",
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return extracted

    # ── Stage 4: Fact Verification ───────────────────────────────────────

    async def _stage_fact_verification(self, extracted: list) -> dict:
        await self._update_session(status=SessionStatus.VERIFYING, progress_percent=55)
        t0 = time.monotonic()
        agent = build_fact_verification_agent()
        task = build_fact_verification_task(agent, extracted)
        raw = self._run_single_task(agent, task)
        verified = _safe_json_parse(
            raw, fallback={"verified_sources": [], "contradictions": [], "overall_confidence": 0}
        )
        if not isinstance(verified, dict):
            verified = {"verified_sources": [], "contradictions": [], "overall_confidence": 0}

        await self._update_session(progress_percent=65)
        await self._log(
            AgentName.FACT_VERIFICATION,
            f"Verified {len(verified.get('verified_sources', []))} sources, "
            f"found {len(verified.get('contradictions', []))} contradictions",
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return verified

    async def _apply_verification_scores(self, source_rows: list, verified: dict) -> None:
        url_to_id = {r.url: r.id for r in source_rows}
        scored_by_url = {item.get("url"): item for item in verified.get("verified_sources", [])}

        async with get_db_context() as db:
            for url, source_id in url_to_id.items():
                scores = scored_by_url.get(url)
                if not scores:
                    continue
                row = await db.get(Source, source_id)
                if row:
                    row.domain_authority_score = scores.get("domain_authority_score")
                    row.source_age_score = scores.get("source_age_score")
                    row.citation_count_score = scores.get("citation_count_score")
                    row.trustworthiness_score = scores.get("trustworthiness_score")
                    row.verification_notes = {"notes": scores.get("notes", "")}

    # ── Stage 5: Knowledge Base Storage ──────────────────────────────────

    async def _stage_knowledge_storage(
        self, source_rows: list, extracted: list, verified: dict, user_id: uuid.UUID
    ) -> None:
        await self._update_session(status=SessionStatus.SUMMARIZING, progress_percent=68)
        t0 = time.monotonic()

        scored_by_url = {item.get("url"): item for item in verified.get("verified_sources", [])}
        payload = []
        for item in extracted:
            url = item.get("url")
            scores = scored_by_url.get(url, {})
            payload.append(
                {
                    "source_id": uuid.UUID(item["source_id"]) if item.get("source_id") else None,
                    "url": url,
                    "extracted_content": item.get("extracted_content", ""),
                    "trustworthiness_score": scores.get("trustworthiness_score", 0),
                }
            )

        result = await store_verified_content(
            research_session_id=self.research_session_id, user_id=user_id, verified_sources=payload
        )
        await self._log(
            AgentName.KNOWLEDGE_BASE,
            f"Indexed {result['total_chunks_stored']} chunks across {result['sources_indexed']} sources",
            duration_ms=(time.monotonic() - t0) * 1000,
        )

    # ── Stage 6: Summarization ───────────────────────────────────────────

    async def _stage_summarization(self, research_plan: dict, verified: dict) -> dict:
        t0 = time.monotonic()
        agent = build_summarization_agent()
        task = build_summarization_task(agent, research_plan, verified)
        raw = self._run_single_task(agent, task)
        summaries = _safe_json_parse(
            raw, fallback={"short_summary": "", "medium_summary": "", "detailed_summary": ""}
        )
        if not isinstance(summaries, dict):
            summaries = {"short_summary": "", "medium_summary": "", "detailed_summary": ""}

        await self._update_session(progress_percent=75)
        await self._log(
            AgentName.SUMMARIZATION, "Generated short/medium/detailed summaries",
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return summaries

    # ── Stage 7: Report Writing ──────────────────────────────────────────

    async def _stage_report_writing(self, research_plan: dict, verified: dict, summaries: dict) -> dict:
        await self._update_session(status=SessionStatus.WRITING_REPORT, progress_percent=78)
        t0 = time.monotonic()
        agent = build_report_writer_agent()
        task = build_report_writer_task(agent, research_plan, verified, summaries)
        raw = self._run_single_task(agent, task)
        sections = _safe_json_parse(raw, fallback={})
        if not isinstance(sections, dict):
            sections = {}

        await self._update_session(progress_percent=85)
        await self._log(
            AgentName.REPORT_WRITER, f"Drafted report: {sections.get('title', 'Untitled')}",
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return sections

    # ── Stage 8: Executive Summary ───────────────────────────────────────

    async def _stage_executive_summary(self, research_plan: dict, report_sections: dict) -> dict:
        await self._update_session(status=SessionStatus.GENERATING_EXECUTIVE_SUMMARY, progress_percent=88)
        t0 = time.monotonic()
        agent = build_executive_summary_agent()
        task = build_executive_summary_task(agent, research_plan, report_sections)
        raw = self._run_single_task(agent, task)
        block = _safe_json_parse(
            raw, fallback={"executive_summary": "", "key_takeaways": [], "risks": [], "opportunities": []}
        )
        if not isinstance(block, dict):
            block = {"executive_summary": "", "key_takeaways": [], "risks": [], "opportunities": []}

        await self._update_session(progress_percent=91)
        await self._log(
            AgentName.EXECUTIVE_SUMMARY, "Generated executive brief",
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return block

    # ── Stage 9: Citations ───────────────────────────────────────────────

    async def _stage_citations(self, source_rows: list) -> dict:
        await self._update_session(status=SessionStatus.GENERATING_CITATIONS, progress_percent=93)
        t0 = time.monotonic()
        source_payload = [
            {
                "source_id": str(r.id), "url": r.url, "title": r.title,
                "domain": r.domain, "published_date": r.published_date,
            }
            for r in source_rows
        ]
        citations = generate_all_citations(source_payload)
        await self._log(
            AgentName.CITATION, f"Generated {len(source_rows)} citations in APA/MLA/IEEE",
            duration_ms=(time.monotonic() - t0) * 1000,
        )
        return citations

    # ── Persist Report ───────────────────────────────────────────────────

    async def _persist_report(
        self, user_id: uuid.UUID, report_sections: dict, summaries: dict,
        exec_summary_block: dict, citations: dict, citation_style: str,
    ) -> uuid.UUID:
        async with get_db_context() as db:
            report = Report(
                research_session_id=self.research_session_id,
                user_id=user_id,
                title=report_sections.get("title", "Untitled Research Report"),
                abstract=report_sections.get("abstract"),
                introduction=report_sections.get("introduction"),
                key_findings=report_sections.get("key_findings"),
                analysis=report_sections.get("analysis"),
                recommendations=report_sections.get("recommendations"),
                conclusion=report_sections.get("conclusion"),
                short_summary=summaries.get("short_summary"),
                medium_summary=summaries.get("medium_summary"),
                detailed_summary=summaries.get("detailed_summary"),
                executive_summary=exec_summary_block.get("executive_summary"),
                key_takeaways=exec_summary_block.get("key_takeaways"),
                risks=exec_summary_block.get("risks"),
                opportunities=exec_summary_block.get("opportunities"),
                citations_apa=citations.get("apa"),
                citations_mla=citations.get("mla"),
                citations_ieee=citations.get("ieee"),
                default_citation_style=citation_style,
            )
            db.add(report)
            await db.flush()
            await db.refresh(report)
            return report.id

    # ── Stage 10: PDF Export ─────────────────────────────────────────────

    async def _stage_pdf_export(
        self, report_id: uuid.UUID, report_sections: dict, exec_summary_block: dict,
        citations: dict, citation_style: str,
    ) -> None:
        await self._update_session(status=SessionStatus.EXPORTING_PDF, progress_percent=96)
        t0 = time.monotonic()

        pdf_path = await generate_report_pdf(
            report_id=report_id,
            title=report_sections.get("title", "Untitled Research Report"),
            sections=report_sections,
            executive_summary_block=exec_summary_block,
            citations=citations,
            citation_style=citation_style,
        )

        async with get_db_context() as db:
            report = await db.get(Report, report_id)
            if report:
                report.pdf_file_path = pdf_path
                report.pdf_generated_at = datetime.now(timezone.utc)

        await self._log(
            AgentName.PDF_GENERATION, f"Exported PDF to {pdf_path}",
            duration_ms=(time.monotonic() - t0) * 1000,
        )


async def run_research_pipeline(
    research_session_id: uuid.UUID, query: str, user_id: uuid.UUID,
    max_sources: int = 10, citation_style: str = "apa",
) -> uuid.UUID:
    """Public entrypoint called by the Celery task / API layer."""
    runner = ResearchCrewRunner(research_session_id)
    return await runner.run(query, user_id, max_sources, citation_style)


async def apply_follow_up(report_id: uuid.UUID, instruction: str) -> uuid.UUID:
    """
    Real follow-up implementation: re-invokes the Report Writer agent with
    the user's instruction (e.g. "Expand section 3", "Make the
    recommendations more actionable") and the report's current sections as
    context, then persists whichever sections the model chose to revise.

    This replaces the earlier placeholder that only appended a text note
    without actually regenerating any content.
    """
    async with get_db_context() as db:
        report = await db.get(Report, report_id)
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        current_sections = {
            "title": report.title,
            "abstract": report.abstract,
            "introduction": report.introduction,
            "key_findings": report.key_findings,
            "analysis": report.analysis,
            "recommendations": report.recommendations,
            "conclusion": report.conclusion,
        }
        user_id = report.user_id

    await ResearchCrewRunner._apply_user_key_overrides(user_id)
    try:
        agent = build_report_writer_agent()
        task = build_follow_up_task(agent, current_sections, instruction)
        raw = ResearchCrewRunner._run_single_task(agent, task)
        revised = _safe_json_parse(raw, fallback={})
    finally:
        clear_llm_overrides()

    if not isinstance(revised, dict) or not revised:
        raise ValueError("The model did not return a usable revision — please try rephrasing your request.")

    async with get_db_context() as db:
        report = await db.get(Report, report_id)
        for key, value in revised.items():
            if hasattr(report, key) and value:
                setattr(report, key, value)
        report.version += 1
        await db.flush()
        await db.refresh(report)

        db.add(
            AgentLog(
                research_session_id=report.research_session_id,
                agent_name=AgentName.REPORT_WRITER,
                level=LogLevel.SUCCESS,
                message=f"Applied follow-up: {instruction[:80]}",
                details={"instruction": instruction, "revised_fields": list(revised.keys())},
            )
        )

        return_id = report.id

    return return_id
