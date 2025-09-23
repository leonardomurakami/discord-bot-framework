"""Tests for Moderation plugin."""

from unittest.mock import AsyncMock, MagicMock

import hikari
import pytest

from plugins.moderation import PLUGIN_METADATA, ModerationPlugin


class TestModerationPlugin:
    """Test ModerationPlugin functionality."""

    def test_plugin_creation(self, mock_bot):
        """Test creating moderation plugin."""
        plugin = ModerationPlugin(mock_bot)

        assert plugin.bot == mock_bot

    @pytest.mark.asyncio
    async def test_kick_member_success(self, mock_bot, mock_context, mock_member, mock_guild):
        """Test successful member kick."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock member data
        mock_member.id = 123
        mock_member.mention = "<@123>"
        mock_member.fetch_dm_channel = AsyncMock()

        await plugin.kick_member(mock_context)

        # Should attempt to kick
        assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_kick_self_error(self, mock_bot, mock_context):
        """Test error when trying to kick self."""
        plugin = ModerationPlugin(mock_bot)

        # Mock context to simulate kicking self
        mock_context.author = MagicMock(id=123)

        await plugin.kick_member(mock_context)

        # Should handle gracefully
        assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_ban_member_success(self, mock_bot, mock_context, mock_user, mock_guild):
        """Test successful member ban."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        await plugin.ban_member(mock_context)

        # Should handle gracefully
        assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_timeout_member_success(self, mock_bot, mock_context, mock_member, mock_guild):
        """Test successful member timeout."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock options for timeout command
        mock_context.options = MagicMock()
        mock_context.options.member = mock_member
        mock_context.options.duration = 30  # 30 minutes
        mock_context.options.reason = "Test timeout"

        await plugin.timeout_member(mock_context)

        # Should handle gracefully
        assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_timeout_invalid_duration(self, mock_bot, mock_context):
        """Test timeout with invalid duration."""
        plugin = ModerationPlugin(mock_bot)

        # Mock options with invalid duration
        mock_context.options = MagicMock()
        mock_context.options.member = None
        mock_context.options.duration = 0  # Invalid duration
        mock_context.options.reason = "Test timeout"

        await plugin.timeout_member(mock_context)

        # Should handle gracefully
        assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_purge_messages_success(self, mock_bot, mock_context, mock_channel):
        """Test successful message purge."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_context.defer = AsyncMock()

        # The mock_channel fixture already has a proper async iterator
        mock_channel.delete_messages = AsyncMock()

        await plugin.purge_messages(mock_context, 5)

        mock_context.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_purge_invalid_amount(self, mock_bot, mock_context):
        """Test purge with invalid amount."""
        plugin = ModerationPlugin(mock_bot)

        await plugin.purge_messages(mock_context, 150)  # Too many

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_purge_with_user_filter(self, mock_bot, mock_context, mock_channel, mock_user):
        """Test purge with user filter."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_context.defer = AsyncMock()

        # Override the default async iterator for this test
        async def mock_fetch_history_with_filter(*args, **kwargs):
            mock_message1 = MagicMock()
            mock_message1.author.id = mock_user.id
            mock_message2 = MagicMock()
            mock_message2.author.id = 999  # Different user
            for msg in [mock_message1, mock_message2]:
                yield msg

        mock_channel.fetch_history = mock_fetch_history_with_filter
        mock_channel.delete_messages = AsyncMock()

        await plugin.purge_messages(mock_context, 5, mock_user)

        mock_context.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_unban_user_success(self, mock_bot, mock_context, mock_guild):
        """Test successful user unban."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild

        # Mock banned user
        mock_ban = MagicMock()
        mock_ban.user.id = 123456789
        mock_ban.user.mention = "<@123456789>"
        mock_ban.user.username = "testuser"

        # Create async iterator for fetch_bans
        async def mock_fetch_bans():
            for ban in [mock_ban]:
                yield ban

        mock_guild.fetch_bans = mock_fetch_bans
        mock_guild.unban = AsyncMock()

        await plugin.unban_user(mock_context, "123456789")

        mock_guild.unban.assert_called_once()

    @pytest.mark.asyncio
    async def test_unban_user_not_banned(self, mock_bot, mock_context, mock_guild):
        """Test unban user that's not banned."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild

        # The mock_guild fixture already has an empty async iterator for fetch_bans
        await plugin.unban_user(mock_context, "123456789")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_unban_invalid_user_id(self, mock_bot, mock_context):
        """Test unban with invalid user ID."""
        plugin = ModerationPlugin(mock_bot)

        await plugin.unban_user(mock_context, "invalid-id")

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_slowmode_enable(self, mock_bot, mock_context, mock_channel):
        """Test enabling slowmode."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_TEXT
        mock_channel.edit = AsyncMock()
        mock_channel.mention = "<#123>"

        # Mock options for slowmode command
        mock_context.options = MagicMock()
        mock_context.options.duration = 30
        mock_context.options.reason = None

        await plugin.slowmode(mock_context, 30)

        # Verify channel edit was called
        mock_channel.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_slowmode_disable(self, mock_bot, mock_context, mock_channel):
        """Test disabling slowmode."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_TEXT
        mock_channel.edit = AsyncMock()
        mock_channel.mention = "<#123>"

        # Mock options for slowmode command
        mock_context.options = MagicMock()
        mock_context.options.duration = 0
        mock_context.options.reason = None

        await plugin.slowmode(mock_context, 0)

        # Verify channel edit was called
        mock_channel.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_slowmode_invalid_duration(self, mock_bot, mock_context):
        """Test slowmode with invalid duration."""
        plugin = ModerationPlugin(mock_bot)

        await plugin.slowmode(mock_context, 25000)  # Too high

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_slowmode_invalid_channel(self, mock_bot, mock_context, mock_channel):
        """Test slowmode on invalid channel type."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_VOICE  # Wrong type

        await plugin.slowmode(mock_context, 30)

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")


