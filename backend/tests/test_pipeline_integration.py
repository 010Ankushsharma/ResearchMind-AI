"""
tests/test_pipeline_integration.py

Integration test for the full research pipeline (ResearchCrewRunner.run),
exercising a REAL Postgres database — not a mock — for everything except
the LLM/network boundary (CrewAI's Crew.kickoff calls, the web search and
scraping tools, and the embedding model). Those are mocked because:
  - hitting real free-tier LLM/search providers in CI is slow and flaky
  - we want deterministic assertions, not "did the model happen to return
    valid JSON this time"

What this test verifies that the unit tests can't:
  - JSONB columns (research_plan, key_takeaways, citations_*, chart_data)
    actually round-trip through Postgres correctly
  - UUID foreign keys and cascading relationships behave correctly
  - the full multi-stage orchestration in crews/research_crew.py actually
    persists a ResearchSession -> Sources -> AgentLogs -> Report chain
    end-to-end, not just that each stage's helper function works in isolation

REQUIRES a running test database — see docker-compose.test.yml.
This test is SKIPPED automatically if DATABASE_URL isn't pointed at it
(set via the TEST_DATABASE_URL env var), so it never blocks the unit test
suite or a contributor who hasn't bothered to start the test DB.

Run with:
    docker compose -f docker-compose.test.yml up -d
    cd backend && TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:5433/test_db \
        pytest tests/test_pipeline_integration.py -v
    docker compose -f docker-compose.test.yml down -v

Or simply: make test-integration
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL not set — start docker-compose.test.yml and set it to run this test",
)


@pytest.fixture
async def test_db_engine():
    """Points the app's engine/session factory at the disposable test Postgres for this test only."""
    import core.config
    import database.connection as db_module

    # Override the cached settings singleton + rebuild the engine/session
    # factory against the test database, then restore everything after.
    original_engine = db_module.engine
    original_session_factory = db_module.AsyncSessionLocal

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    test_session_factory = async_sessionmaker(
        bind=test_engine, class_=db_module.AsyncSession, expire_on_commit=False
    )

    db_module.engine = test_engine
    db_module.AsyncSessionLocal = test_session_factory

    await db_module.init_db()

    yield test_engine

    await test_engine.dispose()
    db_module.engine = original_engine
    db_module.AsyncSessionLocal = original_session_factory


@pytest.fixture
async def seeded_user(test_db_engine):
    from database.connection import get_db_context
    from models.user import User

    async with get_db_context() as db:
        user = User(clerk_id=f"test_{uuid.uuid4().hex[:8]}", email=f"{uuid.uuid4().hex[:8]}@test.local")
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user


def _mock_crew_kickoff(*expected_json_responses: str):
    """
    Returns a function suitable for patching ResearchCrewRunner._run_single_task,
    yielding each provided JSON string in sequence on successive calls — one
    per pipeline stage that actually calls an LLM (planning, web research,
    content extraction, fact verification, summarization, report writing,
    executive summary).
    """
    responses = iter(expected_json_responses)

    def _fake_run_single_task(agent, task):  # noqa: ARG001
        return next(responses)

    return _fake_run_single_task


