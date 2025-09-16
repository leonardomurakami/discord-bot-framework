"""Tests for database manager functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.manager import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    @patch("bot.database.manager.settings")
    @patch("bot.database.manager.create_async_engine")
    @patch("bot.database.manager.async_sessionmaker")
    def test_database_manager_creation(self, mock_sessionmaker, mock_create_engine, mock_settings):
        """Test creating a DatabaseManager instance."""
        mock_settings.database_url = "sqlite+aiosqlite:///test.db"
        mock_settings.debug = False

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        db_manager = DatabaseManager("sqlite+aiosqlite:///test.db")

        assert db_manager.database_url == "sqlite+aiosqlite:///test.db"
        assert db_manager.engine == mock_engine

    @patch("bot.database.manager.settings")
    @patch("bot.database.manager.create_async_engine")
    @patch("bot.database.manager.async_sessionmaker")
    def test_database_manager_default_url(self, mock_sessionmaker, mock_create_engine, mock_settings):
        """Test DatabaseManager with default URL from settings."""
        mock_settings.database_url = "sqlite+aiosqlite:///default.db"
        mock_settings.debug = False

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        db_manager = DatabaseManager()

        assert db_manager.database_url == "sqlite+aiosqlite:///default.db"

    @patch("bot.database.manager.settings")
    @patch("bot.database.manager.create_async_engine")
    @patch("bot.database.manager.async_sessionmaker")
    @patch("bot.database.manager.Base")
    @pytest.mark.asyncio
    async def test_create_tables(self, mock_base, mock_sessionmaker, mock_create_engine, mock_settings):
        """Test table creation."""
        mock_settings.database_url = "sqlite+aiosqlite:///test.db"
        mock_settings.debug = False

        # Mock engine and connection context manager properly
        mock_conn = AsyncMock()
        mock_begin_context = MagicMock()
        mock_begin_context.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_begin_context.__aexit__ = AsyncMock(return_value=None)

        mock_engine = MagicMock()  # Use MagicMock, not AsyncMock for engine
        mock_engine.begin.return_value = mock_begin_context
        mock_create_engine.return_value = mock_engine

        db_manager = DatabaseManager("sqlite+aiosqlite:///test.db")

        await db_manager.create_tables()

        mock_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once()

    @patch("bot.database.manager.settings")
    @patch("bot.database.manager.create_async_engine")
    @patch("bot.database.manager.async_sessionmaker")
    @pytest.mark.asyncio
    async def test_session_context_manager(self, mock_sessionmaker, mock_create_engine, mock_settings):
        """Test session context manager."""
        mock_settings.database_url = "sqlite+aiosqlite:///test.db"
        mock_settings.debug = False

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_session = AsyncMock(spec=AsyncSession)
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_sessionmaker.return_value = mock_session_factory

        db_manager = DatabaseManager("sqlite+aiosqlite:///test.db")

        async with db_manager.session() as session:
            assert session == mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("bot.database.manager.settings")
    @patch("bot.database.manager.create_async_engine")
    @patch("bot.database.manager.async_sessionmaker")
    @pytest.mark.asyncio
    async def test_close_method(self, mock_sessionmaker, mock_create_engine, mock_settings):
        """Test database close method."""
        mock_settings.database_url = "sqlite+aiosqlite:///test.db"
        mock_settings.debug = False

        mock_engine = AsyncMock()
        mock_create_engine.return_value = mock_engine

        db_manager = DatabaseManager("sqlite+aiosqlite:///test.db")

        await db_manager.close()

        mock_engine.dispose.assert_called_once()

    def test_postgresql_url_conversion(self):
        """Test PostgreSQL URL conversion."""
        with patch("bot.database.manager.settings") as mock_settings:
            mock_settings.debug = False

            with patch("bot.database.manager.create_async_engine") as mock_create_engine:
                mock_engine = MagicMock()
                mock_create_engine.return_value = mock_engine

                with patch("bot.database.manager.async_sessionmaker"):
                    db_manager = DatabaseManager("postgresql://user:pass@localhost/db")

                    # Should convert to asyncpg URL
                    mock_create_engine.assert_called_once()
                    call_args = mock_create_engine.call_args
                    assert "postgresql+asyncpg://" in call_args[0][0]

    def test_unsupported_database_url(self):
        """Test error handling for unsupported database URLs."""
        with patch("bot.database.manager.settings") as mock_settings:
            mock_settings.debug = False

            with pytest.raises(ValueError, match="Unsupported database URL"):
                DatabaseManager("mysql://localhost/db")

    @patch("bot.database.manager.settings")
    @patch("bot.database.manager.create_async_engine")
    @patch("bot.database.manager.async_sessionmaker")
    @pytest.mark.asyncio
    async def test_create_tables_no_engine(self, mock_sessionmaker, mock_create_engine, mock_settings):
        """Test create_tables when engine is not initialized."""
        mock_settings.database_url = "sqlite+aiosqlite:///test.db"
        mock_settings.debug = False

        db_manager = DatabaseManager("sqlite+aiosqlite:///test.db")
        db_manager.engine = None

        with pytest.raises(RuntimeError, match="Database engine not initialized"):
            await db_manager.create_tables()

    @patch("bot.database.manager.settings")
    @patch("bot.database.manager.create_async_engine")
    @patch("bot.database.manager.async_sessionmaker")
    def test_debug_mode_enabled(self, mock_sessionmaker, mock_create_engine, mock_settings):
        """Test database creation with debug mode enabled."""
        mock_settings.database_url = "sqlite+aiosqlite:///test.db"
        mock_settings.debug = True

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        DatabaseManager("sqlite+aiosqlite:///test.db")

        # Should call create_async_engine with echo=True
        mock_create_engine.assert_called_once()
        call_kwargs = mock_create_engine.call_args[1]
        assert call_kwargs["echo"] is True
