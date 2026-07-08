"""
scripts/seed_db.py

Populates the local database with a demo user, a completed research
session, sample sources (with credibility scores), agent logs, and a full
report — so the frontend has something realistic to display immediately
after `docker compose up`, without needing to run a real (API-key-consuming)
research pipeline first.

Usage:
    cd backend
    python scripts/seed_db.py
    # or: make seed
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.connection import AsyncSessionLocal, init_db  # noqa: E402
from models.agent_log import AgentLog, AgentName, LogLevel  # noqa: E402
from models.report import CitationStyle, Report  # noqa: E402
from models.research_session import ResearchSession, SessionStatus  # noqa: E402
from models.source import Source  # noqa: E402
from models.user import User, UserRole  # noqa: E402

DEMO_CLERK_ID = "user_demo_seed_0001"
DEMO_EMAIL = "demo@research-platform.local"


async def seed() -> None:
    await init_db()

    async with AsyncSessionLocal() as db:
        # ── Demo user ────────────────────────────────────────────────────
        user = User(
            clerk_id=DEMO_CLERK_ID,
            email=DEMO_EMAIL,
            full_name="Demo Researcher",
            role=UserRole.MEMBER,
            research_count=1,
        )
        db.add(user)
        await db.flush()

        # ── Completed research session ──────────────────────────────────
        session = ResearchSession(
            user_id=user.id,
            query="Latest advancements in AI Agents",
            status=SessionStatus.COMPLETED,
            progress_percent=100,
            research_plan={
                "main_topic": "Latest advancements in AI Agents",
                "research_objective": "Summarize the current state and near-term trajectory of autonomous AI agents.",
                "subtopics": [
                    {
                        "title": "Multi-agent orchestration frameworks",
                        "search_queries": ["multi-agent AI frameworks 2026"],
                        "rationale": "Core to understanding current architecture trends.",
                    },
                    {
                        "title": "Enterprise adoption",
                        "search_queries": ["enterprise AI agent adoption 2026"],
                        "rationale": "Shows real-world traction.",
                    },
                ],
                "suggested_report_sections": ["Introduction", "Key Findings", "Analysis", "Conclusion"],
                "estimated_source_count": 3,
            },
            completed_at=datetime.now(timezone.utc),
        )
        db.add(session)
        await db.flush()

        # ── Sample sources ───────────────────────────────────────────────
        sources_data = [
            {
                "url": "https://www.nature.com/articles/ai-agents-2026",
                "title": "The Rise of Autonomous AI Agents",
                "domain": "nature.com",
                "snippet": "A survey of recent progress in agentic AI systems and multi-agent collaboration.",
                "trustworthiness_score": 92.0,
                "domain_authority_score": 95.0,
                "source_age_score": 88.0,
                "citation_count_score": 80.0,
                "citation_index": 1,
            },
            {
                "url": "https://arxiv.org/abs/2026.01234",
                "title": "Benchmarking Multi-Agent Coordination at Scale",
                "domain": "arxiv.org",
                "snippet": "We introduce a new benchmark for evaluating coordination strategies across agent swarms.",
                "trustworthiness_score": 85.0,
                "domain_authority_score": 90.0,
                "source_age_score": 95.0,
                "citation_count_score": 60.0,
                "citation_index": 2,
            },
            {
                "url": "https://example-techblog.com/ai-agents-enterprise",
                "title": "How Enterprises Are Deploying AI Agents in 2026",
                "domain": "example-techblog.com",
                "snippet": "A look at real-world enterprise deployments of autonomous agent systems.",
                "trustworthiness_score": 58.0,
                "domain_authority_score": 45.0,
                "source_age_score": 90.0,
                "citation_count_score": 40.0,
                "citation_index": 3,
            },
        ]

        sources = []
        for data in sources_data:
            source = Source(research_session_id=session.id, **data)
            db.add(source)
            sources.append(source)
        await db.flush()

        # ── Agent logs (a plausible timeline) ────────────────────────────
        base_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        log_entries = [
            (AgentName.RESEARCH_COORDINATOR, "Created research plan with 2 subtopics", 0),
            (AgentName.WEB_RESEARCH, "Found 3 candidate sources", 15),
            (AgentName.CONTENT_EXTRACTION, "Extracted content from 3 pages", 45),
            (AgentName.FACT_VERIFICATION, "Verified 3 sources, found 0 contradictions", 75),
            (AgentName.KNOWLEDGE_BASE, "Indexed 9 chunks across 3 sources", 95),
            (AgentName.SUMMARIZATION, "Generated short/medium/detailed summaries", 130),
            (AgentName.REPORT_WRITER, "Drafted report: The State of Autonomous AI Agents in 2026", 180),
            (AgentName.EXECUTIVE_SUMMARY, "Generated executive brief", 210),
            (AgentName.CITATION, "Generated 3 citations in APA/MLA/IEEE", 220),
            (AgentName.PDF_GENERATION, "Exported PDF to ./storage/reports/demo.pdf", 235),
        ]
        for agent_name, message, offset_seconds in log_entries:
            db.add(
                AgentLog(
                    research_session_id=session.id,
                    agent_name=agent_name,
                    level=LogLevel.SUCCESS,
                    message=message,
                    created_at=base_time + timedelta(seconds=offset_seconds),
                )
            )

        # ── Report ───────────────────────────────────────────────────────
        report = Report(
            research_session_id=session.id,
            user_id=user.id,
            title="The State of Autonomous AI Agents in 2026",
            abstract=(
                "This report surveys recent advancements in autonomous AI agents, covering "
                "multi-agent orchestration frameworks, coordination benchmarks, and enterprise "
                "adoption patterns observed through early 2026."
            ),
            introduction=(
                "Autonomous AI agents have moved from research prototypes to production "
                "deployments over the past two years. This report examines the architectural "
                "patterns, evaluation methods, and adoption trends shaping the field."
            ),
            key_findings=(
                "Multi-agent frameworks increasingly favor specialized agent roles over "
                "monolithic generalist agents.\n\n"
                "New benchmarks for agent coordination reveal significant performance gaps "
                "between research demos and production-grade reliability.\n\n"
                "Enterprise adoption is concentrated in research, customer support, and "
                "software engineering workflows."
            ),
            analysis=(
                "The shift toward specialized, role-based agent architectures mirrors broader "
                "software engineering principles of separation of concerns. However, "
                "coordination overhead between agents remains a key bottleneck, particularly "
                "in latency-sensitive applications."
            ),
            recommendations=(
                "Organizations evaluating agentic AI systems should start with narrow, "
                "well-bounded workflows before expanding to open-ended multi-agent pipelines, "
                "and should invest in observability tooling to monitor agent-to-agent handoffs."
            ),
            conclusion=(
                "Autonomous AI agents are maturing quickly, but production reliability still "
                "lags behind research demonstrations. The next 12-18 months will likely "
                "determine which orchestration patterns become industry standards."
            ),
            short_summary="AI agents are maturing fast, with multi-agent frameworks gaining traction in enterprise settings, though reliability gaps remain.",
            medium_summary=(
                "Recent research shows a shift toward specialized, role-based multi-agent "
                "architectures over single generalist agents. New benchmarks highlight "
                "coordination challenges at scale, while enterprises are adopting agents "
                "primarily for research, support, and engineering workflows."
            ),
            detailed_summary=(
                "Autonomous AI agents have progressed significantly, with the field "
                "converging on multi-agent orchestration patterns that assign specialized "
                "roles to individual agents rather than relying on a single generalist model. "
                "New benchmarking efforts have begun quantifying coordination overhead and "
                "reliability at scale, revealing meaningful gaps between demo-stage and "
                "production-stage performance. On the adoption side, enterprises are "
                "deploying agents primarily in well-bounded domains — research synthesis, "
                "customer support triage, and software engineering assistance — rather than "
                "fully open-ended autonomous workflows, reflecting a cautious, incremental "
                "rollout strategy across the industry."
            ),
            executive_summary=(
                "AI agents are transitioning from experimental prototypes to production tools, "
                "with the strongest enterprise traction in research, support, and engineering "
                "use cases. While multi-agent orchestration is becoming the dominant design "
                "pattern, coordination reliability remains the primary technical risk for "
                "teams considering broader deployment."
            ),
            key_takeaways=[
                "Specialized, role-based multi-agent architectures are outperforming generalist single-agent designs.",
                "Enterprise adoption is concentrated in well-bounded, narrow workflows.",
                "New benchmarks reveal a meaningful gap between demo and production reliability.",
            ],
            risks=[
                "Coordination overhead between agents can introduce unpredictable latency in production.",
                "Limited standardization across orchestration frameworks increases vendor lock-in risk.",
            ],
            opportunities=[
                "Early movers in narrow, well-scoped agentic workflows can capture efficiency gains ahead of competitors.",
                "Investment in agent observability tooling is likely to become a differentiator.",
            ],
            citations_apa=[
                {"source_id": str(sources[0].id), "formatted": "Nature. (2026). The Rise of Autonomous AI Agents. Retrieved from https://www.nature.com/articles/ai-agents-2026"},
                {"source_id": str(sources[1].id), "formatted": "Arxiv. (2026). Benchmarking Multi-Agent Coordination at Scale. Retrieved from https://arxiv.org/abs/2026.01234"},
                {"source_id": str(sources[2].id), "formatted": "Example Techblog. (2026). How Enterprises Are Deploying AI Agents in 2026. Retrieved from https://example-techblog.com/ai-agents-enterprise"},
            ],
            citations_mla=[
                {"source_id": str(sources[0].id), "formatted": '"The Rise of Autonomous AI Agents." Nature, 2026, https://www.nature.com/articles/ai-agents-2026.'},
            ],
            citations_ieee=[
                {"source_id": str(sources[0].id), "formatted": '[1] Nature, "The Rise of Autonomous AI Agents," 2026. [Online]. Available: https://www.nature.com/articles/ai-agents-2026'},
            ],
            default_citation_style=CitationStyle.APA,
            chart_data={
                "source_trustworthiness": {
                    "type": "bar",
                    "labels": ["nature.com", "arxiv.org", "example-techblog.com"],
                    "values": [92, 85, 58],
                }
            },
        )
        db.add(report)

        await db.commit()
        print(f"✅ Seeded demo data:")
        print(f"   User:    {user.email} (clerk_id={user.clerk_id})")
        print(f"   Session: {session.id}")
        print(f"   Report:  {report.id}")


if __name__ == "__main__":
    asyncio.run(seed())
