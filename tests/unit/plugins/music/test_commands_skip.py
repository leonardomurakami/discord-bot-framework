"""Tests for the /skip command."""

from unittest.mock import AsyncMock, MagicMock

import pytest

GUILD_ID = 123456789


class TestSkipCommand:
    """Test skip command behavior."""

    @pytest.mark.asyncio
    async def test_skip_when_playing(self, music_plugin):
        """Skip should call player.skip() and broadcast."""
        plugin, player = music_plugin
        player.is_playing = True

        track = MagicMock()
        track.title = "Current Track"
        track.duration = 300000
        track.uri = "https://example.com/track"
        track.requester = 111111
        player.current = track

        next_track = MagicMock()
        next_track.title = "Next Track"
        next_track.duration = 200000
        next_track.uri = "https://example.com/next"
        next_track.requester = 222222
        player.queue = [next_track]

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        skip_cmd = next(c for c in commands if c.__name__ == "skip")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()
        plugin.fetch_user = AsyncMock(return_value=MagicMock(display_name="User", username="user"))

        await skip_cmd(ctx)

        player.skip.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_when_not_playing(self, music_plugin):
        """Skip when nothing is playing should respond with error."""
        plugin, player = music_plugin
        player.is_playing = False
        player.current = None

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        skip_cmd = next(c for c in commands if c.__name__ == "skip")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await skip_cmd(ctx)

        player.skip.assert_not_called()
        plugin.smart_respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_skip_no_guild(self, music_plugin):
        """Skip in DMs should respond with error."""
        plugin, player = music_plugin
        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        skip_cmd = next(c for c in commands if c.__name__ == "skip")

        ctx = MagicMock()
        ctx.guild_id = None
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await skip_cmd(ctx)

        player.skip.assert_not_called()
        plugin.smart_respond.assert_called_once()
