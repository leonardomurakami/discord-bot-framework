"""Tests for base plugin functionality."""

from unittest.mock import AsyncMock, MagicMock

import hikari
import pytest

from bot.plugins.base import BasePlugin


class TestBasePlugin:
    """Test BasePlugin class."""

    def test_plugin_creation(self, mock_bot):
        """Test creating a base plugin."""
        plugin = BasePlugin(mock_bot)

        assert plugin.bot == mock_bot
        assert plugin.logger is not None
        assert plugin.db == mock_bot.db
        assert plugin.permissions == mock_bot.permission_manager
        assert plugin.cache == mock_bot.cache

    @pytest.mark.asyncio
    async def test_on_load(self, mock_bot):
        """Test plugin on_load method."""
        plugin = BasePlugin(mock_bot)

        # Should not raise any exceptions
        await plugin.on_load()

    @pytest.mark.asyncio
    async def test_on_unload(self, mock_bot):
        """Test plugin on_unload method."""
        plugin = BasePlugin(mock_bot)

        # Should not raise any exceptions
        await plugin.on_unload()

    def test_create_embed_basic(self, mock_bot):
        """Test creating a basic embed."""
        plugin = BasePlugin(mock_bot)

        embed = plugin.create_embed()

        assert isinstance(embed, hikari.Embed)
        assert embed.title is None
        assert embed.description is None

    def test_create_embed_with_params(self, mock_bot):
        """Test creating an embed with parameters."""
        plugin = BasePlugin(mock_bot)

        embed = plugin.create_embed(
            title="Test Title",
            description="Test Description",
            color=hikari.Color(0xFF0000),
        )

        assert embed.title == "Test Title"
        assert embed.description == "Test Description"
        assert embed.color == hikari.Color(0xFF0000)

    @pytest.mark.asyncio
    async def test_smart_respond_basic(self, mock_bot, mock_context):
        """Test smart response with basic content."""
        plugin = BasePlugin(mock_bot)

        await plugin.smart_respond(mock_context, "Test message")

        mock_context.respond.assert_called_once_with(content="Test message")

    @pytest.mark.asyncio
    async def test_smart_respond_with_embed(self, mock_bot, mock_context):
        """Test smart response with embed."""
        plugin = BasePlugin(mock_bot)
        embed = MagicMock(spec=hikari.Embed)

        await plugin.smart_respond(mock_context, embed=embed)

        mock_context.respond.assert_called_once_with(embed=embed)

    @pytest.mark.asyncio
    async def test_smart_respond_ephemeral(self, mock_bot, mock_context):
        """Test smart response with ephemeral flag."""
        plugin = BasePlugin(mock_bot)

        await plugin.smart_respond(mock_context, "Test message", ephemeral=True)

        mock_context.respond.assert_called_once_with(flags=hikari.MessageFlag.EPHEMERAL, content="Test message")

    @pytest.mark.asyncio
    async def test_smart_respond_error_handling(self, mock_bot, mock_context):
        """Test smart response error handling."""
        plugin = BasePlugin(mock_bot)

        # Mock respond to fail first time, succeed second time
        mock_context.respond = AsyncMock(side_effect=[Exception("Response failed"), None])

        # Should handle the error and try again without flags
        await plugin.smart_respond(mock_context, "Test message")

        # Should be called twice - first fails, second succeeds
        assert mock_context.respond.call_count == 2

    @pytest.mark.asyncio
    async def test_log_command_usage_success(self, mock_bot, mock_context):
        """Test logging successful command usage."""
        plugin = BasePlugin(mock_bot)

        # Should not raise any exceptions
        await plugin.log_command_usage(mock_context, "test_command", True)

    @pytest.mark.asyncio
    async def test_log_command_usage_failure(self, mock_bot, mock_context):
        """Test logging failed command usage."""
        plugin = BasePlugin(mock_bot)

        # Should not raise any exceptions
        await plugin.log_command_usage(mock_context, "test_command", False, "Test error")

    @pytest.mark.asyncio
    async def test_log_command_usage_with_analytics(self, mock_bot, mock_context):
        """Test logging command usage with database logging."""
        plugin = BasePlugin(mock_bot)

        # Mock database session
        mock_session = AsyncMock()
        mock_bot.db.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_bot.db.session.return_value.__aexit__ = AsyncMock(return_value=None)

        await plugin.log_command_usage(mock_context, "test_command", True)

        # Verify database session was used
        mock_bot.db.session.assert_called_once()

    def test_repr(self, mock_bot):
        """Test plugin string representation."""
        plugin = BasePlugin(mock_bot)

        result = repr(plugin)

        assert "BasePlugin" in result

    def test_plugin_inheritance(self, mock_bot):
        """Test that plugins can be properly inherited."""

        class TestPlugin(BasePlugin):
            def __init__(self, bot):
                super().__init__(bot)
                self.test_attribute = "test_value"

            async def test_method(self):
                return "test_result"

        plugin = TestPlugin(mock_bot)

        assert plugin.bot == mock_bot
        assert plugin.test_attribute == "test_value"
        assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_plugin_custom_lifecycle(self, mock_bot):
        """Test custom plugin lifecycle methods."""

        class TestPlugin(BasePlugin):
            def __init__(self, bot):
                super().__init__(bot)
                self.loaded = False
                self.unloaded = False

            async def on_load(self):
                await super().on_load()
                self.loaded = True

            async def on_unload(self):
                await super().on_unload()
                self.unloaded = True

        plugin = TestPlugin(mock_bot)

        await plugin.on_load()
        assert plugin.loaded is True

        await plugin.on_unload()
        assert plugin.unloaded is True
