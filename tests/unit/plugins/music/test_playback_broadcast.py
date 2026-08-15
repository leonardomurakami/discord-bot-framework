"""Tests for seek/position WebSocket broadcast in playback commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

GUILD_ID = 123456789


class TestPlaybackBroadcast:
    """Assert /seek and /position broadcast playback_update."""

    @pytest.mark.asyncio
    async def test_seek_broadcasts_playback_update(self, music_plugin):
        """After player.seek(), _broadcast_music_update should be called with 'playback_update'."""
        plugin, player = music_plugin

        # Setup player with a current track
        track = MagicMock()
        track.title = "Test Track"
        track.duration = 300000  # 5 minutes
        player.current = track
        player.position = 0

        # Import and setup playback commands
        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        seek_cmd = next(c for c in commands if c.__name__ == "seek")

        # Create a mock context
        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        with patch("plugins.music.commands.playback._broadcast_music_update", new_callable=AsyncMock) as mock_broadcast:
            await seek_cmd(ctx, position="1:30")
            mock_broadcast.assert_called_once_with(plugin, GUILD_ID, "playback_update")

    @pytest.mark.asyncio
    async def test_position_broadcasts_playback_update(self, music_plugin):
        """After computing position, _broadcast_music_update should be called with 'playback_update'."""
        plugin, player = music_plugin

        # Setup player with a current track
        track = MagicMock()
        track.title = "Test Track"
        track.duration = 300000  # 5 minutes
        player.current = track
        player.position = 90000  # 1:30

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        position_cmd = next(c for c in commands if c.__name__ == "position")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        with patch("plugins.music.commands.playback._broadcast_music_update", new_callable=AsyncMock) as mock_broadcast:
            await position_cmd(ctx)
            mock_broadcast.assert_called_once_with(plugin, GUILD_ID, "playback_update")

    @pytest.mark.asyncio
    async def test_seek_validates_bounds(self, music_plugin):
        """Seek should reject positions outside track bounds without broadcasting."""
        plugin, player = music_plugin

        track = MagicMock()
        track.title = "Test Track"
        track.duration = 300000  # 5 minutes
        player.current = track
        player.position = 0

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        seek_cmd = next(c for c in commands if c.__name__ == "seek")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        with patch("plugins.music.commands.playback._broadcast_music_update", new_callable=AsyncMock) as mock_broadcast:
            # 10 minutes > 5 minute track
            await seek_cmd(ctx, position="10:00")
            mock_broadcast.assert_not_called()
