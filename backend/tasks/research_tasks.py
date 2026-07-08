"""
tasks/research_tasks.py

Celery task wrapper around `crews.research_crew.run_research_pipeline`.

This IS the production dispatch path: `api/research.py`'s POST /research
endpoint calls `run_research_task.delay(...)` rather than running the
pipeline in-process. If the API process restarts mid-run, the Celery
worker (a separate process — see the `celery_worker` service in
docker-compose.yml) keeps the job going independently, and failed tasks
can be retried without losing in-flight work.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from celery import Task
from celery.utils.log import get_task_logger

from core.celery_app import celery_app
from crews.research_crew import run_research_pipeline

logger = get_task_logger(__name__)


class ResearchTask(Task):
    """Base Celery Task class with shared retry/error-handling behavior."""

    autoretry_for = (ConnectionError, TimeoutError)
    retry_kwargs = {"max_retries": 2, "countdown": 10}
    retry_backoff = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: N803 (Celery's required signature)
        logger.error("Research task %s failed permanently: %s", task_id, exc)
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    base=ResearchTask,
    bind=True,
    name="tasks.research_tasks.run_research_task",
)
def run_research_task(
    self,
    research_session_id: str,
    query: str,
    user_id: str,
    max_sources: int = 10,
    citation_style: str = "apa",
) -> str:
    """
    Synchronous Celery task entrypoint that drives the async pipeline.

    Celery workers run tasks synchronously by default, so we spin up a
    dedicated event loop per task invocation to run the async
    `run_research_pipeline` coroutine to completion.
    """
    logger.info("Starting research task for session %s (query=%r)", research_session_id, query)

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        report_id: uuid.UUID = loop.run_until_complete(
            run_research_pipeline(
                research_session_id=uuid.UUID(research_session_id),
                query=query,
                user_id=uuid.UUID(user_id),
                max_sources=max_sources,
                citation_style=citation_style,
            )
        )
    finally:
        loop.close()

    logger.info("Completed research task for session %s -> report %s", research_session_id, report_id)
    return str(report_id)
