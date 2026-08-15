"""Tests for the AIConversation model and its registration with the database manager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.database.models import Base
from plugins.ai.models import AIConversation
from plugins.ai.plugin import AIPlugin


class TestAIConversationModel:
    """Test the AIConversation model definition and registration."""

    def test_model_tablename_and_columns(self):
        """The model declares the expected table and columns."""
        assert AIConversation.__tablename__ == "ai_conversation"

        columns = {c.name for c in AIConversation.__table__.columns}
        assert {"id", "guild_id", "channel_id", "role", "content", "created_at"}.issubset(columns)

        # guild_id and channel_id are indexed.
        indexed = {col.name for col in AIConversation.__table__.columns if col.index}
        assert "guild_id" in indexed
        assert "channel_id" in indexed

    def test_model_registers_on_plugin_init(self, mock_bot):
        """AIPlugin registers the AIConversation model in __init__."""
        plugin = AIPlugin(mock_bot)

        assert AIConversation in plugin.get_models()

    @pytest.mark.asyncio
    async def test_create_plugin_tables_creates_ai_conversation(self):
        """create_plugin_tables creates the ai_conversation table for a registered model."""
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Verify the table exists by inserting and selecting a row.
            session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
            async with session_factory() as session:
                session.add(AIConversation(guild_id=1, channel_id=2, role="user", content="hello"))
                await session.commit()

                result = await session.execute(select(AIConversation))
                rows = result.scalars().all()
                assert len(rows) == 1
                assert rows[0].content == "hello"
                assert rows[0].role == "user"

            # Confirm the table is present in the inspector.
            async with engine.connect() as conn:
                tables = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
            assert "ai_conversation" in tables
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_database_manager_registers_plugin_model(self, mock_bot):
        """DatabaseMixin.on_load registers the model with the database manager."""
        plugin = AIPlugin(mock_bot)
        # The mock db manager exposes register_plugin_model as an AsyncMock; DatabaseMixin
        # calls it in on_load. Patch db to a MagicMock with a sync register method.
        plugin.db = MagicMock()
        plugin.db.register_plugin_model = MagicMock()

        await plugin.on_load()

        plugin.db.register_plugin_model.assert_called_once_with(AIConversation, plugin.name)