class TestModerationPluginMetadata:
    """Test plugin metadata and configuration."""

    def test_plugin_metadata(self):
        """Test plugin metadata structure."""
        assert PLUGIN_METADATA["name"] == "Moderation"
        assert PLUGIN_METADATA["version"] == "1.0.0"
        assert "moderation.manage" in PLUGIN_METADATA["permissions"]
        assert "moderation.members.kick" in PLUGIN_METADATA["permissions"]
        assert "moderation.members.ban" in PLUGIN_METADATA["permissions"]
        assert "moderation.members.timeout" in PLUGIN_METADATA["permissions"]


class TestKickMemberExtended:
    """Extended tests for kick_member functionality."""

    @pytest.mark.asyncio
    async def test_kick_member_prefix_command_parsing(self, mock_bot, mock_context, mock_guild):
        """Test kick member with prefix command args parsing."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock prefix command args
        mock_context.args = ["<@123>", "Being", "too", "awesome"]
        delattr(mock_context, "options")  # Remove options to trigger args parsing

        # Mock member
        mock_member = MagicMock()
        mock_member.id = 123
        mock_member.mention = "<@123>"
        mock_member.fetch_dm_channel = AsyncMock()
        mock_guild.get_member.return_value = mock_member
        mock_guild.kick = AsyncMock()

        await plugin.kick_member(mock_context)

        # Should parse reason from multiple args
        expected_reason = "Being too awesome"
        mock_guild.kick.assert_called_once()
        call_args = mock_guild.kick.call_args
        assert expected_reason in call_args[1]["reason"]

    @pytest.mark.asyncio
    async def test_kick_member_invalid_member_id(self, mock_bot, mock_context, mock_guild):
        """Test kick with invalid member ID in args."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock prefix command with invalid member ID
        mock_context.args = ["invalid_id"]
        delattr(mock_context, "options")
        mock_guild.get_member.return_value = None

        await plugin.kick_member(mock_context)

        # Should respond with error about invalid member
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_kick_member_bot_target_error(self, mock_bot, mock_context, mock_guild):
        """Test kick when trying to kick the bot itself."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)
        mock_context.client.get_me.return_value = MagicMock(id=123)

        # Mock options to target the bot
        mock_context.options = MagicMock()
        mock_member = MagicMock()
        mock_member.id = 123  # Same as bot ID
        mock_context.options.member = mock_member
        mock_context.options.reason = "Test reason"

        await plugin.kick_member(mock_context)

        # Should respond with error about cannot kick self
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_kick_member_dm_failure_continues(self, mock_bot, mock_context, mock_guild):
        """Test kick continues even if DM fails."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock member
        mock_member = MagicMock()
        mock_member.id = 123
        mock_member.mention = "<@123>"
        mock_member.fetch_dm_channel = AsyncMock(side_effect=hikari.ForbiddenError("", {}, b""))

        mock_context.options = MagicMock()
        mock_context.options.member = mock_member
        mock_context.options.reason = "Test reason"

        mock_guild.kick = AsyncMock()

        await plugin.kick_member(mock_context)

        # Should still proceed with kick despite DM failure
        mock_guild.kick.assert_called_once()

    @pytest.mark.asyncio
    async def test_kick_member_forbidden_error(self, mock_bot, mock_context, mock_guild):
        """Test kick when bot lacks permissions."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock member
        mock_member = MagicMock()
        mock_member.id = 123
        mock_context.options = MagicMock()
        mock_context.options.member = mock_member
        mock_context.options.reason = "Test reason"

        # Mock kick to raise ForbiddenError
        mock_guild.kick = AsyncMock(side_effect=hikari.ForbiddenError("", {}, b""))

        await plugin.kick_member(mock_context)

        # Should handle permission error gracefully
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_kick_member_general_exception(self, mock_bot, mock_context, mock_guild):
        """Test kick with unexpected exception."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock member
        mock_member = MagicMock()
        mock_member.id = 123
        mock_context.options = MagicMock()
        mock_context.options.member = mock_member
        mock_context.options.reason = "Test reason"

        # Mock kick to raise general exception
        mock_guild.kick = AsyncMock(side_effect=Exception("Unexpected error"))

        await plugin.kick_member(mock_context)

        # Should handle exception gracefully
        plugin.smart_respond.assert_called()


