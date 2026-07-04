"""
core/request_context.py

Async-safe, per-task context for things that must NOT be stored as global
mutable state (which would leak between concurrent users/requests):

  - request_id: for log correlation across a single HTTP request or
    Celery/background task execution
  - per-user override API keys (OpenRouter/Groq/Tavily): when a user has
    saved their own free-tier keys in Settings, the research pipeline
    should use THEIRS instead of the platform's shared defaults, but only
    for the duration of that user's pipeline run — never globally.

Implemented with `contextvars.ContextVar`, which is automatically isolated
per asyncio task (and per thread), so concurrent pipeline runs for
different users never see each other's overrides.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMKeyOverrides:
    openrouter_api_key: str | None = None
    groq_api_key: str | None = None
    tavily_api_key: str | None = None


_request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)
_llm_overrides_var: contextvars.ContextVar[LLMKeyOverrides | None] = contextvars.ContextVar(
    "llm_overrides", default=None
)


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    return _request_id_var.get()


def set_llm_overrides(overrides: LLMKeyOverrides | None) -> None:
    _llm_overrides_var.set(overrides)


def get_llm_overrides() -> LLMKeyOverrides | None:
    return _llm_overrides_var.get()


def clear_llm_overrides() -> None:
    _llm_overrides_var.set(None)
