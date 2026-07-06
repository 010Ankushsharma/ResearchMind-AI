"""
models/user_settings.py

UserSettings ORM model — persists the per-user preferences and (encrypted)
bring-your-own API keys configured on the Settings page. One row per user.

API keys are stored encrypted at rest via core/crypto.py (Fernet, keyed off
SECRET_KEY) and decrypted only transiently in-memory when building the LLM/
search clients for that user's research runs — never logged, never returned
in API responses in plaintext (see schemas/settings.py).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # ── Encrypted bring-your-own API keys (nullable -> fall back to shared
    #    platform keys from core.config.settings when not set) ───────────
    openrouter_key_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    groq_key_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    tavily_key_encrypted: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ── Preferences ──────────────────────────────────────────────────────
    preferred_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_max_sources: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    default_citation_style: Mapped[str] = mapped_column(String(10), default="apa", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<UserSettings user_id={self.user_id} preferred_model={self.preferred_model}>"
