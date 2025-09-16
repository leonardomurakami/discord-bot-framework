"""Tests for core bot functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from bot.core.bot import DiscordBot


class TestDiscordBot:
    """Test DiscordBot core functionality."""

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    def test_bot_creation(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test creating a DiscordBot instance."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = []
        mock_settings.bot_prefix = "!"

        # Mock hikari bot
        mock_hikari_bot = MagicMock()
        mock_hikari.return_value = mock_hikari_bot

        # Mock lightbulb client
        mock_lightbulb_client = MagicMock()
        mock_lightbulb.return_value = mock_lightbulb_client

        bot = DiscordBot()

        assert bot.hikari_bot == mock_hikari_bot
        assert bot.bot == mock_lightbulb_client
        assert bot.plugin_loader is not None
        assert bot.permission_manager is not None
        assert bot.is_ready is False

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    def test_run_method(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test bot run method."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = []
        mock_settings.bot_prefix = "!"

        # Mock hikari bot
        mock_hikari_bot = MagicMock()
        mock_hikari.return_value = mock_hikari_bot

        bot = DiscordBot()

        # Test run method
        bot.run()

        mock_hikari_bot.run.assert_called_once()

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    @pytest.mark.asyncio
    async def test_initialize_systems(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test system initialization."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = []
        mock_settings.bot_prefix = "!"

        # Mock database operations
        mock_db.create_tables = AsyncMock()

        bot = DiscordBot()
        bot.permission_manager.initialize = AsyncMock()

        await bot._initialize_systems()

        mock_db.create_tables.assert_called_once()
        bot.permission_manager.initialize.assert_called_once()

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    @pytest.mark.asyncio
    async def test_cleanup(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test cleanup method."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = []
        mock_settings.bot_prefix = "!"

        # Mock database close
        mock_db.close = AsyncMock()

        bot = DiscordBot()
        bot.event_system.emit = AsyncMock()

        await bot._cleanup()

        mock_db.close.assert_called_once()
        bot.event_system.emit.assert_called()

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    def test_add_startup_task(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test adding startup tasks."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = []
        mock_settings.bot_prefix = "!"

        bot = DiscordBot()
        task = AsyncMock()

        bot.add_startup_task(task)

        assert task in bot._startup_tasks

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    @pytest.mark.asyncio
    async def test_get_guild_prefix(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test getting guild prefix."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = []
        mock_settings.bot_prefix = "!"

        bot = DiscordBot()

        prefix = await bot.get_guild_prefix(12345)

        assert prefix == "!"

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    @pytest.mark.asyncio
    async def test_load_plugins(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test plugin loading."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = ["test_plugin"]
        mock_settings.bot_prefix = "!"

        bot = DiscordBot()
        bot.plugin_loader.discover_plugins = MagicMock(return_value=["test_plugin"])
        bot.plugin_loader.load_all_plugins = AsyncMock()

        await bot._load_plugins()

        bot.plugin_loader.load_all_plugins.assert_called_once_with(["test_plugin"])

    @patch('bot.core.bot.settings')
    @patch('bot.core.bot.hikari.GatewayBot')
    @patch('bot.core.bot.lightbulb.client_from_app')
    @patch('bot.core.bot.miru.Client')
    @patch('bot.core.bot.db_manager')
    def test_bot_properties(self, mock_db, mock_miru, mock_lightbulb, mock_hikari, mock_settings):
        """Test bot properties and accessors."""
        # Mock settings
        mock_settings.discord_token = "test_token"
        mock_settings.plugin_directories = []
        mock_settings.enabled_plugins = []
        mock_settings.bot_prefix = "!"

        bot = DiscordBot()

        # Test that properties are accessible
        assert hasattr(bot, 'hikari_bot')
        assert hasattr(bot, 'bot')
        assert hasattr(bot, 'plugin_loader')
        assert hasattr(bot, 'permission_manager')
        assert hasattr(bot, 'db')
        assert hasattr(bot, 'event_system')
        assert hasattr(bot, 'is_ready')