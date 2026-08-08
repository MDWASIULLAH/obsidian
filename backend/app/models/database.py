"""SENTINEL AI X — Database engine, session, and base model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Engine & Session Factory ────────────────────────────────────────

_settings = get_settings()

# SQLite/aiosqlite does not support the PostgreSQL-style connection
# pool arguments used below. Only apply those options to non-SQLite DBs.
if _settings.database_url.startswith("sqlite"):
    engine = create_async_engine(
        _settings.database_url,
        echo=_settings.debug,
    )
else:
    engine = create_async_engine(
        _settings.database_url,
        echo=_settings.debug,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency — yields an async DB session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Declarative Base ────────────────────────────────────────────────


class Base(DeclarativeBase):
    """
    Base model with common fields.

    Every table gets:
    - id:         UUID primary key (auto-generated)
    - created_at: Timestamp (server default)
    - updated_at: Timestamp (auto-updated)
    """

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
    )