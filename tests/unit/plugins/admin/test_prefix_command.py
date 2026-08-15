"""Tests for the prefix command."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from plugins.admin.config import validate_prefix
from plugins.admin.plugin import AdminPlugin


class TestPrefixValidation:
    """Test the validate_prefix helper directly."""

    def test_valid_prefix(self):
        is_valid, msg = validate_prefix("?")
        assert is_valid is True
        assert msg == ""

    def test_valid_prefix_multi_char(self):
        is_valid, msg = validate_prefix("!!")
        assert is_valid is True
        assert msg == ""

    def test_prefix_too_long(self):
        is_valid, msg = validate_prefix("!!!!!!")
        assert is_valid is False
        assert "5 characters" in msg

    def test_prefix_empty(self):
        is_valid, msg = validate_prefix("")
        assert is_valid is False
        assert "empty" in msg.lower()

    def test_prefix_whitespace_only(self):
        is_valid, msg = validate_prefix("   ")
        assert is_valid is False
        assert "empty" in msg.lower() or "whitespace" in msg.lower()

    def test_prefix_disallowed_quote(self):
        is_valid, msg = validate_prefix("!'")
        assert is_valid is False
        assert "quotes" in msg.lower() or "backticks" in msg.lower()

    def test_prefix_disallowed_backtick(self):
        is_valid, msg = validate_prefix("!`")
        assert is_valid is False
        assert "quotes" in msg.lower() or "backticks" in msg.lower()

    def test_prefix_disallowed_newline(self):
        is_valid, msg = validate_prefix("!\n")
        assert is_valid is False
        assert "whitespace" in msg.lower()


class TestPrefixCommand:
    """Test the /prefix command."""

    @pytest.mark.asyncio
    async def test_view_current_prefix(self, mock_bot, mock_context):
        """Test viewing the current prefix."""
        plugin = AdminPlugin(mock_bot)
        mock_bot.get_guild_prefix = AsyncMock(return_value="!")
        mock_context.guild_id = 123456789

        await plugin.manage_prefix(mock_context, new_prefix=None)

        mock_context.respond.assert_called_once()
        embed = mock_context.respond.call_args.kwargs.get("embed")
        assert embed is not None

    @pytest.mark.asyncio
    async def test_set_valid_prefix(self, mock_bot, mock_context):
        """Test setting a valid prefix."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_guild = MagicMock()
        mock_guild.prefix = "!"
        mock_result.scalar_one_or_none.return_value = mock_guild
        mock_session.execute.return_value = mock_result

        with patch.object(plugin, "db_session") as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            await plugin.manage_prefix(mock_context, new_prefix="?")

            mock_context.respond.assert_called_once()
            embed = mock_context.respond.call_args.kwargs.get("embed")
            assert embed is not None

    @pytest.mark.asyncio
    async def test_prefix_too_long(self, mock_bot, mock_context):
        """Test rejecting a prefix that is too long."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        with patch.object(plugin, "smart_respond", new_callable=AsyncMock) as mock_respond:
            await plugin.manage_prefix(mock_context, new_prefix="!!!!!!")

            mock_respond.assert_called_once()
            embed = mock_respond.call_args.kwargs.get("embed")
            assert embed is not None

    @pytest.mark.asyncio
    async def test_prefix_empty(self, mock_bot, mock_context):
        """Test rejecting an empty/whitespace prefix."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        with patch.object(plugin, "smart_respond", new_callable=AsyncMock) as mock_respond:
            await plugin.manage_prefix(mock_context, new_prefix="   ")

            mock_respond.assert_called_once()
            embed = mock_respond.call_args.kwargs.get("embed")
            assert embed is not None

    @pytest.mark.asyncio
    async def test_prefix_disallowed_chars(self, mock_bot, mock_context):
        """Test rejecting a prefix with disallowed characters."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = 123456789

        with patch.object(plugin, "smart_respond", new_callable=AsyncMock) as mock_respond:
            await plugin.manage_prefix(mock_context, new_prefix="!'`")

            mock_respond.assert_called_once()
            embed = mock_respond.call_args.kwargs.get("embed")
            assert embed is not None

    @pytest.mark.asyncio
    async def test_prefix_no_guild(self, mock_bot, mock_context):
        """Test prefix command outside a guild."""
        plugin = AdminPlugin(mock_bot)
        mock_context.guild_id = None

        with patch.object(plugin, "smart_respond", new_callable=AsyncMock) as mock_respond:
            await plugin.manage_prefix(mock_context, new_prefix=None)

            mock_respond.assert_called_once()
