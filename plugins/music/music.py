import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

import hikari
import lightbulb
import lavalink
from sqlalchemy import delete, func, select, update

from bot.core.utils import has_permissions
from bot.database.models import MusicQueue, MusicSession
from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command
from config.settings import settings

logger = logging.getLogger(__name__)


class MusicPlugin(BasePlugin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self.lavalink_client: lavalink.Client | None = None
        self.cleanup_task: asyncio.Task | None = None
        self.inactivity_timeout = 30  # seconds

    async def on_load(self) -> None:
        await super().on_load()

        # Initialize Lavalink client
        self.lavalink_client = lavalink.Client(self.bot.hikari_bot.get_me().id)

        # Add node with proper WebSocket connection
        self.lavalink_client.add_node(
            host=settings.lavalink_host,
            port=settings.lavalink_port,
            password=settings.lavalink_password,
            region="us",
            name="default",
            ssl=settings.lavalink_secure,
        )

        # Setup voice update handler for Hikari
        @self.bot.hikari_bot.listen(hikari.VoiceStateUpdateEvent)
        async def voice_state_update(event):
            # Transform Hikari event to Lavalink format
            if event.state.user_id == self.bot.hikari_bot.get_me().id:
                lavalink_data = {
                    't': 'VOICE_STATE_UPDATE',
                    'd': {
                        'guild_id': str(event.state.guild_id) if event.state.guild_id else None,
                        'channel_id': str(event.state.channel_id) if event.state.channel_id else None,
                        'user_id': str(event.state.user_id),
                        'session_id': event.state.session_id,
                        'deaf': event.state.is_guild_deafened,
                        'mute': event.state.is_guild_muted,
                        'self_deaf': event.state.is_self_deafened,
                        'self_mute': event.state.is_self_muted,
                        'suppress': event.state.is_suppressed,
                    }
                }
                await self.lavalink_client.voice_update_handler(lavalink_data)

        @self.bot.hikari_bot.listen(hikari.VoiceServerUpdateEvent)
        async def voice_server_update(event):
            # Transform Hikari event to Lavalink format
            lavalink_data = {
                't': 'VOICE_SERVER_UPDATE',
                'd': {
                    'guild_id': str(event.guild_id),
                    'endpoint': event.endpoint,
                    'token': event.token,
                }
            }
            await self.lavalink_client.voice_update_handler(lavalink_data)

        # Setup event listeners for lavalink
        self._setup_lavalink_events()

        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_inactive_sessions())

        self.logger.info("Music plugin loaded with Lavalink.py")

    async def on_unload(self) -> None:
        if self.cleanup_task:
            self.cleanup_task.cancel()

        if self.lavalink_client:
            await self.lavalink_client.destroy()

        await super().on_unload()

    def _setup_lavalink_events(self) -> None:
        @self.lavalink_client.add_event_hook
        async def on_track_end(event) -> None:
            if hasattr(event, 'track') and hasattr(event, 'player'):
                await self._handle_track_end(event)

        @self.lavalink_client.add_event_hook
        async def on_track_start(event) -> None:
            if hasattr(event, 'track') and hasattr(event, 'player'):
                await self._handle_track_start(event)

        @self.lavalink_client.add_event_hook
        async def on_track_exception(event) -> None:
            if hasattr(event, 'exception') and hasattr(event, 'player'):
                self.logger.error(f"Track exception in guild {event.player.guild_id}: {event.exception}")

    async def _handle_track_end(self, event) -> None:
        if not event.player.guild_id:
            return

        guild_id = event.player.guild_id
        self.logger.info(f"Track ended in guild {guild_id}, reason: {event.reason if hasattr(event, 'reason') else 'Unknown'}")

        try:
            async with self.bot.db.session() as session:
                # Get current session
                result = await session.execute(
                    select(MusicSession).where(MusicSession.guild_id == guild_id)
                )
                music_session = result.scalar_one_or_none()

                if not music_session:
                    return

                # Check repeat mode
                if music_session.repeat_mode == "track":
                    # Replay the same track
                    player = self.lavalink_client.player_manager.get(guild_id)
                    if player and event.track:
                        await player.play(event.track)
                        return

                # Get next track from queue
                next_track = await self._get_next_track(guild_id, session)

                if next_track:
                    player = self.lavalink_client.player_manager.get(guild_id)
                    if player:
                        search_result = await self.lavalink_client.get_tracks(next_track.track_identifier)
                        tracks = search_result.tracks if hasattr(search_result, 'tracks') else search_result
                        if tracks:
                            track = tracks[0]
                            await player.play(track)
                            # Update current position
                            music_session.current_track_position = next_track.position
                            music_session.last_activity = datetime.now(timezone.utc)
                            await session.commit()
                            return

                # No more tracks, handle repeat queue mode
                if music_session.repeat_mode == "queue":
                    await self._restart_queue(guild_id, session)
                else:
                    # Stop playback
                    music_session.is_playing = False
                    music_session.last_activity = datetime.now(timezone.utc)
                    await session.commit()

        except Exception as e:
            self.logger.error(f"Error handling track end: {e}")

    async def _handle_track_start(self, event) -> None:
        if not event.player.guild_id:
            return

        guild_id = event.player.guild_id
        self.logger.info(f"Track started in guild {guild_id}: {event.track.title if hasattr(event, 'track') and hasattr(event.track, 'title') else 'Unknown track'}")

        try:
            async with self.bot.db.session() as session:
                # Update session state
                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == guild_id)
                    .values(
                        is_playing=True,
                        is_paused=False,
                        last_activity=datetime.now(timezone.utc),
                    )
                )
                await session.commit()

        except Exception as e:
            self.logger.error(f"Error handling track start: {e}")

    async def _get_next_track(self, guild_id: int, session) -> MusicQueue | None:
        # Get current session
        result = await session.execute(
            select(MusicSession).where(MusicSession.guild_id == guild_id)
        )
        music_session = result.scalar_one_or_none()

        if not music_session:
            return None

        current_pos = music_session.current_track_position

        if music_session.shuffle_enabled:
            # Get random track from remaining queue
            result = await session.execute(
                select(MusicQueue)
                .where(
                    MusicQueue.guild_id == guild_id,
                    MusicQueue.position > current_pos
                )
            )
            tracks = result.scalars().all()
            return random.choice(tracks) if tracks else None
        else:
            # Get next track in order
            result = await session.execute(
                select(MusicQueue)
                .where(
                    MusicQueue.guild_id == guild_id,
                    MusicQueue.position > current_pos
                )
                .order_by(MusicQueue.position)
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _restart_queue(self, guild_id: int, session) -> None:
        # Reset to first track
        result = await session.execute(
            select(MusicQueue)
            .where(MusicQueue.guild_id == guild_id)
            .order_by(MusicQueue.position)
            .limit(1)
        )
        first_track = result.scalar_one_or_none()

        if first_track:
            player = self.lavalink_client.player_manager.get(guild_id)
            if player:
                search_result = await self.lavalink_client.get_tracks(first_track.track_identifier)
                tracks = search_result.tracks if hasattr(search_result, 'tracks') else search_result
                if tracks:
                    track = tracks[0]
                    await player.play(track)
                    await session.execute(
                        update(MusicSession)
                        .where(MusicSession.guild_id == guild_id)
                        .values(current_track_position=0)
                    )
                    await session.commit()

    async def _cleanup_inactive_sessions(self) -> None:
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                cutoff_time = datetime.now(timezone.utc) - timedelta(seconds=self.inactivity_timeout)

                async with self.bot.db.session() as session:
                    # Get inactive sessions
                    result = await session.execute(
                        select(MusicSession).where(
                            MusicSession.last_activity < cutoff_time,
                            MusicSession.is_playing == False
                        )
                    )
                    inactive_sessions = result.scalars().all()

                    for music_session in inactive_sessions:
                        guild_id = music_session.guild_id

                        # Check if auto-disconnect is enabled for this guild
                        auto_disconnect = await self.get_setting(guild_id, "auto_disconnect", True)

                        if auto_disconnect:
                            try:
                                player = self.lavalink_client.player_manager.get(guild_id)
                                if player:
                                    await player.disconnect()

                                # Clean up database
                                await session.delete(music_session)
                                await session.execute(
                                    delete(MusicQueue).where(MusicQueue.guild_id == guild_id)
                                )
                                await session.commit()

                                self.logger.info(f"Auto-disconnected from inactive guild {guild_id}")

                            except Exception as e:
                                self.logger.error(f"Error auto-disconnecting from guild {guild_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")

    async def _get_or_create_session(self, guild_id: int, voice_channel_id: int, text_channel_id: int) -> MusicSession:
        async with self.bot.db.session() as session:
            # Try to get existing session
            result = await session.execute(
                select(MusicSession).where(MusicSession.guild_id == guild_id)
            )
            music_session = result.scalar_one_or_none()

            if not music_session:
                # Create new session
                music_session = MusicSession(
                    guild_id=guild_id,
                    voice_channel_id=voice_channel_id,
                    text_channel_id=text_channel_id,
                )
                session.add(music_session)
                await session.commit()
                await session.refresh(music_session)
            else:
                # Update channels
                music_session.voice_channel_id = voice_channel_id
                music_session.text_channel_id = text_channel_id
                music_session.last_activity = datetime.now(timezone.utc)
                await session.commit()

            return music_session

    def _format_time(self, ms: int) -> str:
        """Format milliseconds to human-readable time."""
        seconds = ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @command(
        name="play",
        description="Play a song or add to queue",
        permission_node="music.play",
        arguments=[
            CommandArgument("query", hikari.OptionType.STRING, "Song name or URL to play")
        ],
    )
    async def play(self, ctx: lightbulb.Context, query: str) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        # Check if user is in voice channel
        voice_state = ctx.bot.hikari_bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
        if not voice_state or not voice_state.channel_id:
            await self.smart_respond(ctx, "You must be in a voice channel to use this command.", ephemeral=True)
            return

        voice_channel_id = voice_state.channel_id

        # Check bot permissions
        bot_member = ctx.bot.hikari_bot.cache.get_member(ctx.guild_id, ctx.bot.hikari_bot.get_me().id)
        guild = ctx.bot.hikari_bot.cache.get_guild(ctx.guild_id)
        voice_channel = ctx.bot.hikari_bot.cache.get_guild_channel(voice_channel_id)

        if bot_member and guild:
            # Check if bot has required voice permissions
            required_permissions = hikari.Permissions.CONNECT | hikari.Permissions.SPEAK

            if not has_permissions(bot_member, guild, required_permissions, voice_channel):
                await self.smart_respond(ctx, "I don't have permission to connect or speak in that voice channel.", ephemeral=True)
                return

        try:
            # Search for tracks
            self.logger.info(f"Searching for: ytsearch:{query}")
            search_result = await self.lavalink_client.get_tracks(f"ytsearch:{query}")
            tracks = search_result.tracks if hasattr(search_result, 'tracks') else search_result
            self.logger.info(f"Search result type: {type(search_result)}, tracks found: {len(tracks) if tracks else 0}")

            if not tracks:
                self.logger.warning(f"No tracks found for query: {query}")
                embed = self.create_embed(
                    title="❌ No Results",
                    description=f"No tracks found for: `{query}`",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            track = tracks[0]
            self.logger.info(f"Selected track: {track.title} by {track.author} (Duration: {track.duration}ms)")

            # Get or create player
            player = self.lavalink_client.player_manager.create(ctx.guild_id)
            self.logger.info(f"Player for guild {ctx.guild_id}: connected={player.is_connected}, position={player.position}")

            # Connect to voice channel using Hikari
            if not player.is_connected:
                self.logger.info(f"Connecting to voice channel {voice_channel_id}")
                await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, voice_channel_id)
            else:
                self.logger.info(f"Player already connected to voice channel")

            # Get or create session
            music_session = await self._get_or_create_session(
                ctx.guild_id, voice_channel_id, ctx.channel_id
            )

            # Add to queue
            async with self.bot.db.session() as session:
                # Get next position
                result = await session.execute(
                    select(func.coalesce(func.max(MusicQueue.position), -1))
                    .where(MusicQueue.guild_id == ctx.guild_id)
                )
                next_position = result.scalar() + 1

                # Add track to queue
                queue_item = MusicQueue(
                    guild_id=ctx.guild_id,
                    position=next_position,
                    track_identifier=track.track if hasattr(track, 'track') else str(track),
                    track_title=track.title,
                    track_author=track.author,
                    track_duration=track.duration,
                    track_uri=track.uri,
                    requester_id=ctx.author.id,
                )
                session.add(queue_item)
                await session.commit()

                # If nothing is playing, start playback
                if not music_session.is_playing:
                    self.logger.info(f"Starting playback of track: {track.title}")
                    await player.play(track)
                    # Set volume from session (default is 50 from database)
                    self.logger.info(f"Setting volume to {music_session.volume}%")
                    await player.set_volume(music_session.volume)
                    music_session.current_track_position = next_position
                    music_session.last_activity = datetime.now(timezone.utc)
                    await session.commit()
                    self.logger.info(f"Playback started successfully")

                    embed = self.create_embed(
                        title="🎵 Now Playing",
                        description=f"[{track.title}]({track.uri})\nBy: {track.author}",
                        color=hikari.Color(0x00FF00)
                    )
                else:
                    embed = self.create_embed(
                        title="🎵 Added to Queue",
                        description=f"[{track.title}]({track.uri})\nBy: {track.author}\nPosition: {next_position + 1}",
                        color=hikari.Color(0x0099FF)
                    )

                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "play", True)

        except Exception as e:
            self.logger.error(f"Error in play command: {e}")
            embed = self.create_embed(
                title="❌ Error",
                description=f"An error occurred: {str(e)}",
                color=hikari.Color(0xFF0000),
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)
            await self.log_command_usage(ctx, "play", False, str(e))

    @command(
        name="pause",
        description="Pause the current track",
        permission_node="music.manage",
    )
    async def pause(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            player = self.lavalink_client.player_manager.get(ctx.guild_id)
            if not player or not player.is_connected:
                embed = self.create_embed(
                    title="❌ Not Playing",
                    description="I'm not playing anything.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await player.set_pause(True)

            async with self.bot.db.session() as session:
                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == ctx.guild_id)
                    .values(is_paused=True, last_activity=datetime.now(timezone.utc))
                )
                await session.commit()

            embed = self.create_embed(
                title="⏸️ Paused",
                description="Playback has been paused.",
                color=hikari.Color(0xFFAA00),
            )
            await self.smart_respond(ctx, embed=embed)
            await self.log_command_usage(ctx, "pause", True)

        except Exception as e:
            self.logger.error(f"Error in pause command: {e}")
            await self.log_command_usage(ctx, "pause", False, str(e))

    @command(
        name="resume",
        description="Resume the current track",
        permission_node="music.manage",
    )
    async def resume(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            player = self.lavalink_client.player_manager.get(ctx.guild_id)
            if not player or not player.is_connected:
                embed = self.create_embed(
                    title="❌ Not Playing",
                    description="I'm not playing anything.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await player.set_pause(False)

            async with self.bot.db.session() as session:
                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == ctx.guild_id)
                    .values(is_paused=False, last_activity=datetime.now(timezone.utc))
                )
                await session.commit()

            embed = self.create_embed(
                title="▶️ Resumed",
                description="Playback has been resumed.",
                color=hikari.Color(0x00FF00),
            )
            await self.smart_respond(ctx, embed=embed)
            await self.log_command_usage(ctx, "resume", True)

        except Exception as e:
            self.logger.error(f"Error in resume command: {e}")
            await self.log_command_usage(ctx, "resume", False, str(e))

    @command(
        name="stop",
        description="Stop playback and clear the queue",
        permission_node="music.manage",
    )
    async def stop(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            player = self.lavalink_client.player_manager.get(ctx.guild_id)
            if not player or not player.is_connected:
                embed = self.create_embed(
                    title="❌ Not Playing",
                    description="I'm not playing anything.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await player.stop()

            async with self.bot.db.session() as session:
                # Clear queue and session
                await session.execute(
                    delete(MusicQueue).where(MusicQueue.guild_id == ctx.guild_id)
                )
                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == ctx.guild_id)
                    .values(
                        is_playing=False,
                        is_paused=False,
                        current_track_position=0,
                        last_activity=datetime.now(timezone.utc)
                    )
                )
                await session.commit()

            embed = self.create_embed(
                title="⏹️ Stopped",
                description="Stopped playback and cleared the queue.",
                color=hikari.Color(0xFFAA00),
            )
            await self.smart_respond(ctx, embed=embed)
            await self.log_command_usage(ctx, "stop", True)

        except Exception as e:
            self.logger.error(f"Error in stop command: {e}")
            await self.log_command_usage(ctx, "stop", False, str(e))

    @command(
        name="skip",
        description="Skip the current track",
        permission_node="music.manage",
    )
    async def skip(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            player = self.lavalink_client.player_manager.get(ctx.guild_id)
            if not player or not player.is_connected:
                embed = self.create_embed(
                    title="❌ Not Playing",
                    description="I'm not playing anything.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await player.skip()
            embed = self.create_embed(
                title="⏭️ Skipped",
                description="Skipped to the next track.",
                color=hikari.Color(0x0099FF),
            )
            await self.smart_respond(ctx, embed=embed)
            await self.log_command_usage(ctx, "skip", True)

        except Exception as e:
            self.logger.error(f"Error in skip command: {e}")
            await self.log_command_usage(ctx, "skip", False, str(e))

    @command(
        name="queue",
        description="Show the current queue",
        aliases=["q"],
    )
    async def queue(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            async with self.bot.db.session() as session:
                result = await session.execute(
                    select(MusicQueue)
                    .where(MusicQueue.guild_id == ctx.guild_id)
                    .order_by(MusicQueue.position)
                    .limit(10)
                )
                queue_items = result.scalars().all()

                if not queue_items:
                    embed = self.create_embed(
                        title="📋 Queue Empty",
                        description="The queue is empty.",
                        color=hikari.Color(0xFFAA00),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                # Get current session
                result = await session.execute(
                    select(MusicSession).where(MusicSession.guild_id == ctx.guild_id)
                )
                music_session = result.scalar_one_or_none()
                current_pos = music_session.current_track_position if music_session else -1

                embed = self.create_embed(title="🎵 Current Queue", color=hikari.Color(0x0099FF))

                queue_text = ""
                for i, item in enumerate(queue_items):
                    status = "🎵 " if item.position == current_pos else f"{i + 1}. "
                    queue_text += f"{status}[{item.track_title}]({item.track_uri}) - {item.track_author}\n"

                embed.description = queue_text[:2048]  # Discord embed limit

                if len(queue_items) == 10:
                    embed.set_footer(text="Showing first 10 tracks...")

                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "queue", True)

        except Exception as e:
            self.logger.error(f"Error in queue command: {e}")
            await self.log_command_usage(ctx, "queue", False, str(e))

    @command(
        name="volume",
        description="Set the volume (0-100)",
        permission_node="music.manage",
        arguments=[
            CommandArgument("level", hikari.OptionType.INTEGER, "Volume level (0-100)")
        ],
    )
    async def volume(self, ctx: lightbulb.Context, level: int) -> None:
        if not ctx.guild_id:
            return

        try:
            if not 0 <= level <= 100:
                embed = self.create_embed(
                    title="❌ Invalid Volume",
                    description="Volume must be between 0 and 100.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            player = self.lavalink_client.player_manager.get(ctx.guild_id)
            if not player or not player.is_connected:
                embed = self.create_embed(
                    title="❌ Not Connected",
                    description="I'm not connected to a voice channel.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await player.set_volume(level)

            async with self.bot.db.session() as session:
                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == ctx.guild_id)
                    .values(volume=level, last_activity=datetime.now(timezone.utc))
                )
                await session.commit()

            embed = self.create_embed(
                title="🔊 Volume Updated",
                description=f"Volume set to {level}%.",
                color=hikari.Color(0x00FF00),
            )
            await self.smart_respond(ctx, embed=embed)
            await self.log_command_usage(ctx, "volume", True)

        except Exception as e:
            self.logger.error(f"Error in volume command: {e}")
            await self.log_command_usage(ctx, "volume", False, str(e))

    @command(
        name="shuffle",
        description="Toggle shuffle mode",
        permission_node="music.manage",
    )
    async def shuffle(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            async with self.bot.db.session() as session:
                result = await session.execute(
                    select(MusicSession).where(MusicSession.guild_id == ctx.guild_id)
                )
                music_session = result.scalar_one_or_none()

                if not music_session:
                    embed = self.create_embed(
                        title="❌ No Session",
                        description="No active music session.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                new_shuffle_state = not music_session.shuffle_enabled

                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == ctx.guild_id)
                    .values(shuffle_enabled=new_shuffle_state, last_activity=datetime.now(timezone.utc))
                )
                await session.commit()

                status = "enabled" if new_shuffle_state else "disabled"
                emoji = "🔀" if new_shuffle_state else "🔁"
                embed = self.create_embed(
                    title=f"{emoji} Shuffle {status.title()}",
                    description=f"Shuffle has been {status}.",
                    color=hikari.Color(0x0099FF),
                )
                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "shuffle", True)

        except Exception as e:
            self.logger.error(f"Error in shuffle command: {e}")
            await self.log_command_usage(ctx, "shuffle", False, str(e))

    @command(
        name="repeat",
        description="Set repeat mode (off/track/queue)",
        permission_node="music.manage",
        arguments=[
            CommandArgument(
                "mode",
                hikari.OptionType.STRING,
                "Repeat mode: off, track, or queue",
                choices=["off", "track", "queue"]
            )
        ],
    )
    async def repeat(self, ctx: lightbulb.Context, mode: str) -> None:
        if not ctx.guild_id:
            return

        try:
            if mode.lower() not in ["off", "track", "queue"]:
                embed = self.create_embed(
                    title="❌ Invalid Mode",
                    description="Repeat mode must be `off`, `track`, or `queue`.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            async with self.bot.db.session() as session:
                result = await session.execute(
                    select(MusicSession).where(MusicSession.guild_id == ctx.guild_id)
                )
                music_session = result.scalar_one_or_none()

                if not music_session:
                    embed = self.create_embed(
                        title="❌ No Session",
                        description="No active music session.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == ctx.guild_id)
                    .values(repeat_mode=mode.lower(), last_activity=datetime.now(timezone.utc))
                )
                await session.commit()

                emoji_map = {"off": "⏹️", "track": "🔂", "queue": "🔁"}
                embed = self.create_embed(
                    title=f"{emoji_map[mode.lower()]} Repeat Mode Updated",
                    description=f"Repeat mode set to {mode.lower()}.",
                    color=hikari.Color(0x0099FF),
                )
                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "repeat", True)

        except Exception as e:
            self.logger.error(f"Error in repeat command: {e}")
            await self.log_command_usage(ctx, "repeat", False, str(e))

    @command(
        name="disconnect",
        description="Disconnect from voice channel",
        permission_node="music.manage",
        aliases=["dc"],
    )
    async def disconnect(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            player = self.lavalink_client.player_manager.get(ctx.guild_id)
            if not player or not player.is_connected:
                embed = self.create_embed(
                    title="❌ Not Connected",
                    description="I'm not connected to a voice channel.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            await player.disconnect()

            # Clean up database
            async with self.bot.db.session() as session:
                await session.execute(
                    delete(MusicSession).where(MusicSession.guild_id == ctx.guild_id)
                )
                await session.execute(
                    delete(MusicQueue).where(MusicQueue.guild_id == ctx.guild_id)
                )
                await session.commit()

            embed = self.create_embed(
                title="👋 Disconnected",
                description="Disconnected from voice channel.",
                color=hikari.Color(0x0099FF),
            )
            await self.smart_respond(ctx, embed=embed)
            await self.log_command_usage(ctx, "disconnect", True)

        except Exception as e:
            self.logger.error(f"Error in disconnect command: {e}")
            await self.log_command_usage(ctx, "disconnect", False, str(e))

    @command(
        name="nowplaying",
        description="Show the currently playing track",
        aliases=["np"],
    )
    async def nowplaying(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            async with self.bot.db.session() as session:
                result = await session.execute(
                    select(MusicSession).where(MusicSession.guild_id == ctx.guild_id)
                )
                music_session = result.scalar_one_or_none()

                if not music_session or not music_session.is_playing:
                    embed = self.create_embed(
                        title="❌ Nothing Playing",
                        description="Nothing is currently playing.",
                        color=hikari.Color(0xFFAA00),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                # Get current track
                result = await session.execute(
                    select(MusicQueue).where(
                        MusicQueue.guild_id == ctx.guild_id,
                        MusicQueue.position == music_session.current_track_position
                    )
                )
                current_track = result.scalar_one_or_none()

                if not current_track:
                    embed = self.create_embed(
                        title="❌ Track Not Found",
                        description="Current track information not found.",
                        color=hikari.Color(0xFF0000),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                player = self.lavalink_client.player_manager.get(ctx.guild_id)
                position = player.position if player else 0

                position_str = self._format_time(position)
                duration_str = self._format_time(current_track.track_duration)

                embed = self.create_embed(
                    title="🎵 Now Playing",
                    description=f"[{current_track.track_title}]({current_track.track_uri})\nBy: {current_track.track_author}",
                    color=hikari.Color(0x00FF00)
                )
                embed.add_field("Progress", f"{position_str} / {duration_str}", inline=True)
                embed.add_field("Volume", f"{music_session.volume}%", inline=True)
                embed.add_field("Repeat", music_session.repeat_mode.title(), inline=True)

                status_parts = []
                if music_session.is_paused:
                    status_parts.append("⏸️ Paused")
                if music_session.shuffle_enabled:
                    status_parts.append("🔀 Shuffle")

                if status_parts:
                    embed.add_field("Status", " | ".join(status_parts), inline=False)

                requester = self.bot.hikari_bot.cache.get_user(current_track.requester_id)
                if requester:
                    embed.set_footer(text=f"Requested by {requester.username}")

                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "nowplaying", True)

        except Exception as e:
            self.logger.error(f"Error in nowplaying command: {e}")
            await self.log_command_usage(ctx, "nowplaying", False, str(e))

    @command(
        name="clear",
        description="Clear the queue",
        permission_node="music.manage",
    )
    async def clear(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            return

        try:
            async with self.bot.db.session() as session:
                result = await session.execute(
                    select(func.count(MusicQueue.id)).where(MusicQueue.guild_id == ctx.guild_id)
                )
                count = result.scalar()

                if count == 0:
                    embed = self.create_embed(
                        title="📋 Queue Empty",
                        description="The queue is already empty.",
                        color=hikari.Color(0xFFAA00),
                    )
                    await self.smart_respond(ctx, embed=embed, ephemeral=True)
                    return

                await session.execute(
                    delete(MusicQueue).where(MusicQueue.guild_id == ctx.guild_id)
                )
                await session.execute(
                    update(MusicSession)
                    .where(MusicSession.guild_id == ctx.guild_id)
                    .values(current_track_position=0, last_activity=datetime.now(timezone.utc))
                )
                await session.commit()

                embed = self.create_embed(
                    title="🗑️ Queue Cleared",
                    description=f"Cleared {count} track(s) from the queue.",
                    color=hikari.Color(0x00FF00),
                )
                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "clear", True)

        except Exception as e:
            self.logger.error(f"Error in clear command: {e}")
            await self.log_command_usage(ctx, "clear", False, str(e))

    @command(
        name="music-settings",
        description="Configure music plugin settings",
        permission_node="music.settings",
        arguments=[
            CommandArgument(
                "setting",
                hikari.OptionType.STRING,
                "Setting to configure",
                choices=["auto_disconnect", "follow_user"],
                required=False
            ),
            CommandArgument(
                "value",
                hikari.OptionType.STRING,
                "Value to set (true/false)",
                choices=["true", "false", "enable", "disable", "on", "off"],
                required=False
            ),
        ],
    )
    async def music_settings(self, ctx: lightbulb.Context, setting: str = None, value: str = None) -> None:
        if not ctx.guild_id:
            return

        try:
            if not setting:
                # Show current settings
                auto_disconnect = await self.get_setting(ctx.guild_id, "auto_disconnect", True)
                follow_user = await self.get_setting(ctx.guild_id, "follow_user", False)

                embed = self.create_embed(
                    title="🎵 Music Settings",
                    description="Current server music settings:",
                    color=hikari.Color(0x0099FF)
                )
                embed.add_field("Auto Disconnect", "Enabled" if auto_disconnect else "Disabled", inline=True)
                embed.add_field("Follow User", "Enabled" if follow_user else "Disabled", inline=True)
                embed.add_field("Inactivity Timeout", f"{self.inactivity_timeout}s", inline=True)

                embed.set_footer(text="Use `/music-settings <setting> <value>` to change settings")
                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "music-settings", True)
                return

            if setting.lower() not in ["auto_disconnect", "follow_user"]:
                embed = self.create_embed(
                    title="❌ Invalid Setting",
                    description="Available settings: `auto_disconnect`, `follow_user`",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if value is None:
                embed = self.create_embed(
                    title="❌ Missing Value",
                    description="Please provide a value (true/false).",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            if value.lower() not in ["true", "false", "enable", "disable", "on", "off"]:
                embed = self.create_embed(
                    title="❌ Invalid Value",
                    description="Value must be true/false, enable/disable, or on/off.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            bool_value = value.lower() in ["true", "enable", "on"]

            success = await self.set_setting(ctx.guild_id, setting.lower(), bool_value)
            if success:
                status = "enabled" if bool_value else "disabled"
                embed = self.create_embed(
                    title="✅ Setting Updated",
                    description=f"{setting.replace('_', ' ').title()} {status}.",
                    color=hikari.Color(0x00FF00),
                )
                await self.smart_respond(ctx, embed=embed)
                await self.log_command_usage(ctx, "music-settings", True)
            else:
                embed = self.create_embed(
                    title="❌ Update Failed",
                    description="Failed to update setting.",
                    color=hikari.Color(0xFF0000),
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                await self.log_command_usage(ctx, "music-settings", False, "Failed to update setting")

        except Exception as e:
            self.logger.error(f"Error in music-settings command: {e}")
            await self.log_command_usage(ctx, "music-settings", False, str(e))


def load(bot) -> None:
    bot.add_plugin(MusicPlugin(bot))


def unload(bot) -> None:
    bot.remove_plugin("MusicPlugin")