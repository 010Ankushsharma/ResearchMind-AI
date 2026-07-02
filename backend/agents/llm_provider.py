"""
agents/llm_provider.py

Centralized LLM provider for all CrewAI agents.

Strategy:
  1. PRIMARY  -> OpenRouter free models (DeepSeek V3 / R1, Qwen 3, Llama 3.3, Gemma 3)
  2. FALLBACK -> Groq free API (Llama 3.3, Gemma2) if OpenRouter fails or
                 rate-limits the request.

IMPLEMENTATION NOTE: modern CrewAI (0.1xx+) dropped its LangChain dependency
entirely in favor of `litellm` for LLM calls — `crewai.LLM` IS the supported
interface now, not a LangChain `BaseChatModel`. This module's `ResilientLLM`
subclasses CrewAI's own extension point, `crewai.llms.base_llm.BaseLLM`
(see https://docs.crewai.com — "Custom LLM Implementations"), rather than
wrapping a LangChain chat model — an earlier version of this file did the
latter, which both added an unnecessary dependency (langchain) AND silently
pinned an incompatible version range against crewai's own requirements
(crewai<0.70 requires langchain<0.3, but this app needs newer crewai
features), making `pip install` fail outright. Building on CrewAI's actual
BaseLLM contract avoids both problems.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from crewai import LLM
from crewai.llms.base_llm import BaseLLM
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from core.config import settings
from core.request_context import get_llm_overrides

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    """Used to pick the right-sized free model for the job."""
    FAST = "fast"            # quick extraction / classification tasks
    STANDARD = "standard"    # summarization, report writing
    REASONING = "reasoning"  # fact verification, multi-step planning


_MODEL_MAP_OPENROUTER = {
    TaskComplexity.FAST: settings.OPENROUTER_MODEL_FAST,
    TaskComplexity.STANDARD: settings.OPENROUTER_MODEL_PRIMARY,
    TaskComplexity.REASONING: settings.OPENROUTER_MODEL_REASONING,
}

_MODEL_MAP_GROQ = {
    TaskComplexity.FAST: settings.GROQ_MODEL_FAST,
    TaskComplexity.STANDARD: settings.GROQ_MODEL_PRIMARY,
    TaskComplexity.REASONING: settings.GROQ_MODEL_PRIMARY,
}


def _build_openrouter_llm(model: str, temperature: float) -> LLM:
    # litellm has a native "openrouter/" provider prefix that knows
    # OpenRouter's base URL and request shape — no manual base_url needed.
    overrides = get_llm_overrides()
    api_key = (overrides.openrouter_api_key if overrides else None) or settings.OPENROUTER_API_KEY
    return LLM(
        model=f"openrouter/{model}",
        api_key=api_key,
        temperature=temperature,
        extra_headers={
            "HTTP-Referer": "https://research-platform.local",
            "X-Title": "Multi-Agent Research Platform",
        },
    )


def _build_groq_llm(model: str, temperature: float) -> LLM:
    # Likewise, litellm's "groq/" prefix handles Groq's endpoint natively.
    overrides = get_llm_overrides()
    api_key = (overrides.groq_api_key if overrides else None) or settings.GROQ_API_KEY
    return LLM(
        model=f"groq/{model}",
        api_key=api_key,
        temperature=temperature,
    )


class ResilientLLM(BaseLLM):
    """
    A CrewAI `BaseLLM` implementation that tries OpenRouter first and
    transparently falls back to Groq on failure (rate limit, timeout,
    provider outage). Holds two real `crewai.LLM` instances internally and
    delegates `.call()` to whichever one succeeds.
    """

    def __init__(self, complexity: TaskComplexity = TaskComplexity.STANDARD, temperature: float = 0.3):
        primary_model = _MODEL_MAP_OPENROUTER[complexity]
        # BaseLLM.__init__ sets self.model / self.temperature / self.stop=[],
        # which CrewAI's agent executor reads/mutates directly (e.g. to push
        # stop-sequences in), so this MUST be called even though we delegate
        # the actual completion to the two inner LLM instances below.
        super().__init__(model=f"openrouter/{primary_model}", temperature=temperature)

        self.complexity = complexity
        self._primary = _build_openrouter_llm(primary_model, temperature)
        self._fallback = _build_groq_llm(_MODEL_MAP_GROQ[complexity], temperature)

    @retry(
        reraise=True,
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(Exception),
    )
    def _call_primary(self, *args, **kwargs):
        return self._primary.call(*args, **kwargs)

    def call(
        self,
        messages,
        tools: list[dict] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
    ):
        # Propagate any stop-words the agent executor has appended onto us
        # (via the `.stop` list — see crewai/agents/crew_agent_executor.py)
        # down to whichever inner LLM actually ends up handling the call.
        self._primary.stop = self.stop
        self._fallback.stop = self.stop

        try:
            return self._call_primary(
                messages, tools=tools, callbacks=callbacks, available_functions=available_functions
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "OpenRouter call failed (%s) — falling back to Groq for complexity=%s",
                exc,
                self.complexity,
            )
            return self._fallback.call(
                messages, tools=tools, callbacks=callbacks, available_functions=available_functions
            )

    def supports_function_calling(self) -> bool:
        try:
            return self._primary.supports_function_calling()
        except Exception:  # noqa: BLE001
            return True  # conservative default — most OpenRouter free models do support it

    def supports_stop_words(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        try:
            return self._primary.get_context_window_size()
        except Exception:  # noqa: BLE001
            return 8192  # safe-ish default for the free models in _MODEL_MAP_OPENROUTER


def get_llm(complexity: TaskComplexity = TaskComplexity.STANDARD, temperature: float = 0.3) -> ResilientLLM:
    """
    Factory used by every agent in `agents/*.py` to obtain an LLM instance
    sized to the task at hand.

        from agents.llm_provider import get_llm, TaskComplexity
        llm = get_llm(TaskComplexity.REASONING)
    """
    return ResilientLLM(complexity=complexity, temperature=temperature)
