"""Tests for message handler functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import hikari

from bot.core.message_handler import MessageCommandHandler, PrefixCommand, PrefixContext


class TestPrefixCommand:
    """Test PrefixCommand class."""

    def test_prefix_command_creation(self):
        """Test creating a prefix command."""
        callback = AsyncMock()
        cmd = PrefixCommand(
            name="test",
            callback=callback,
            description="Test command",
            aliases=["t"],
            permission_node="test.command",
            plugin_name="test_plugin"
        )

        assert cmd.name == "test"
        assert cmd.callback == callback
        assert cmd.description == "Test command"
        assert cmd.aliases == ["t"]
        assert cmd.permission_node == "test.command"
        assert cmd.plugin_name == "test_plugin"

    def test_prefix_command_defaults(self):
        """Test prefix command with default values."""
        callback = AsyncMock()
        cmd = PrefixCommand(name="test", callback=callback)

        assert cmd.name == "test"
        assert cmd.callback == callback
        assert cmd.description == ""
        assert cmd.aliases == []
        assert cmd.permission_node is None
        assert cmd.plugin_name is None
        assert cmd.arguments == []


class TestMessageCommandHandler:
    """Test MessageCommandHandler class."""

    def test_handler_creation(self, mock_bot):
        """Test creating a message command handler."""
        handler = MessageCommandHandler(mock_bot)

        assert handler.bot == mock_bot
        assert handler.commands == {}
        assert handler.prefix == "!"  # Default from settings

    def test_add_command(self, mock_bot):
        """Test adding a command."""
        handler = MessageCommandHandler(mock_bot)
        callback = AsyncMock()
        cmd = PrefixCommand(
            name="test",
            callback=callback,
            aliases=["t", "testing"]
        )

        handler.add_command(cmd)

        assert "test" in handler.commands
        assert "t" in handler.commands
        assert "testing" in handler.commands
        assert handler.commands["test"] == cmd
        assert handler.commands["t"] == cmd
        assert handler.commands["testing"] == cmd

    def test_remove_command(self, mock_bot):
        """Test removing a command."""
        handler = MessageCommandHandler(mock_bot)
        callback = AsyncMock()
        cmd = PrefixCommand(
            name="test",
            callback=callback,
            aliases=["t"]
        )

        handler.add_command(cmd)
        handler.remove_command("test")

        assert "test" not in handler.commands
        assert "t" not in handler.commands

    @pytest.mark.asyncio
    async def test_handle_message_bot_ignore(self, mock_bot, mock_message_event):
        """Test that bot messages are ignored."""
        handler = MessageCommandHandler(mock_bot)
        mock_message_event.author.is_bot = True

        result = await handler.handle_message(mock_message_event)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_no_prefix(self, mock_bot, mock_message_event):
        """Test that messages without prefix are ignored."""
        handler = MessageCommandHandler(mock_bot)
        mock_message_event.content = "hello world"

        result = await handler.handle_message(mock_message_event)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_empty_content(self, mock_bot, mock_message_event):
        """Test that empty messages are ignored."""
        handler = MessageCommandHandler(mock_bot)
        mock_message_event.content = None

        result = await handler.handle_message(mock_message_event)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_only_prefix(self, mock_bot, mock_message_event):
        """Test that messages with only prefix are ignored."""
        handler = MessageCommandHandler(mock_bot)
        mock_message_event.content = "!"

        result = await handler.handle_message(mock_message_event)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_unknown_command(self, mock_bot, mock_message_event):
        """Test that unknown commands are ignored."""
        handler = MessageCommandHandler(mock_bot)
        mock_message_event.content = "!unknown"

        result = await handler.handle_message(mock_message_event)
        assert result is False

    @pytest.mark.asyncio
    async def test_handle_message_success(self, mock_bot, mock_message_event):
        """Test successful command execution."""
        handler = MessageCommandHandler(mock_bot)
        callback = AsyncMock()
        cmd = PrefixCommand(name="test", callback=callback)
        handler.add_command(cmd)
        mock_message_event.content = "!test arg1 arg2"

        result = await handler.handle_message(mock_message_event)

        assert result is True
        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_with_permissions(self, mock_bot, mock_message_event):
        """Test command execution with permission check."""
        handler = MessageCommandHandler(mock_bot)
        callback = AsyncMock()
        cmd = PrefixCommand(
            name="test",
            callback=callback,
            permission_node="test.command"
        )
        handler.add_command(cmd)
        mock_message_event.content = "!test"
        mock_bot.permission_manager.has_permission.return_value = True

        result = await handler.handle_message(mock_message_event)

        assert result is True
        callback.assert_called_once()
        mock_bot.permission_manager.has_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_permission_denied(self, mock_bot, mock_message_event):
        """Test command execution with permission denied."""
        handler = MessageCommandHandler(mock_bot)
        callback = AsyncMock()
        cmd = PrefixCommand(
            name="test",
            callback=callback,
            permission_node="test.command"
        )
        handler.add_command(cmd)
        mock_message_event.content = "!test"
        mock_bot.permission_manager.has_permission.return_value = False

        with patch.object(PrefixContext, 'respond', new=AsyncMock()) as mock_respond:
            result = await handler.handle_message(mock_message_event)

            assert result is True
            callback.assert_not_called()
            mock_respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_command_error(self, mock_bot, mock_message_event):
        """Test command execution with error."""
        handler = MessageCommandHandler(mock_bot)
        callback = AsyncMock(side_effect=Exception("Test error"))
        cmd = PrefixCommand(name="test", callback=callback)
        handler.add_command(cmd)
        mock_message_event.content = "!test"

        with patch.object(PrefixContext, 'respond', new=AsyncMock()) as mock_respond:
            result = await handler.handle_message(mock_message_event)

            assert result is True
            callback.assert_called_once()


class TestPrefixContext:
    """Test PrefixContext class."""

    def test_context_creation(self, mock_message_event, mock_bot):
        """Test creating a prefix context."""
        args = ["arg1", "arg2"]
        ctx = PrefixContext(mock_message_event, mock_bot, args)

        assert ctx.event == mock_message_event
        assert ctx.bot == mock_bot
        assert ctx.args == args
        assert ctx.author == mock_message_event.author
        assert ctx.member == mock_message_event.member
        assert ctx.guild_id == mock_message_event.guild_id
        assert ctx.channel_id == mock_message_event.channel_id

    def test_get_guild(self, mock_message_event, mock_bot, mock_guild):
        """Test getting guild from context."""
        ctx = PrefixContext(mock_message_event, mock_bot, [])
        mock_bot.hikari_bot.cache.get_guild.return_value = mock_guild

        result = ctx.get_guild()

        assert result == mock_guild
        mock_bot.hikari_bot.cache.get_guild.assert_called_once_with(mock_message_event.guild_id)

    def test_get_guild_no_guild_id(self, mock_message_event, mock_bot):
        """Test getting guild when no guild_id."""
        ctx = PrefixContext(mock_message_event, mock_bot, [])
        ctx.guild_id = None

        result = ctx.get_guild()

        assert result is None

    def test_get_channel(self, mock_message_event, mock_bot, mock_channel):
        """Test getting channel from context."""
        ctx = PrefixContext(mock_message_event, mock_bot, [])
        mock_message_event.get_channel.return_value = mock_channel

        result = ctx.get_channel()

        assert result == mock_channel

    @pytest.mark.asyncio
    async def test_respond(self, mock_message_event, mock_bot):
        """Test responding to a message."""
        mock_bot.hikari_bot.rest.create_message = AsyncMock()
        ctx = PrefixContext(mock_message_event, mock_bot, [])

        await ctx.respond("Test message")

        mock_bot.hikari_bot.rest.create_message.assert_called_once_with(
            mock_message_event.channel_id,
            content="Test message",
            embed=None,
            components=None
        )

    @pytest.mark.asyncio
    async def test_respond_with_embed(self, mock_message_event, mock_bot):
        """Test responding with an embed."""
        mock_bot.hikari_bot.rest.create_message = AsyncMock()
        ctx = PrefixContext(mock_message_event, mock_bot, [])
        embed = MagicMock(spec=hikari.Embed)

        await ctx.respond(embed=embed)

        mock_bot.hikari_bot.rest.create_message.assert_called_once_with(
            mock_message_event.channel_id,
            content=None,
            embed=embed,
            components=None
        )