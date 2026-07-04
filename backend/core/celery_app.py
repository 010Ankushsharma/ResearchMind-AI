"""
core/celery_app.py

Celery application instance, used by the `celery_worker` service in
docker-compose.yml (`celery -A core.celery_app worker --loglevel=info`).

Currently the API dispatches research runs via FastAPI `BackgroundTasks`
(see api/research.py) for simplicity. This Celery app is wired up and
ready for production traffic — swap the dispatch call to
`tasks.research_tasks.run_research_task.delay(...)` to move execution off
the API process entirely and gain retries, concurrency control, and
horizontal worker scaling.
"""

from __future__ import annotations

from celery import Celery

from core.config import settings

celery_app = Celery(
    "research_platform",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["tasks.research_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    # Research pipelines call multiple free-tier LLM/search APIs and can
    # legitimately take several minutes — avoid premature SIGKILL.
    task_time_limit=60 * 20,
    task_soft_time_limit=60 * 18,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)