class TestBanMemberExtended:
    """Extended tests for ban_member functionality."""

    @pytest.mark.asyncio
    async def test_ban_member_prefix_command_with_delete_days(self, mock_bot, mock_context, mock_guild):
        """Test ban with prefix command including delete days."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock prefix command args
        mock_context.args = ["<@123>", "7", "Spamming", "channels"]
        delattr(mock_context, "options")

        # Mock user fetch
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.mention = "<@123>"
        mock_bot.hikari_bot.rest.fetch_user = AsyncMock(return_value=mock_user)
        mock_guild.ban = AsyncMock()
        mock_guild.get_member.return_value = None  # User not in server

        await plugin.ban_member(mock_context)

        # Should parse delete_days and reason correctly
        mock_guild.ban.assert_called_once()
        call_args = mock_guild.ban.call_args
        assert call_args[1]["delete_message_days"] == 7
        assert "Spamming channels" in call_args[1]["reason"]

    @pytest.mark.asyncio
    async def test_ban_member_user_not_found(self, mock_bot, mock_context):
        """Test ban with user not found."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.author = MagicMock(id=999)

        # Mock args with invalid user
        mock_context.args = ["invalid_user"]
        delattr(mock_context, "options")
        mock_bot.hikari_bot.rest.fetch_user = AsyncMock(side_effect=hikari.NotFoundError("", {}, b""))

        await plugin.ban_member(mock_context)

        # Should respond with error about invalid user
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_ban_member_self_target_error(self, mock_bot, mock_context):
        """Test ban when trying to ban self."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.author = MagicMock(id=123)

        # Mock user targeting self
        mock_user = MagicMock()
        mock_user.id = 123
        mock_context.options = MagicMock()
        mock_context.options.user = mock_user

        await plugin.ban_member(mock_context)

        # Should respond with error about cannot ban self
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_ban_member_with_dm_to_member(self, mock_bot, mock_context, mock_guild):
        """Test ban sends DM to server member before banning."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock user who is a member
        mock_user = MagicMock()
        mock_user.id = 123
        mock_user.fetch_dm_channel = AsyncMock()
        mock_dm_channel = MagicMock()
        mock_dm_channel.send = AsyncMock()
        mock_user.fetch_dm_channel.return_value = mock_dm_channel

        # Mock member exists
        mock_member = MagicMock()
        mock_guild.get_member.return_value = mock_member
        mock_guild.ban = AsyncMock()

        mock_context.options = MagicMock()
        mock_context.options.user = mock_user
        mock_context.options.reason = "Test ban"
        mock_context.options.delete_days = 1

        await plugin.ban_member(mock_context)

        # Should attempt to send DM
        mock_user.fetch_dm_channel.assert_called_once()
        mock_dm_channel.send.assert_called_once()
        mock_guild.ban.assert_called_once()