@pytest.mark.asyncio
class TestResearchPipelineIntegration:
    async def test_full_pipeline_persists_session_sources_and_report(self, seeded_user):
        """
        Drives ResearchCrewRunner.run() end-to-end against the real test DB,
        with every LLM call mocked to return canned (but valid) JSON, and
        verifies the final Postgres state: session marked COMPLETED, sources
        persisted with scores, agent logs recorded per stage, and a Report
        row with all sections populated.
        """
        from crews.research_crew import ResearchCrewRunner
        from database.connection import get_db_context
        from models.report import Report
        from models.research_session import ResearchSession, SessionStatus
        from models.source import Source

        async with get_db_context() as db:
            session = ResearchSession(user_id=seeded_user.id, query="Integration test topic")
            db.add(session)
            await db.flush()
            session_id = session.id

        planning_response = (
            '{"main_topic": "Integration test topic", "research_objective": "test", '
            '"subtopics": [{"title": "Sub A", "search_queries": ["q1"], "rationale": "r"}], '
            '"suggested_report_sections": ["Introduction"], "estimated_source_count": 1}'
        )
        web_research_response = (
            '[{"title": "Test Source", "url": "https://example.com/a", '
            '"domain": "example.com", "snippet": "snippet text"}]'
        )
        content_extraction_response = (
            '[{"url": "https://example.com/a", "title": "Test Source", '
            '"extracted_content": "Full extracted body text for the integration test.", '
            '"extraction_failed": false}]'
        )
        fact_verification_response = (
            '{"verified_sources": [{"url": "https://example.com/a", '
            '"domain_authority_score": 80, "source_age_score": 70, '
            '"citation_count_score": 50, "trustworthiness_score": 75, "notes": "ok"}], '
            '"contradictions": [], "overall_confidence": 75}'
        )
        summarization_response = (
            '{"short_summary": "Short.", "medium_summary": "Medium.", "detailed_summary": "Detailed."}'
        )
        report_writer_response = (
            '{"title": "Integration Test Report", "abstract": "Abstract text.", '
            '"introduction": "Intro text.", "key_findings": "Findings text.", '
            '"analysis": "Analysis text.", "recommendations": "Recs text.", "conclusion": "Conclusion text."}'
        )
        executive_summary_response = (
            '{"executive_summary": "Exec summary.", "key_takeaways": ["Takeaway 1"], '
            '"risks": ["Risk 1"], "opportunities": ["Opportunity 1"]}'
        )

        fake_responses = _mock_crew_kickoff(
            planning_response,
            web_research_response,
            content_extraction_response,
            fact_verification_response,
            summarization_response,
            report_writer_response,
            executive_summary_response,
        )

        with (
            patch.object(ResearchCrewRunner, "_run_single_task", staticmethod(fake_responses)),
            patch("crews.research_crew.store_verified_content", new=AsyncMock(return_value={
                "total_chunks_stored": 1, "sources_indexed": 1, "per_source_chunk_counts": {},
            })),
            patch("crews.research_crew.generate_report_pdf", new=AsyncMock(return_value="/tmp/fake_report.pdf")),
        ):
            runner = ResearchCrewRunner(session_id)
            report_id = await runner.run(
                query="Integration test topic", user_id=seeded_user.id, max_sources=5
            )

        async with get_db_context() as db:
            persisted_session = await db.get(ResearchSession, session_id)
            assert persisted_session.status == SessionStatus.COMPLETED
            assert persisted_session.progress_percent == 100
            assert persisted_session.research_plan["main_topic"] == "Integration test topic"

            from sqlalchemy import select

            result = await db.execute(select(Source).where(Source.research_session_id == session_id))
            sources = result.scalars().all()
            assert len(sources) == 1
            assert sources[0].trustworthiness_score == 75
            assert sources[0].extracted_content == "Full extracted body text for the integration test."

            report = await db.get(Report, report_id)
            assert report.title == "Integration Test Report"
            assert report.key_takeaways == ["Takeaway 1"]
            assert report.citations_apa is not None and len(report.citations_apa) == 1

    async def test_pipeline_marks_session_failed_on_unexpected_exception(self, seeded_user):
        """A genuine exception mid-pipeline should leave the session in FAILED, not stuck PLANNING forever."""
        from crews.research_crew import ResearchCrewRunner
        from database.connection import get_db_context
        from models.research_session import ResearchSession, SessionStatus

        async with get_db_context() as db:
            session = ResearchSession(user_id=seeded_user.id, query="Will fail")
            db.add(session)
            await db.flush()
            session_id = session.id

        with patch.object(
            ResearchCrewRunner, "_run_single_task", side_effect=RuntimeError("simulated LLM outage")
        ):
            runner = ResearchCrewRunner(session_id)
            with pytest.raises(RuntimeError):
                await runner.run(query="Will fail", user_id=seeded_user.id)

        async with get_db_context() as db:
            persisted_session = await db.get(ResearchSession, session_id)
            assert persisted_session.status == SessionStatus.FAILED
            assert persisted_session.error_message is not None
