"""
api/analytics.py

Routes powering the "Analytics" dashboard page:
  GET /api/analytics/overview          - top-line stats (totals, avg confidence)
  GET /api/analytics/source-distribution - sources grouped by domain
  GET /api/analytics/research-timeline   - research session volume over time
  GET /api/analytics/confidence-scores   - trustworthiness score distribution
  GET /api/analytics/topic-clusters      - topic frequency for the topic-cluster bar chart
  GET /api/analytics/knowledge-graph     - node/edge graph of co-occurring topics for the
                                            interactive Knowledge Graph visualization
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.connection import get_db
from models.knowledge_document import KnowledgeDocument
from models.report import Report
from models.research_session import ResearchSession, SessionStatus
from models.source import Source
from models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnalyticsOverview(BaseModel):
    total_research_sessions: int
    total_reports_generated: int
    total_sources_collected: int
    average_trustworthiness_score: float | None
    sessions_in_progress: int


class ChartDataPoint(BaseModel):
    label: str
    value: float


class GraphNode(BaseModel):
    id: str
    label: str
    weight: int  # frequency — drives node size in the visualization


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: int  # co-occurrence count — drives edge thickness


class KnowledgeGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_sessions = await db.scalar(
        select(func.count(ResearchSession.id)).where(ResearchSession.user_id == current_user.id)
    )
    total_reports = await db.scalar(
        select(func.count(Report.id)).where(Report.user_id == current_user.id)
    )
    in_progress = await db.scalar(
        select(func.count(ResearchSession.id)).where(
            ResearchSession.user_id == current_user.id,
            ResearchSession.status.notin_([SessionStatus.COMPLETED, SessionStatus.FAILED]),
        )
    )

    source_stats = await db.execute(
        select(func.count(Source.id), func.avg(Source.trustworthiness_score))
        .join(ResearchSession, ResearchSession.id == Source.research_session_id)
        .where(ResearchSession.user_id == current_user.id)
    )
    total_sources, avg_trust = source_stats.one()

    return AnalyticsOverview(
        total_research_sessions=total_sessions or 0,
        total_reports_generated=total_reports or 0,
        total_sources_collected=total_sources or 0,
        average_trustworthiness_score=round(avg_trust, 1) if avg_trust is not None else None,
        sessions_in_progress=in_progress or 0,
    )


@router.get("/source-distribution", response_model=list[ChartDataPoint])
async def get_source_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    top_n: int = Query(default=10, ge=1, le=30),
):
    """Sources grouped by domain — feeds the 'Source Distribution' chart."""
    result = await db.execute(
        select(Source.domain, func.count(Source.id))
        .join(ResearchSession, ResearchSession.id == Source.research_session_id)
        .where(ResearchSession.user_id == current_user.id, Source.domain.isnot(None))
        .group_by(Source.domain)
        .order_by(func.count(Source.id).desc())
        .limit(top_n)
    )
    return [ChartDataPoint(label=domain or "unknown", value=count) for domain, count in result.all()]


@router.get("/research-timeline", response_model=list[ChartDataPoint])
async def get_research_timeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    days: int = Query(default=30, ge=1, le=365),
):
    """Research session volume per day over the trailing window — feeds the 'Research Timeline' chart."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(ResearchSession.created_at).where(
            ResearchSession.user_id == current_user.id, ResearchSession.created_at >= since
        )
    )
    counts = Counter(row[0].date().isoformat() for row in result.all())
    return [ChartDataPoint(label=day, value=count) for day, count in sorted(counts.items())]


@router.get("/confidence-scores", response_model=list[ChartDataPoint])
async def get_confidence_score_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Buckets source trustworthiness scores into ranges — feeds the 'Confidence Scores' chart."""
    result = await db.execute(
        select(Source.trustworthiness_score)
        .join(ResearchSession, ResearchSession.id == Source.research_session_id)
        .where(ResearchSession.user_id == current_user.id, Source.trustworthiness_score.isnot(None))
    )
    scores = [row[0] for row in result.all()]

    buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for score in scores:
        if score <= 20:
            buckets["0-20"] += 1
        elif score <= 40:
            buckets["21-40"] += 1
        elif score <= 60:
            buckets["41-60"] += 1
        elif score <= 80:
            buckets["61-80"] += 1
        else:
            buckets["81-100"] += 1

    return [ChartDataPoint(label=label, value=count) for label, count in buckets.items()]


@router.get("/topic-clusters", response_model=list[ChartDataPoint])
async def get_topic_clusters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    top_n: int = Query(default=15, ge=1, le=50),
):
    """Topic tag frequency across the knowledge base — feeds the topic-cluster chart / knowledge graph."""
    result = await db.execute(
        select(KnowledgeDocument.metadata_tags).where(
            KnowledgeDocument.user_id == current_user.id,
            KnowledgeDocument.metadata_tags.isnot(None),
        )
    )
    counter: Counter[str] = Counter()
    for (tags,) in result.all():
        if isinstance(tags, dict):
            for topic in tags.get("topics", []):
                counter[str(topic)] += 1

    return [ChartDataPoint(label=topic, value=count) for topic, count in counter.most_common(top_n)]


@router.get("/knowledge-graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    max_nodes: int = Query(default=40, ge=5, le=150),
):
    """
    Builds a topic co-occurrence graph: each distinct topic tag becomes a
    node (sized by frequency), and an edge connects two topics whenever
    they appear together on the same knowledge chunk (weighted by how often
    that pairing co-occurs). Powers the interactive Knowledge Graph
    visualization on the Analytics page.
    """
    result = await db.execute(
        select(KnowledgeDocument.metadata_tags).where(
            KnowledgeDocument.user_id == current_user.id,
            KnowledgeDocument.metadata_tags.isnot(None),
        )
    )

    node_freq: Counter[str] = Counter()
    edge_freq: Counter[tuple[str, str]] = Counter()

    for (tags,) in result.all():
        if not isinstance(tags, dict):
            continue
        topics = sorted(set(str(t) for t in tags.get("topics", [])))
        if not topics:
            continue

        node_freq.update(topics)

        # Every unique pair of topics co-occurring on this chunk gets an edge.
        for i in range(len(topics)):
            for j in range(i + 1, len(topics)):
                edge_freq[(topics[i], topics[j])] += 1

    top_topics = {topic for topic, _ in node_freq.most_common(max_nodes)}

    nodes = [
        GraphNode(id=topic, label=topic, weight=freq)
        for topic, freq in node_freq.items()
        if topic in top_topics
    ]
    edges = [
        GraphEdge(source=a, target=b, weight=freq)
        for (a, b), freq in edge_freq.items()
        if a in top_topics and b in top_topics
    ]

    return KnowledgeGraphResponse(nodes=nodes, edges=edges)
