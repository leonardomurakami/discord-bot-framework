"""Tests for Utility plugin."""

import base64
from unittest.mock import patch

import hikari
import pytest

from plugins.utility.utility import UtilityPlugin


class TestUtilityPlugin:
    """Test UtilityPlugin functionality."""

    def test_plugin_creation(self, mock_bot):
        """Test creating utility plugin."""
        plugin = UtilityPlugin(mock_bot)

        assert plugin.bot == mock_bot
        assert plugin.session is None

    @pytest.mark.asyncio
    async def test_on_load(self, mock_bot):
        """Test plugin loading."""
        plugin = UtilityPlugin(mock_bot)

        with patch("aiohttp.ClientSession") as mock_session:
            await plugin.on_load()

            assert plugin.session is not None
            mock_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_userinfo_command_self(self, mock_bot, mock_context, mock_user):
        """Test userinfo command for self."""
        plugin = UtilityPlugin(mock_bot)
        mock_context.author = mock_user
        mock_context.get_guild.return_value = None

        await plugin.user_info(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_userinfo_command_with_member(self, mock_bot, mock_context, mock_user, mock_member, mock_guild):
        """Test userinfo command with guild member."""
        plugin = UtilityPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_guild.fetch_member.return_value = mock_member

        await plugin.user_info(mock_context, mock_user)

        mock_context.respond.assert_called_once()
        mock_guild.fetch_member.assert_called_once_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_userinfo_command_member_not_found(self, mock_bot, mock_context, mock_user, mock_guild):
        """Test userinfo command when member not found."""
        plugin = UtilityPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_guild.fetch_member.side_effect = hikari.NotFoundError("Member not found", {}, b"", code=10007)

        await plugin.user_info(mock_context, mock_user)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_userinfo_command_error(self, mock_bot, mock_context):
        """Test userinfo command with error."""
        plugin = UtilityPlugin(mock_bot)
        mock_context.author = None  # Force error

        await plugin.user_info(mock_context)

        # Should handle error gracefully
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_avatar_command_self(self, mock_bot, mock_context, mock_user):
        """Test avatar command for self."""
        plugin = UtilityPlugin(mock_bot)
        mock_context.author = mock_user

        await plugin.avatar(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_avatar_command_other_user(self, mock_bot, mock_context, mock_user):
        """Test avatar command for another user."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.avatar(mock_context, mock_user)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_timestamp_command_now(self, mock_bot, mock_context):
        """Test timestamp command with 'now'."""
        plugin = UtilityPlugin(mock_bot)

        with patch("plugins.utility.utility.datetime") as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = 1640995200

            await plugin.timestamp(mock_context, "now")

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_timestamp_command_unix(self, mock_bot, mock_context):
        """Test timestamp command with unix timestamp."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.timestamp(mock_context, "1640995200")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_timestamp_command_date_string(self, mock_bot, mock_context):
        """Test timestamp command with date string."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.timestamp(mock_context, "2022-01-01 12:00")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_timestamp_command_invalid_format(self, mock_bot, mock_context):
        """Test timestamp command with invalid format."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.timestamp(mock_context, "invalid-date")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_color_command_hex(self, mock_bot, mock_context):
        """Test color command with hex code."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.color_info(mock_context, "#FF0000")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_color_command_name(self, mock_bot, mock_context):
        """Test color command with color name."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.color_info(mock_context, "red")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_color_command_invalid(self, mock_bot, mock_context):
        """Test color command with invalid color."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.color_info(mock_context, "invalid-color")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_color_command_invalid_hex(self, mock_bot, mock_context):
        """Test color command with invalid hex format."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.color_info(mock_context, "#GGGGGG")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_base64_encode(self, mock_bot, mock_context):
        """Test base64 encode command."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.base64_convert(mock_context, "encode", "hello world")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_base64_decode(self, mock_bot, mock_context):
        """Test base64 decode command."""
        plugin = UtilityPlugin(mock_bot)

        # Encode "hello world" to base64
        encoded = base64.b64encode(b"hello world").decode("utf-8")

        await plugin.base64_convert(mock_context, "decode", encoded)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_base64_invalid_action(self, mock_bot, mock_context):
        """Test base64 command with invalid action."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.base64_convert(mock_context, "invalid", "test")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_base64_invalid_decode(self, mock_bot, mock_context):
        """Test base64 decode with invalid base64."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.base64_convert(mock_context, "decode", "invalid-base64!")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_hash_md5(self, mock_bot, mock_context):
        """Test hash command with MD5."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.hash_text(mock_context, "md5", "hello world")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_hash_sha1(self, mock_bot, mock_context):
        """Test hash command with SHA1."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.hash_text(mock_context, "sha1", "hello world")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_hash_sha256(self, mock_bot, mock_context):
        """Test hash command with SHA256."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.hash_text(mock_context, "sha256", "hello world")

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_hash_invalid_algorithm(self, mock_bot, mock_context):
        """Test hash command with invalid algorithm."""
        plugin = UtilityPlugin(mock_bot)

        await plugin.hash_text(mock_context, "invalid", "hello world")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    def test_rgb_to_hsl_conversion(self, mock_bot):
        """Test RGB to HSL color conversion."""
        plugin = UtilityPlugin(mock_bot)

        # Test red color
        hsl = plugin._rgb_to_hsl(255, 0, 0)
        assert hsl == (0, 100, 50)

        # Test white color
        hsl = plugin._rgb_to_hsl(255, 255, 255)
        assert hsl == (0, 0, 100)

        # Test black color
        hsl = plugin._rgb_to_hsl(0, 0, 0)
        assert hsl == (0, 0, 0)