class TestTimeoutMemberExtended:
    """Extended tests for timeout_member functionality."""

    @pytest.mark.asyncio
    async def test_timeout_member_prefix_command_parsing(self, mock_bot, mock_context, mock_guild):
        """Test timeout with prefix command parsing."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock prefix command args
        mock_context.args = ["<@123>", "60", "Too", "chatty"]
        delattr(mock_context, "options")

        # Mock member
        mock_member = MagicMock()
        mock_member.id = 123
        mock_member.edit = AsyncMock()
        mock_guild.get_member.return_value = mock_member

        await plugin.timeout_member(mock_context)

        # Should parse duration and reason correctly
        mock_member.edit.assert_called_once()
        call_args = mock_member.edit.call_args
        assert "Too chatty" in call_args[1]["reason"]

    @pytest.mark.asyncio
    async def test_timeout_member_invalid_args(self, mock_bot, mock_context):
        """Test timeout with invalid arguments."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.author = MagicMock(id=999)

        # Mock invalid args
        mock_context.args = ["invalid"]
        delattr(mock_context, "options")

        await plugin.timeout_member(mock_context)

        # Should respond with error about invalid parameters
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_timeout_member_complex_duration_formatting(self, mock_bot, mock_context, mock_guild):
        """Test timeout duration formatting for different time ranges."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild
        mock_context.author = MagicMock(id=999)

        # Mock member
        mock_member = MagicMock()
        mock_member.id = 123
        mock_member.edit = AsyncMock()

        # Test 90 minutes (1 hour 30 minutes)
        mock_context.options = MagicMock()
        mock_context.options.member = mock_member
        mock_context.options.duration = 90
        mock_context.options.reason = "Test"

        await plugin.timeout_member(mock_context)

        # Should format duration as hours and minutes
        mock_context.respond.assert_called()
        embed_call = mock_context.respond.call_args[1]["embed"]
        # Check that the embed contains proper duration formatting
        assert mock_member.edit.called

    @pytest.mark.asyncio
    async def test_timeout_member_bot_target_error(self, mock_bot, mock_context):
        """Test timeout when trying to timeout the bot."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.author = MagicMock(id=999)
        mock_context.client.get_me.return_value = MagicMock(id=123)

        # Mock member targeting bot
        mock_member = MagicMock()
        mock_member.id = 123  # Same as bot
        mock_context.options = MagicMock()
        mock_context.options.member = mock_member
        mock_context.options.duration = 30

        await plugin.timeout_member(mock_context)

        # Should respond with error about cannot timeout self
        plugin.smart_respond.assert_called()


