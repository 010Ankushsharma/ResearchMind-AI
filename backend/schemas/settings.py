"""
schemas/settings.py

Pydantic schemas for the persisted Settings page: bring-your-own API keys
and research defaults.

SECURITY NOTE: `UserSettingsRead` deliberately never includes decrypted (or
even encrypted) key values — only boolean `*_key_configured` flags. The
frontend should never receive a usable key back after it's saved; it can
only know whether one is set, and overwrite/clear it via `UserSettingsUpdate`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserSettingsUpdate(BaseModel):
    # Use the sentinel `""` (empty string) to explicitly clear a stored key;
    # omit the field entirely (None / not sent) to leave the existing key untouched.
    openrouter_api_key: str | None = None
    groq_api_key: str | None = None
    tavily_api_key: str | None = None

    preferred_model: str | None = None
    default_max_sources: int | None = Field(default=None, ge=1, le=20)
    default_citation_style: str | None = Field(default=None, pattern="^(apa|mla|ieee)$")


class UserSettingsRead(BaseModel):
    openrouter_key_configured: bool
    groq_key_configured: bool
    tavily_key_configured: bool

    preferred_model: str | None
    default_max_sources: int
    default_citation_style: str
