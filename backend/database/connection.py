"""
database/connection.py

Async SQLAlchemy engine + session management for PostgreSQL.
Provides:
  - `Base`            declarative base for all ORM models
  - `engine`           the async engine instance
  - `AsyncSessionLocal` session factory
  - `get_db()`         FastAPI dependency that yields a DB session
  - `init_db()`        creates all tables (used on startup / for dev)
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


class Base(DeclarativeBase):
    """Base class for all ORM models in the platform."""
    pass


# ── Engine ───────────────────────────────────────────────────────────────
# `pool_pre_ping` avoids stale-connection errors on long-lived free-tier DBs.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

# ── Session Factory ─────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a DB session per request and
    guarantees it is closed afterwards, rolling back on error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context-manager variant for use outside FastAPI's DI system —
    e.g. inside CrewAI agent tools or Celery tasks.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Create all tables defined on `Base.metadata`.
    Intended for local development; production should use Alembic migrations.
    """
    # Import models here so they're registered on Base.metadata
    # before create_all is called (avoids circular imports at module load).
    from models import (  # noqa: F401
        agent_log,
        knowledge_document,
        report,
        research_session,
        source,
        user,
        user_settings,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine's connection pool on app shutdown."""
    await engine.dispose()
