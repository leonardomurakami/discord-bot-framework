"""Tests for /pause and /resume commands."""

from unittest.mock import AsyncMock, MagicMock

import pytest

GUILD_ID = 123456789


class TestPauseResumeCommands:
    """Test pause and resume command behavior."""

    @pytest.mark.asyncio
    async def test_pause_when_playing(self, music_plugin):
        """Pause should set pause state and broadcast."""
        plugin, player = music_plugin
        player.is_playing = True
        player.paused = False

        track = MagicMock()
        track.title = "Test Track"
        player.current = track

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        pause_cmd = next(c for c in commands if c.__name__ == "pause")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await pause_cmd(ctx)

        player.set_pause.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_pause_when_not_playing(self, music_plugin):
        """Pause when nothing is playing should respond with error."""
        plugin, player = music_plugin
        player.is_playing = False

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        pause_cmd = next(c for c in commands if c.__name__ == "pause")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await pause_cmd(ctx)

        player.set_pause.assert_not_called()
        plugin.smart_respond.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_already_paused(self, music_plugin):
        """Pause when already paused should respond with info."""
        plugin, player = music_plugin
        player.is_playing = True
        player.paused = True

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        pause_cmd = next(c for c in commands if c.__name__ == "pause")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await pause_cmd(ctx)

        player.set_pause.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_when_paused(self, music_plugin):
        """Resume should unset pause state and broadcast."""
        plugin, player = music_plugin
        player.paused = True

        track = MagicMock()
        track.title = "Test Track"
        player.current = track

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        resume_cmd = next(c for c in commands if c.__name__ == "resume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await resume_cmd(ctx)

        player.set_pause.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_resume_not_paused(self, music_plugin):
        """Resume when not paused should respond with info."""
        plugin, player = music_plugin
        player.paused = False

        track = MagicMock()
        track.title = "Test Track"
        player.current = track

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        resume_cmd = next(c for c in commands if c.__name__ == "resume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await resume_cmd(ctx)

        player.set_pause.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_no_track(self, music_plugin):
        """Resume with no current track should respond with error."""
        plugin, player = music_plugin
        player.current = None

        from plugins.music.commands.playback import setup_playback_commands

        commands = setup_playback_commands(plugin)
        resume_cmd = next(c for c in commands if c.__name__ == "resume")

        ctx = MagicMock()
        ctx.guild_id = GUILD_ID
        ctx.author = MagicMock(id=111111)
        ctx.author.mention = "<@111111>"
        plugin.smart_respond = AsyncMock()

        await resume_cmd(ctx)

        player.set_pause.assert_not_called()
