"""
api/settings.py

Routes:
  GET /api/settings   - read the current user's saved preferences
                         (key *presence* only — never the key values)
  PUT /api/settings   - update preferences and/or BYO API keys

This is the real persistence layer backing the Settings page — replacing
the placeholder client-side-only UI from the initial scaffold. Keys are
encrypted at rest via core/crypto.py and decrypted only transiently inside
the research pipeline (see crews/research_crew.py's `_load_user_overrides`).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.crypto import encrypt_secret
from core.security import get_current_user
from database.connection import get_db
from models.user import User
from models.user_settings import UserSettings
from schemas.settings import UserSettingsRead, UserSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


async def _get_or_create_settings(db: AsyncSession, user_id) -> UserSettings:
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    row = result.scalar_one_or_none()
    if row is None:
        row = UserSettings(user_id=user_id)
        db.add(row)
        await db.flush()
        await db.refresh(row)
    return row


def _to_read_schema(row: UserSettings) -> UserSettingsRead:
    return UserSettingsRead(
        openrouter_key_configured=bool(row.openrouter_key_encrypted),
        groq_key_configured=bool(row.groq_key_encrypted),
        tavily_key_configured=bool(row.tavily_key_encrypted),
        preferred_model=row.preferred_model,
        default_max_sources=row.default_max_sources,
        default_citation_style=row.default_citation_style,
    )


def apply_settings_update(row: UserSettings, payload: UserSettingsUpdate) -> None:
    """
    Mutates `row` in place per `payload`, applying the same field semantics
    everywhere this is used (the live endpoint, and tests):

      - field omitted (None)   -> leave the existing stored value untouched
      - field set to ""        -> explicitly clear the stored (encrypted) key
      - field set to a value   -> encrypt and store it

    Pulled out of the route handler as a plain function (no DB session, no
    FastAPI dependencies) so it's directly unit-testable without spinning up
    a database — `row` just needs to be any object with these attributes,
    real ORM instance or test double alike.
    """
    if payload.openrouter_api_key is not None:
        row.openrouter_key_encrypted = encrypt_secret(payload.openrouter_api_key) or None
    if payload.groq_api_key is not None:
        row.groq_key_encrypted = encrypt_secret(payload.groq_api_key) or None
    if payload.tavily_api_key is not None:
        row.tavily_key_encrypted = encrypt_secret(payload.tavily_api_key) or None

    if payload.preferred_model is not None:
        row.preferred_model = payload.preferred_model
    if payload.default_max_sources is not None:
        row.default_max_sources = payload.default_max_sources
    if payload.default_citation_style is not None:
        row.default_citation_style = payload.default_citation_style


@router.get("", response_model=UserSettingsRead)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await _get_or_create_settings(db, current_user.id)
    return _to_read_schema(row)


@router.put("", response_model=UserSettingsRead)
async def update_settings(
    payload: UserSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await _get_or_create_settings(db, current_user.id)
    apply_settings_update(row, payload)
    await db.flush()
    await db.refresh(row)
    return _to_read_schema(row)
