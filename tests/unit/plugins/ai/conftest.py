"""Shared fixtures for the AI plugin tests."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.database.models import Base
from plugins.ai.models import AIConversation  # noqa: F401  (ensures table is registered on Base)


@pytest_asyncio.fixture
async def ai_db_session() -> AsyncIterator[AsyncSession]:
    """Yield an async SQLAlchemy session backed by an in-memory SQLite database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    @asynccontextmanager
    async def _session_cm() -> AsyncIterator[AsyncSession]:
        session = session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    # The plugin helpers accept a session directly; yield a fresh session per test.
    async with _session_cm() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def ai_settings():
    """Return a lightweight settings stub with the AI-related fields."""

    class _AISettings:
        acpbox_url = "http://acpbox.local:8080"
        ai_model = "gpt-test"
        ai_api_key = None
        ai_system_prompt = "You are a helpful assistant."
        ai_max_tokens = 1000
        ai_temperature = 0.7
        ai_memory_turns = 2
        ai_request_timeout = 30

    return _AISettings()


@pytest.fixture
def ai_settings_with_key(ai_settings):
    """Settings stub with an API key set."""
    ai_settings.ai_api_key = "secret-key"
    return ai_settings


def make_turn(
    guild_id: int = 1, channel_id: int = 2, role: str = "user", content: str = "hi", *, offset_seconds: int = 0
) -> AIConversation:
    """Build an AIConversation row with a deterministic timestamp."""
    return AIConversation(
        guild_id=guild_id,
        channel_id=channel_id,
        role=role,
        content=content,
        created_at=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC).replace(second=offset_seconds),
    )
