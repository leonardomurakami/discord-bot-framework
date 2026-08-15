"""Tests for the /volume Discord command."""

from unittest.mock import AsyncMock, MagicMock

import pytest

GUILD_ID = 123456789


class TestVolumeCommand:
    """Test volume command bounds and behavior."""

    @pytest.mark.asyncio
    async def test_volume_over_100_rejected(self, music_plugin):
        """Volume > 100 should be rejected."""
        plugin, player = music_plugin
        from plugins.music.commands.voice import setup_voice_commands

        commands = setup_voice_commands(plugin)
        volume_cmd = next(c for c in commands if c.__name__ == "volume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await volume_cmd(ctx, level=150)

        # Should respond with error, not set volume
        plugin.smart_respond.assert_called_once()
        call_args = plugin.smart_respond.call_args
        assert "between 0 and 100" in str(call_args)
        player.set_volume.assert_not_called()

    @pytest.mark.asyncio
    async def test_volume_100_accepted(self, music_plugin):
        """Volume 100 should be applied."""
        plugin, player = music_plugin
        from plugins.music.commands.voice import setup_voice_commands

        commands = setup_voice_commands(plugin)
        volume_cmd = next(c for c in commands if c.__name__ == "volume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await volume_cmd(ctx, level=100)

        player.set_volume.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_volume_0_accepted(self, music_plugin):
        """Volume 0 should be applied."""
        plugin, player = music_plugin
        from plugins.music.commands.voice import setup_voice_commands

        commands = setup_voice_commands(plugin)
        volume_cmd = next(c for c in commands if c.__name__ == "volume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await volume_cmd(ctx, level=0)

        player.set_volume.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_volume_negative_rejected(self, music_plugin):
        """Volume < 0 should be rejected."""
        plugin, player = music_plugin
        from plugins.music.commands.voice import setup_voice_commands

        commands = setup_voice_commands(plugin)
        volume_cmd = next(c for c in commands if c.__name__ == "volume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await volume_cmd(ctx, level=-10)

        plugin.smart_respond.assert_called_once()
        call_args = plugin.smart_respond.call_args
        assert "between 0 and 100" in str(call_args)
        player.set_volume.assert_not_called()

    @pytest.mark.asyncio
    async def test_volume_no_arg_shows_current(self, music_plugin):
        """Volume with no argument should show current volume."""
        plugin, player = music_plugin
        player.volume = 75
        from plugins.music.commands.voice import setup_voice_commands

        commands = setup_voice_commands(plugin)
        volume_cmd = next(c for c in commands if c.__name__ == "volume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await volume_cmd(ctx, level=None)

        player.set_volume.assert_not_called()
        plugin.smart_respond.assert_called_once()
