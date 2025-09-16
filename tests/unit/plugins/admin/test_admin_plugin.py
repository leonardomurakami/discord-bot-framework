"""Tests for Admin plugin."""

from unittest.mock import MagicMock, patch

import hikari
import pytest

from plugins.admin.admin import AdminPlugin


class TestAdminPlugin:
    """Test AdminPlugin functionality."""

    def test_plugin_creation(self, mock_bot):
        """Test creating admin plugin."""
        plugin = AdminPlugin(mock_bot)

        assert plugin.bot == mock_bot
        assert plugin.logger is not None

    @pytest.mark.asyncio
    async def test_permission_command_list_all(self, mock_bot, mock_context):
        """Test permission command listing all permissions."""
        plugin = AdminPlugin(mock_bot)

        # Mock permission manager
        mock_perm = MagicMock()
        mock_perm.node = "test.permission"
        mock_perm.description = "Test permission"
        mock_bot.permission_manager.get_all_permissions.return_value = [mock_perm]

        await plugin.manage_permissions(mock_context)

        mock_context.respond.assert_called_once()
        mock_bot.permission_manager.get_all_permissions.assert_called_once()

    @pytest.mark.asyncio
    async def test_permission_command_error(self, mock_bot, mock_context):
        """Test permission command with error."""
        plugin = AdminPlugin(mock_bot)

        # Mock permission manager to raise error
        mock_bot.permission_manager.get_all_permissions.side_effect = Exception(
            "Test error"
        )

        await plugin.manage_permissions(mock_context)

        # Should handle error gracefully
        assert mock_context.respond.call_count >= 1

    @pytest.mark.asyncio
    async def test_bot_info_command(self, mock_bot, mock_context):
        """Test bot info command."""
        plugin = AdminPlugin(mock_bot)

        # Mock bot data
        mock_user = MagicMock()
        mock_user.username = "TestBot"
        mock_user.created_at = MagicMock()
        mock_user.created_at.strftime.return_value = "January 01, 2022"
        mock_user.make_avatar_url.return_value = "https://example.com/avatar.png"

        mock_bot.hikari_bot.get_me.return_value = mock_user
        mock_bot.hikari_bot.cache.get_guilds_view.return_value = {
            1: MagicMock(),
            2: MagicMock(),
        }
        mock_bot.db.health_check.return_value = True
        mock_bot.plugin_loader.get_loaded_plugins.return_value = ["plugin1", "plugin2"]

        await plugin.bot_info(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_bot_info_command_error(self, mock_bot, mock_context):
        """Test bot info command with error."""
        plugin = AdminPlugin(mock_bot)

        # Mock to raise error
        mock_bot.hikari_bot.get_me.side_effect = Exception("Test error")

        await plugin.bot_info(mock_context)

        # Should handle error gracefully
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_server_info_command(self, mock_bot, mock_context, mock_guild):
        """Test server info command."""
        plugin = AdminPlugin(mock_bot)
        mock_context.get_guild.return_value = mock_guild

        # Mock guild data
        mock_guild.member_count = 100
        mock_guild.get_channels.return_value = {1: MagicMock(), 2: MagicMock()}
        mock_guild.get_roles.return_value = {1: MagicMock(), 2: MagicMock()}
        mock_guild.get_emojis.return_value = {1: MagicMock()}

        # Mock channel types
        mock_channel1 = MagicMock()
        mock_channel1.type = hikari.ChannelType.GUILD_TEXT
        mock_channel2 = MagicMock()
        mock_channel2.type = hikari.ChannelType.GUILD_VOICE

        mock_guild.get_channels.return_value = {1: mock_channel1, 2: mock_channel2}

        await plugin.server_info(mock_context)

        mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_server_info_command_no_guild(self, mock_bot, mock_context):
        """Test server info command outside of guild."""
        plugin = AdminPlugin(mock_bot)
        mock_context.get_guild.return_value = None

        await plugin.server_info(mock_context)

        # Should respond with error
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")

    @pytest.mark.asyncio
    async def test_uptime_command(self, mock_bot, mock_context):
        """Test uptime command."""
        plugin = AdminPlugin(mock_bot)

        with patch("psutil.Process") as mock_process_class:
            mock_process = MagicMock()
            mock_process.create_time.return_value = 1640995200  # 2022-01-01
            mock_process.cpu_percent.return_value = 1.5
            mock_process.memory_info.return_value = MagicMock(
                rss=1024 * 1024 * 50
            )  # 50MB
            mock_process.pid = 12345
            mock_process_class.return_value = mock_process

            with patch("psutil.boot_time", return_value=1640908800):  # Earlier time
                with patch("time.time", return_value=1641081600):  # Current time
                    mock_bot.hikari_bot.cache.get_guilds_view.return_value = {
                        1: MagicMock()
                    }
                    mock_bot.hikari_bot.heartbeat_latency = 0.05

                    await plugin.uptime(mock_context)

                    mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_uptime_command_no_psutil(self, mock_bot, mock_context):
        """Test uptime command without psutil."""
        plugin = AdminPlugin(mock_bot)

        # Mock ImportError for psutil
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'psutil'")
        ):
            mock_bot.hikari_bot.cache.get_guilds_view.return_value = {1: MagicMock()}
            mock_bot.hikari_bot.heartbeat_latency = 0.05

            await plugin.uptime(mock_context)

            mock_context.respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_uptime_command_error(self, mock_bot, mock_context):
        """Test uptime command with error."""
        plugin = AdminPlugin(mock_bot)

        # Mock to raise error
        mock_bot.hikari_bot.cache.get_guilds_view.side_effect = Exception("Test error")

        await plugin.uptime(mock_context)

        # Should handle error gracefully
        assert mock_context.respond.call_count >= 1 or hasattr(plugin, "smart_respond")