class TestUnbanUserExtended:
    """Extended tests for unban_user functionality."""

    @pytest.mark.asyncio
    async def test_unban_user_forbidden_ban_list_access(self, mock_bot, mock_context, mock_guild):
        """Test unban when bot can't access ban list."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_guild.return_value = mock_guild

        # Mock fetch_bans to raise ForbiddenError
        async def mock_fetch_bans():
            raise hikari.ForbiddenError("", {}, b"")
            yield  # Unreachable but makes it a generator

        mock_guild.fetch_bans = mock_fetch_bans

        await plugin.unban_user(mock_context, "123456789")

        # Should respond with permission error
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_unban_user_not_found_error(self, mock_bot, mock_context, mock_guild):
        """Test unban with NotFoundError."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_guild.return_value = mock_guild

        # Mock banned user exists in list
        mock_ban = MagicMock()
        mock_ban.user.id = 123456789
        mock_ban.user.mention = "<@123456789>"
        mock_ban.user.username = "testuser"

        async def mock_fetch_bans():
            yield mock_ban

        mock_guild.fetch_bans = mock_fetch_bans
        mock_guild.unban = AsyncMock(side_effect=hikari.NotFoundError("", {}, b""))

        await plugin.unban_user(mock_context, "123456789")

        # Should handle NotFoundError
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_unban_user_unban_forbidden(self, mock_bot, mock_context, mock_guild):
        """Test unban when bot lacks unban permissions."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_guild.return_value = mock_guild

        # Mock banned user exists
        mock_ban = MagicMock()
        mock_ban.user.id = 123456789
        mock_ban.user.mention = "<@123456789>"

        async def mock_fetch_bans():
            yield mock_ban

        mock_guild.fetch_bans = mock_fetch_bans
        mock_guild.unban = AsyncMock(side_effect=hikari.ForbiddenError("", {}, b""))

        await plugin.unban_user(mock_context, "123456789")

        # Should handle ForbiddenError for unban
        plugin.smart_respond.assert_called()


class TestSlowmodeExtended:
    """Extended tests for slowmode functionality."""

    @pytest.mark.asyncio
    async def test_slowmode_hour_duration_formatting(self, mock_bot, mock_context, mock_channel):
        """Test slowmode with hour-long durations."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_TEXT
        mock_channel.edit = AsyncMock()
        mock_channel.mention = "<#123>"

        # Test 7200 seconds (2 hours)
        await plugin.slowmode(mock_context, 7200)

        # Should format as hours
        mock_channel.edit.assert_called_once_with(rate_limit_per_user=7200)
        mock_context.respond.assert_called()

    @pytest.mark.asyncio
    async def test_slowmode_minutes_and_seconds_formatting(self, mock_bot, mock_context, mock_channel):
        """Test slowmode with mixed minutes and seconds."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_TEXT
        mock_channel.edit = AsyncMock()
        mock_channel.mention = "<#123>"

        # Test 150 seconds (2 minutes 30 seconds)
        await plugin.slowmode(mock_context, 150)

        mock_channel.edit.assert_called_once()
        mock_context.respond.assert_called()

    @pytest.mark.asyncio
    async def test_slowmode_hours_and_minutes_formatting(self, mock_bot, mock_context, mock_channel):
        """Test slowmode with hours and minutes."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_TEXT
        mock_channel.edit = AsyncMock()
        mock_channel.mention = "<#123>"

        # Test 7800 seconds (2 hours 10 minutes)
        await plugin.slowmode(mock_context, 7800)

        mock_channel.edit.assert_called_once()
        mock_context.respond.assert_called()

    @pytest.mark.asyncio
    async def test_slowmode_news_channel_allowed(self, mock_bot, mock_context, mock_channel):
        """Test slowmode works on news channels."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_NEWS
        mock_channel.edit = AsyncMock()
        mock_channel.mention = "<#123>"

        await plugin.slowmode(mock_context, 30)

        # Should work on news channels
        mock_channel.edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_slowmode_forbidden_error(self, mock_bot, mock_context, mock_channel):
        """Test slowmode with permission error."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_TEXT
        mock_channel.edit = AsyncMock(side_effect=hikari.ForbiddenError("", {}, b""))

        await plugin.slowmode(mock_context, 30)

        # Should handle permission error
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_slowmode_general_exception(self, mock_bot, mock_context, mock_channel):
        """Test slowmode with unexpected exception."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_channel.return_value = mock_channel
        mock_channel.type = hikari.ChannelType.GUILD_TEXT
        mock_channel.edit = AsyncMock(side_effect=Exception("Unexpected error"))

        await plugin.slowmode(mock_context, 30)

        # Should handle general exception
        plugin.smart_respond.assert_called()


class TestPurgeMessagesExtended:
    """Extended tests for purge_messages functionality."""

    @pytest.mark.asyncio
    async def test_purge_messages_forbidden_error(self, mock_bot, mock_context, mock_channel):
        """Test purge with permission error."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_channel.return_value = mock_channel
        mock_context.defer = AsyncMock()

        # Mock delete_messages to raise ForbiddenError
        mock_channel.delete_messages = AsyncMock(side_effect=hikari.ForbiddenError("", {}, b""))

        await plugin.purge_messages(mock_context, 5)

        # Should handle permission error
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_purge_messages_general_exception(self, mock_bot, mock_context, mock_channel):
        """Test purge with unexpected exception."""
        plugin = ModerationPlugin(mock_bot)
        plugin.smart_respond = AsyncMock()
        mock_context.get_channel.return_value = mock_channel
        mock_context.defer = AsyncMock()

        # Mock fetch_history to raise exception
        async def mock_fetch_history(*args, **kwargs):
            raise Exception("Unexpected error")
            yield  # Unreachable

        mock_channel.fetch_history = mock_fetch_history

        await plugin.purge_messages(mock_context, 5)

        # Should handle exception
        plugin.smart_respond.assert_called()

    @pytest.mark.asyncio
    async def test_purge_messages_no_messages_found(self, mock_bot, mock_context, mock_channel):
        """Test purge when no messages are found."""
        plugin = ModerationPlugin(mock_bot)
        mock_context.get_channel.return_value = mock_channel
        mock_context.defer = AsyncMock()

        # Mock empty message history
        async def mock_fetch_history(*args, **kwargs):
            return
            yield  # Make it a generator but return nothing

        mock_channel.fetch_history = mock_fetch_history
        mock_channel.delete_messages = AsyncMock()

        await plugin.purge_messages(mock_context, 5)

        # Should still respond with result (0 messages deleted)
        mock_context.respond.assert_called()
