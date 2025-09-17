import asyncio
import hikari
import lightbulb
import lavalink
import logging
import random
import miru
from typing import Any

from bot.plugins.base import BasePlugin
from bot.plugins.commands import CommandArgument, command
from config.settings import settings

logger = logging.getLogger(__name__)


class MusicControlView(miru.View):
    def __init__(self, music_plugin, guild_id: int, *, timeout: float = 300) -> None:
        super().__init__(timeout=timeout)
        self.music_plugin = music_plugin
        self.guild_id = guild_id

    @miru.button(emoji="⏯️", style=hikari.ButtonStyle.SECONDARY)
    async def pause_resume_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player or not player.current:
            await ctx.respond("Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if player.paused:
            await player.set_pause(False)
            await ctx.respond("▶️ Resumed", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await player.set_pause(True)
            await ctx.respond("⏸️ Paused", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="⏭️", style=hikari.ButtonStyle.SECONDARY)
    async def skip_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player or not player.is_playing:
            await ctx.respond("Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.skip()
        await ctx.respond("⏭️ Skipped", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="⏹️", style=hikari.ButtonStyle.DANGER)
    async def stop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player:
            await ctx.respond("No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player.queue.clear()
        await player.stop()
        await self.music_plugin.bot.hikari_bot.update_voice_state(self.guild_id, None)
        await ctx.respond("⏹️ Stopped and disconnected", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="🔀", style=hikari.ButtonStyle.SECONDARY)
    async def shuffle_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        player = self.music_plugin.lavalink_client.player_manager.get(self.guild_id)

        if not player or len(player.queue) < 2:
            await ctx.respond("Need at least 2 tracks in queue to shuffle.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Shuffle the queue
        queue_list = list(player.queue)
        random.shuffle(queue_list)
        player.queue.clear()
        for track in queue_list:
            player.queue.append(track)

        await ctx.respond(f"🔀 Shuffled {len(queue_list)} tracks", flags=hikari.MessageFlag.EPHEMERAL)

    @miru.button(emoji="🔁", style=hikari.ButtonStyle.SECONDARY)
    async def loop_button(self, ctx: miru.ViewContext, button: miru.Button) -> None:
        current_mode = self.music_plugin.repeat_modes.get(self.guild_id, 0)
        new_mode = (current_mode + 1) % 3
        self.music_plugin.repeat_modes[self.guild_id] = new_mode

        if new_mode == 0:
            await ctx.respond("🔁 Loop disabled", flags=hikari.MessageFlag.EPHEMERAL)
        elif new_mode == 1:
            await ctx.respond("🔂 Track repeat enabled", flags=hikari.MessageFlag.EPHEMERAL)
        else:
            await ctx.respond("🔁 Queue repeat enabled", flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        # Disable all buttons when view times out
        for item in self.children:
            item.disabled = True

        if hasattr(self, 'message') and self.message:
            try:
                await self.message.edit(components=self)
            except:
                pass


class SearchResultView(miru.View):
    def __init__(self, music_plugin, guild_id: int, tracks: list, user_id: int, *, timeout: float = 60) -> None:
        super().__init__(timeout=timeout)
        self.music_plugin = music_plugin
        self.guild_id = guild_id
        self.tracks = tracks
        self.user_id = user_id
        self._setup_select_menu()

    def _setup_select_menu(self) -> None:
        """Setup the track selection dropdown menu."""
        if not self.tracks:
            return

        options = []
        for i, track in enumerate(self.tracks[:5]):  # Limit to 5 options
            # Format duration
            duration_minutes = track.duration // 60000
            duration_seconds = (track.duration % 60000) // 1000
            duration_str = f"{duration_minutes}:{duration_seconds:02d}"

            # Truncate title if too long
            title = track.title[:80] + "..." if len(track.title) > 80 else track.title
            description = f"By: {track.author} | Duration: {duration_str}"

            options.append(
                miru.SelectOption(
                    label=f"{i + 1}. {title}",
                    value=str(i),
                    description=description[:100],  # Discord limit
                    emoji="🎵"
                )
            )

        if options:
            select = miru.TextSelect(
                placeholder="Choose a track to play...",
                options=options,
                custom_id="track_select",
            )
            select.callback = self.on_track_select
            self.add_item(select)

    async def on_track_select(self, ctx: miru.ViewContext) -> None:
        """Handle track selection from dropdown."""
        # Check if the user who clicked is the same as who initiated the search
        if ctx.user.id != self.user_id:
            await ctx.respond("Only the person who started the search can select a track.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Get the select component that triggered this callback
        select = None
        for item in self.children:
            if isinstance(item, miru.TextSelect) and item.custom_id == "track_select":
                select = item
                break

        if not select or not select.values:
            return

        try:
            selected_index = int(select.values[0])
            if selected_index < 0 or selected_index >= len(self.tracks):
                await ctx.respond("Invalid selection.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            selected_track = self.tracks[selected_index]

            # Check if user is still in voice channel
            voice_state = self.music_plugin.bot.hikari_bot.cache.get_voice_state(self.guild_id, self.user_id)
            if not voice_state or not voice_state.channel_id:
                await ctx.respond("You must be in a voice channel to play music.", flags=hikari.MessageFlag.EPHEMERAL)
                return

            # Get or create player
            player = self.music_plugin.lavalink_client.player_manager.create(self.guild_id)

            # Connect to voice channel if not connected
            if not player.is_connected:
                await self.music_plugin.bot.hikari_bot.update_voice_state(self.guild_id, voice_state.channel_id)

            # Add to queue and play if nothing is playing
            player.add(requester=self.user_id, track=selected_track)

            was_playing = player.is_playing
            if not was_playing:
                await player.play()

            # Format duration
            duration_minutes = selected_track.duration // 60000
            duration_seconds = (selected_track.duration % 60000) // 1000

            # Create response embed
            if was_playing:
                queue_position = len(player.queue)
                embed = self.music_plugin.create_embed(
                    title="🎵 Added to Queue",
                    color=hikari.Color(0x00FF00)
                )

                embed.add_field(
                    name="🎶 Track",
                    value=f"**[{selected_track.title}]({selected_track.uri})**\nBy: {selected_track.author}",
                    inline=False
                )

                embed.add_field(
                    name="📍 Position",
                    value=f"#{queue_position} in queue",
                    inline=True
                )

                embed.add_field(
                    name="⏱️ Duration",
                    value=f"`{duration_minutes}:{duration_seconds:02d}`",
                    inline=True
                )
            else:
                embed = self.music_plugin.create_embed(
                    title="🎵 Now Playing",
                    color=hikari.Color(0x00FF00)
                )

                embed.add_field(
                    name="🎶 Track",
                    value=f"**[{selected_track.title}]({selected_track.uri})**\nBy: {selected_track.author}",
                    inline=False
                )

                embed.add_field(
                    name="⏱️ Duration",
                    value=f"`{duration_minutes}:{duration_seconds:02d}`",
                    inline=True
                )

            # Disable the view after selection
            for item in self.children:
                item.disabled = True

            await ctx.edit_response(embed=embed, components=self)

        except Exception as e:
            await ctx.respond(f"Error adding track: {str(e)}", flags=hikari.MessageFlag.EPHEMERAL)

    async def on_timeout(self) -> None:
        # Disable all items when view times out
        for item in self.children:
            item.disabled = True

        if hasattr(self, 'message') and self.message:
            try:
                timeout_embed = self.music_plugin.create_embed(
                    title="⏰ Search Timeout",
                    description="Track selection timed out. Please use `/search` again.",
                    color=hikari.Color(0xFF9800)
                )
                await self.message.edit(embed=timeout_embed, components=self)
            except:
                pass


class MusicEventHandler:
    def __init__(self, music_plugin):
        self.music_plugin = music_plugin

    @lavalink.listener(lavalink.TrackStartEvent)
    async def track_start(self, event: lavalink.TrackStartEvent):
        logger.info(f'Track started on guild: {event.player.guild_id}')

    @lavalink.listener(lavalink.TrackEndEvent)
    async def track_end(self, event: lavalink.TrackEndEvent):
        logger.info(f'Track finished on guild: {event.player.guild_id}')

        # Handle repeat modes
        guild_id = event.player.guild_id
        repeat_mode = self.music_plugin.repeat_modes.get(guild_id, 0)

        if repeat_mode == 1:  # Track repeat
            # Re-add the same track to the front of the queue
            if event.track:
                event.player.add(track=event.track, index=0)
        elif repeat_mode == 2 and event.track:  # Queue repeat
            # Add the finished track to the end of the queue
            event.player.add(track=event.track)

    @lavalink.listener(lavalink.TrackExceptionEvent)
    async def track_exception(self, event: lavalink.TrackExceptionEvent):
        logger.warning(f'Track exception event happened on guild: {event.player.guild_id}')

    @lavalink.listener(lavalink.QueueEndEvent)
    async def queue_finish(self, event: lavalink.QueueEndEvent):
        logger.info(f'Queue finished on guild: {event.player.guild_id}')


class MusicPlugin(BasePlugin):
    def __init__(self, bot: Any) -> None:
        super().__init__(bot)
        self.lavalink_client: lavalink.Client | None = None
        # Track repeat modes per guild: 0 = off, 1 = track, 2 = queue
        self.repeat_modes: dict[int, int] = {}
        # Track auto-disconnect timers per guild
        self.disconnect_timers: dict[int, Any] = {}
        # Track if we're currently restoring queues (to avoid recursion)
        self._restoring_queues: set[int] = set()

    async def on_load(self) -> None:
        await super().on_load()

        # Initialize Lavalink client
        self.lavalink_client = lavalink.Client(self.bot.hikari_bot.get_me().id)
        self.lavalink_client.add_node(
            host=settings.lavalink_host,
            port=settings.lavalink_port,
            password=settings.lavalink_password,
            region='us',
            name='default-node'
        )

        # Add event handlers
        self.lavalink_client.add_event_hooks(MusicEventHandler(self))

        # Setup voice update handlers
        @self.bot.hikari_bot.listen(hikari.VoiceServerUpdateEvent)
        async def voice_server_update(event: hikari.VoiceServerUpdateEvent) -> None:
            lavalink_data = {
                't': 'VOICE_SERVER_UPDATE',
                'd': {
                    'guild_id': event.guild_id,
                    'endpoint': event.endpoint[6:],  # Remove 'wss://' prefix
                    'token': event.token,
                }
            }
            await self.lavalink_client.voice_update_handler(lavalink_data)

        @self.bot.hikari_bot.listen(hikari.VoiceStateUpdateEvent)
        async def voice_state_update(event: hikari.VoiceStateUpdateEvent) -> None:
            lavalink_data = {
                't': 'VOICE_STATE_UPDATE',
                'd': {
                    'guild_id': event.state.guild_id,
                    'user_id': event.state.user_id,
                    'channel_id': event.state.channel_id,
                    'session_id': event.state.session_id,
                }
            }
            await self.lavalink_client.voice_update_handler(lavalink_data)

            # Check for auto-disconnect when users leave/join voice channels
            if event.state.guild_id and not event.state.member.is_bot:
                player = self.lavalink_client.player_manager.get(event.state.guild_id)
                if player and player.is_connected and player.channel_id:
                    # Check if this affects the bot's voice channel
                    if (event.old_state and event.old_state.channel_id == player.channel_id) or \
                       (event.state.channel_id == player.channel_id):
                        await self._check_voice_channel_empty(event.state.guild_id, player.channel_id)

        logger.info("Music plugin loaded with Lavalink.py")

    async def on_unload(self) -> None:
        # Cancel all disconnect timers
        for task in self.disconnect_timers.values():
            if not task.done():
                task.cancel()
        self.disconnect_timers.clear()

        if self.lavalink_client:
            await self.lavalink_client.destroy()
        await super().on_unload()

    @command(
        name="play",
        description="Play a song",
        permission_node="music.play",
        arguments=[
            CommandArgument("query", hikari.OptionType.STRING, "Song name or URL to play")
        ],
    )
    async def play(self, ctx: lightbulb.Context, query: str) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Check if user is in voice channel
        voice_state = ctx.bot.hikari_bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
        if not voice_state or not voice_state.channel_id:
            await self.smart_respond(ctx, "You must be in a voice channel to use this command.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Get or create player
        player = self.lavalink_client.player_manager.create(ctx.guild_id)

        # Connect to voice channel if not connected
        if not player.is_connected:
            await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, voice_state.channel_id)

        # Search for tracks - handle direct URLs vs search queries
        if query.startswith(("http://", "https://")):
            # Direct URL - could be a playlist
            search_result = await self.lavalink_client.get_tracks(query)

            if not search_result.tracks:
                await self.smart_respond(ctx, f"No tracks found for: `{query}`", flags=hikari.MessageFlag.EPHEMERAL)
                return

            # If it's a playlist (multiple tracks), handle differently
            if len(search_result.tracks) > 1:
                await self._handle_playlist_add(ctx, search_result, player, voice_state.channel_id)
                return

            track = search_result.tracks[0]
        else:
            # Search query - only get first result
            search_result = await self.lavalink_client.get_tracks(f"ytsearch:{query}")

            if not search_result.tracks:
                await self.smart_respond(ctx, f"No tracks found for: `{query}`", flags=hikari.MessageFlag.EPHEMERAL)
                return

            track = search_result.tracks[0]

        # Add to queue and play if nothing is playing
        player.add(requester=ctx.author.id, track=track)

        was_playing = player.is_playing
        if not was_playing:
            await player.play()

        # Format duration
        duration_minutes = track.duration // 60000
        duration_seconds = (track.duration % 60000) // 1000

        # Create rich embed
        if was_playing:
            # Track was added to queue
            queue_position = len(player.queue)

            embed = self.create_embed(
                title="🎵 Added to Queue",
                color=hikari.Color(0x00FF00)
            )

            # Track information
            embed.add_field(
                name="🎶 Track",
                value=f"**[{track.title}]({track.uri})**\nBy: {track.author}",
                inline=False
            )

            # Queue information
            embed.add_field(
                name="📍 Position",
                value=f"#{queue_position} in queue",
                inline=True
            )

            embed.add_field(
                name="⏱️ Duration",
                value=f"`{duration_minutes}:{duration_seconds:02d}`",
                inline=True
            )

            embed.add_field(
                name="👤 Requested by",
                value=ctx.author.mention,
                inline=True
            )

            # Calculate estimated time until this track plays
            if queue_position > 1:
                # Get remaining time of current track
                current_remaining = player.current.duration - player.position if player.current else 0
                # Add duration of all tracks before this one in queue
                queue_before_duration = sum(t.duration for t in list(player.queue)[:-1])
                total_wait_time = current_remaining + queue_before_duration

                wait_minutes = total_wait_time // 60000
                wait_hours = wait_minutes // 60
                remaining_wait_minutes = wait_minutes % 60

                if wait_hours > 0:
                    wait_time_str = f"`{wait_hours}h {remaining_wait_minutes}m`"
                else:
                    wait_time_str = f"`{wait_minutes}m`"

                embed.add_field(
                    name="⏰ Estimated Wait",
                    value=wait_time_str,
                    inline=True
                )
        else:
            # Track started playing immediately
            embed = self.create_embed(
                title="🎵 Now Playing",
                color=hikari.Color(0x00FF00)
            )

            # Track information
            embed.add_field(
                name="🎶 Track",
                value=f"**[{track.title}]({track.uri})**\nBy: {track.author}",
                inline=False
            )

            embed.add_field(
                name="⏱️ Duration",
                value=f"`{duration_minutes}:{duration_seconds:02d}`",
                inline=True
            )

            embed.add_field(
                name="👤 Requested by",
                value=ctx.author.mention,
                inline=True
            )

            # Show volume and repeat status
            status_parts = []
            status_parts.append(f"🔊 Volume: {player.volume}%")

            repeat_mode = self.repeat_modes.get(ctx.guild_id, 0)
            if repeat_mode == 1:
                status_parts.append("🔂 Repeat: Track")
            elif repeat_mode == 2:
                status_parts.append("🔁 Repeat: Queue")

            embed.add_field(
                name="ℹ️ Status",
                value="\n".join(status_parts),
                inline=True
            )

        # Set thumbnail if available
        if hasattr(track, 'artwork_url') and track.artwork_url:
            embed.set_thumbnail(track.artwork_url)

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="pause",
        description="Pause the current track",
        permission_node="music.play",
    )
    async def pause(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.is_playing:
            await self.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if player.paused:
            await self.smart_respond(ctx, "The track is already paused.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.set_pause(True)
        embed = self.create_embed(
            title="⏸️ Paused",
            description=f"Paused: **{player.current.title}**",
            color=hikari.Color(0xFFFF00)
        )
        await self.smart_respond(ctx, embed=embed)

    @command(
        name="resume",
        description="Resume the current track",
        permission_node="music.play",
    )
    async def resume(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await self.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if not player.paused:
            await self.smart_respond(ctx, "The track is not paused.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.set_pause(False)
        embed = self.create_embed(
            title="▶️ Resumed",
            description=f"Resumed: **{player.current.title}**",
            color=hikari.Color(0x00FF00)
        )
        await self.smart_respond(ctx, embed=embed)

    @command(
        name="volume",
        description="Set or check the volume (0-100)",
        permission_node="music.play",
        arguments=[
            CommandArgument("level", hikari.OptionType.INTEGER, "Volume level (0-100)", required=False)
        ],
    )
    async def volume(self, ctx: lightbulb.Context, level: int = None) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await self.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # If no level provided, show current volume
        if level is None:
            embed = self.create_embed(
                title="🔊 Volume",
                description=f"Current volume: **{player.volume}%**",
                color=hikari.Color(0x0099FF)
            )
            await self.smart_respond(ctx, embed=embed)
            return

        # Validate volume level
        if level < 0 or level > 100:
            await self.smart_respond(ctx, "Volume must be between 0 and 100.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.set_volume(level)

        # Choose appropriate emoji based on volume level
        if level == 0:
            emoji = "🔇"
        elif level <= 30:
            emoji = "🔉"
        elif level <= 70:
            emoji = "🔊"
        else:
            emoji = "📢"

        embed = self.create_embed(
            title=f"{emoji} Volume Set",
            description=f"Volume set to **{level}%**",
            color=hikari.Color(0x00FF00)
        )
        await self.smart_respond(ctx, embed=embed)

    @command(
        name="seek",
        description="Seek to a specific position in the track (format: mm:ss or seconds)",
        permission_node="music.play",
        arguments=[
            CommandArgument("position", hikari.OptionType.STRING, "Position to seek to (mm:ss or seconds)")
        ],
    )
    async def seek(self, ctx: lightbulb.Context, position: str) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await self.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Parse position
        try:
            if ":" in position:
                # Format: mm:ss
                parts = position.split(":")
                if len(parts) != 2:
                    raise ValueError("Invalid format")
                minutes, seconds = int(parts[0]), int(parts[1])
                seek_position = (minutes * 60 + seconds) * 1000
            else:
                # Format: seconds
                seek_position = int(position) * 1000
        except ValueError:
            await self.smart_respond(ctx, "Invalid position format. Use mm:ss or seconds.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Validate position
        if seek_position < 0 or seek_position > player.current.duration:
            await self.smart_respond(ctx, "Position is out of track bounds.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.seek(seek_position)

        # Format position for display
        seek_minutes = seek_position // 60000
        seek_seconds = (seek_position % 60000) // 1000

        embed = self.create_embed(
            title="🎯 Seeked",
            description=f"Seeked to **{seek_minutes}:{seek_seconds:02d}** in **{player.current.title}**",
            color=hikari.Color(0x00FF00)
        )
        await self.smart_respond(ctx, embed=embed)

    @command(
        name="position",
        description="Show current position in the track",
        permission_node="music.play",
    )
    async def position(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await self.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Format current position and duration
        current_pos = player.position
        duration = player.current.duration

        current_minutes = current_pos // 60000
        current_seconds = (current_pos % 60000) // 1000
        duration_minutes = duration // 60000
        duration_seconds = (duration % 60000) // 1000

        # Create progress bar
        progress_percentage = current_pos / duration if duration > 0 else 0
        bar_length = 20
        filled_length = int(bar_length * progress_percentage)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        embed = self.create_embed(
            title="📍 Track Position",
            description=f"**{player.current.title}**\n"
                       f"`{current_minutes}:{current_seconds:02d}` {bar} `{duration_minutes}:{duration_seconds:02d}`\n"
                       f"Progress: {progress_percentage:.1%}",
            color=hikari.Color(0x0099FF)
        )
        await self.smart_respond(ctx, embed=embed)

    @command(
        name="nowplaying",
        description="Show the currently playing track with detailed information",
        aliases=["np", "current"],
        permission_node="music.play",
    )
    async def now_playing(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await self.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        track = player.current
        current_pos = player.position
        duration = track.duration

        # Format time
        current_minutes = current_pos // 60000
        current_seconds = (current_pos % 60000) // 1000
        duration_minutes = duration // 60000
        duration_seconds = (duration % 60000) // 1000

        # Create progress bar
        progress_percentage = current_pos / duration if duration > 0 else 0
        bar_length = 25
        filled_length = int(bar_length * progress_percentage)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        # Get requester info
        requester = track.requester
        try:
            user = await ctx.bot.rest.fetch_user(requester)
            requester_mention = user.mention
        except:
            requester_mention = f"<@{requester}>"

        # Status emoji
        status_emoji = "⏸️" if player.paused else "▶️"

        embed = self.create_embed(
            title=f"{status_emoji} Now Playing",
            color=hikari.Color(0x00FF00) if not player.paused else hikari.Color(0xFFFF00)
        )

        # Main track info
        embed.add_field(
            name="🎵 Track",
            value=f"**[{track.title}]({track.uri})**\nBy: {track.author}",
            inline=False
        )

        # Progress information
        embed.add_field(
            name="⏱️ Progress",
            value=f"`{current_minutes}:{current_seconds:02d}` {bar} `{duration_minutes}:{duration_seconds:02d}`\n"
                  f"{progress_percentage:.1%} complete",
            inline=False
        )

        # Player status
        status_info = []
        status_info.append(f"🔊 Volume: {player.volume}%")

        repeat_mode = self.repeat_modes.get(ctx.guild_id, 0)
        if repeat_mode == 1:
            status_info.append("🔂 Repeat: Track")
        elif repeat_mode == 2:
            status_info.append("🔁 Repeat: Queue")

        if len(player.queue) > 0:
            status_info.append(f"📋 Queue: {len(player.queue)} tracks")

        embed.add_field(
            name="ℹ️ Status",
            value="\n".join(status_info),
            inline=True
        )

        # Requester info
        embed.add_field(
            name="👤 Requested by",
            value=requester_mention,
            inline=True
        )

        # Set thumbnail if available
        if hasattr(track, 'artwork_url') and track.artwork_url:
            embed.set_thumbnail(track.artwork_url)

        # Add interactive controls
        view = MusicControlView(self, ctx.guild_id)

        # Check if miru client is available
        miru_client = getattr(self.bot, "miru_client", None)
        if miru_client and view.children:
            message = await ctx.respond(embed=embed, components=view)
            miru_client.start_view(view)

            # Store message reference for timeout handling
            if hasattr(message, 'message'):
                view.message = message.message
            elif hasattr(message, 'id'):
                view.message = message
        else:
            # Fallback without interactive controls
            await ctx.respond(embed=embed)

    @command(
        name="shuffle",
        description="Shuffle the current queue",
        permission_node="music.play",
    )
    async def shuffle(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await self.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if len(player.queue) < 2:
            await self.smart_respond(ctx, "Need at least 2 tracks in the queue to shuffle.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Shuffle the queue
        queue_list = list(player.queue)
        random.shuffle(queue_list)

        # Clear and repopulate the queue
        player.queue.clear()
        for track in queue_list:
            player.queue.append(track)

        embed = self.create_embed(
            title="🔀 Queue Shuffled",
            description=f"Shuffled **{len(queue_list)}** tracks in the queue",
            color=hikari.Color(0x00FF00)
        )
        await self.smart_respond(ctx, embed=embed)

    @command(
        name="loop",
        description="Toggle loop modes: off -> track -> queue -> off",
        aliases=["repeat"],
        permission_node="music.play",
        arguments=[
            CommandArgument("mode", hikari.OptionType.STRING, "Loop mode: off, track, or queue", required=False)
        ],
    )
    async def loop(self, ctx: lightbulb.Context, mode: str = None) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        current_mode = self.repeat_modes.get(ctx.guild_id, 0)

        if mode is None:
            # Cycle through modes: 0 -> 1 -> 2 -> 0
            new_mode = (current_mode + 1) % 3
        else:
            # Set specific mode
            mode = mode.lower()
            if mode in ["off", "none", "0"]:
                new_mode = 0
            elif mode in ["track", "song", "1"]:
                new_mode = 1
            elif mode in ["queue", "all", "2"]:
                new_mode = 2
            else:
                await self.smart_respond(ctx, "Invalid mode. Use: `off`, `track`, or `queue`", flags=hikari.MessageFlag.EPHEMERAL)
                return

        self.repeat_modes[ctx.guild_id] = new_mode

        # Create embed with appropriate styling
        if new_mode == 0:
            embed = self.create_embed(
                title="🔁 Loop Off",
                description="Loop mode disabled",
                color=hikari.Color(0xFF0000)
            )
        elif new_mode == 1:
            embed = self.create_embed(
                title="🔂 Loop Track",
                description="Current track will repeat",
                color=hikari.Color(0x00FF00)
            )
        else:  # new_mode == 2
            embed = self.create_embed(
                title="🔁 Loop Queue",
                description="Queue will repeat when finished",
                color=hikari.Color(0x0099FF)
            )

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="stop",
        description="Stop the music and clear the queue",
        permission_node="music.play",
    )
    async def stop(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await self.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player.queue.clear()
        await player.stop()
        await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, None)

        await self.smart_respond(ctx, "⏹️ Stopped the music and cleared the queue.")

    @command(
        name="skip",
        description="Skip the current track",
        permission_node="music.play",
    )
    async def skip(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.is_playing:
            await self.smart_respond(ctx, "Nothing is currently playing.", ephemeral=True)
            return

        # Get current track info before skipping
        current_track = player.current
        current_title = current_track.title if current_track else "Unknown Track"

        # Get next track info
        next_track = None
        if len(player.queue) > 0:
            next_track = player.queue[0]

        # Skip the track
        await player.skip()

        # Create rich embed response
        embed = self.create_embed(
            title="⏭️ Track Skipped",
            color=hikari.Color(0x00FF00)
        )

        embed.add_field(
            name="🎵 Skipped",
            value=f"**{current_title}**",
            inline=False
        )

        if next_track:
            # Format next track duration
            next_duration_minutes = next_track.duration // 60000
            next_duration_seconds = (next_track.duration % 60000) // 1000

            # Get requester info for next track
            try:
                next_user = await ctx.bot.rest.fetch_user(next_track.requester)
                next_requester = next_user.display_name or next_user.username
            except:
                next_requester = "Unknown"

            embed.add_field(
                name="▶️ Now Playing",
                value=f"**[{next_track.title}]({next_track.uri})**\n"
                      f"By: {next_track.author}\n"
                      f"Duration: `{next_duration_minutes}:{next_duration_seconds:02d}`\n"
                      f"Requested by: {next_requester}",
                inline=False
            )

            # Show queue status
            remaining_tracks = len(player.queue) - 1  # Subtract 1 since we just started playing the first queued track
            if remaining_tracks > 0:
                embed.add_field(
                    name="📋 Queue Status",
                    value=f"{remaining_tracks} tracks remaining",
                    inline=True
                )

            # Show repeat mode if active
            repeat_mode = self.repeat_modes.get(ctx.guild_id, 0)
            if repeat_mode == 1:
                embed.add_field(
                    name="🔂 Repeat Mode",
                    value="Track repeat",
                    inline=True
                )
            elif repeat_mode == 2:
                embed.add_field(
                    name="🔁 Repeat Mode",
                    value="Queue repeat",
                    inline=True
                )
        else:
            # No next track
            embed.add_field(
                name="📭 Queue Empty",
                value="No more tracks in queue",
                inline=False
            )

            embed.add_field(
                name="💡 Tip",
                value="Use `/play` to add more music!",
                inline=False
            )

        embed.add_field(
            name="👤 Skipped by",
            value=ctx.author.mention,
            inline=True
        )

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="queue",
        description="Show the current queue with detailed information",
        aliases=["q"],
        permission_node="music.play",
        arguments=[
            CommandArgument("page", hikari.OptionType.INTEGER, "Page number (shows 5 tracks per page)", required=False, default=1)
        ],
    )
    async def queue_command(self, ctx: lightbulb.Context, page: int = 1) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await self.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        # Check if anything is playing or queued
        total_tracks = len(player.queue)
        if not player.current and total_tracks == 0:
            embed = self.create_embed(
                title="📋 Queue is Empty",
                description="No tracks in queue. Use `/play` to add some music!",
                color=hikari.Color(0x888888)
            )
            await self.smart_respond(ctx, embed=embed)
            return

        # Calculate pagination
        tracks_per_page = 5
        max_pages = max(1, (total_tracks + tracks_per_page - 1) // tracks_per_page)

        if page < 1 or page > max_pages:
            await self.smart_respond(ctx, f"Invalid page. Please use a page between 1 and {max_pages}.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        start_idx = (page - 1) * tracks_per_page
        end_idx = min(start_idx + tracks_per_page, total_tracks)

        # Create rich embed
        embed = self.create_embed(
            title="📋 Music Queue",
            color=hikari.Color(0x0099FF)
        )

        # Now playing section
        if player.current:
            current_pos = player.position
            duration = player.current.duration
            current_minutes = current_pos // 60000
            current_seconds = (current_pos % 60000) // 1000
            duration_minutes = duration // 60000
            duration_seconds = (duration % 60000) // 1000

            # Status emoji
            status_emoji = "⏸️" if player.paused else "▶️"

            embed.add_field(
                name=f"{status_emoji} Now Playing",
                value=f"**[{player.current.title}]({player.current.uri})**\n"
                      f"By: {player.current.author}\n"
                      f"Position: `{current_minutes}:{current_seconds:02d}` / `{duration_minutes}:{duration_seconds:02d}`",
                inline=False
            )

        # Queue section
        if total_tracks > 0:
            queue_text = []
            for i in range(start_idx, end_idx):
                track = player.queue[i]
                duration_minutes = track.duration // 60000
                duration_seconds = (track.duration % 60000) // 1000

                # Get requester info
                try:
                    user = await ctx.bot.rest.fetch_user(track.requester)
                    requester_name = user.display_name or user.username
                except:
                    requester_name = "Unknown"

                queue_text.append(
                    f"`{i + 1}.` **[{track.title}]({track.uri})**\n"
                    f"    └ By: {track.author} | Duration: `{duration_minutes}:{duration_seconds:02d}` | Added by: {requester_name}"
                )

            if queue_text:
                embed.add_field(
                    name=f"🎵 Up Next (Page {page}/{max_pages})",
                    value="\n\n".join(queue_text),
                    inline=False
                )

        # Queue summary
        summary_parts = []
        summary_parts.append(f"**{total_tracks}** tracks in queue")

        if total_tracks > 0:
            # Calculate total duration
            total_duration = sum(track.duration for track in player.queue)
            total_minutes = total_duration // 60000
            total_hours = total_minutes // 60
            remaining_minutes = total_minutes % 60

            if total_hours > 0:
                summary_parts.append(f"Total duration: `{total_hours}h {remaining_minutes}m`")
            else:
                summary_parts.append(f"Total duration: `{total_minutes}m`")

        # Add repeat mode info
        repeat_mode = self.repeat_modes.get(ctx.guild_id, 0)
        if repeat_mode == 1:
            summary_parts.append("🔂 Repeat: Track")
        elif repeat_mode == 2:
            summary_parts.append("🔁 Repeat: Queue")

        embed.add_field(
            name="ℹ️ Queue Info",
            value="\n".join(summary_parts),
            inline=True
        )

        # Volume info
        embed.add_field(
            name="🔊 Volume",
            value=f"{player.volume}%",
            inline=True
        )

        # Pagination info
        if max_pages > 1:
            embed.set_footer(text=f"Page {page} of {max_pages} • Use /queue <page> to view other pages")

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="remove",
        description="Remove a track from the queue by position",
        aliases=["rm"],
        permission_node="music.manage",
        arguments=[
            CommandArgument("position", hikari.OptionType.INTEGER, "Position in queue to remove (1-based)")
        ],
    )
    async def remove_track(self, ctx: lightbulb.Context, position: int) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or len(player.queue) == 0:
            await self.smart_respond(ctx, "The queue is empty.", ephemeral=True)
            return

        # Validate position (convert from 1-based to 0-based)
        if position < 1 or position > len(player.queue):
            await self.smart_respond(ctx, f"Invalid position. Please use a number between 1 and {len(player.queue)}.", ephemeral=True)
            return

        # Remove the track
        removed_track = player.queue.pop(position - 1)

        # Get requester info
        try:
            user = await ctx.bot.rest.fetch_user(removed_track.requester)
            requester_name = user.display_name or user.username
        except:
            requester_name = "Unknown"

        embed = self.create_embed(
            title="🗑️ Track Removed",
            description=f"Removed **[{removed_track.title}]({removed_track.uri})**\n"
                       f"Originally added by: {requester_name}",
            color=hikari.Color(0xFF6B6B)
        )

        # Show new queue position info
        remaining_tracks = len(player.queue)
        embed.add_field(
            name="📋 Queue Status",
            value=f"{remaining_tracks} tracks remaining in queue",
            inline=True
        )

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="move",
        description="Move a track to a different position in the queue",
        permission_node="music.manage",
        arguments=[
            CommandArgument("from_position", hikari.OptionType.INTEGER, "Current position of track (1-based)"),
            CommandArgument("to_position", hikari.OptionType.INTEGER, "New position for track (1-based)")
        ],
    )
    async def move_track(self, ctx: lightbulb.Context, from_position: int, to_position: int) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or len(player.queue) == 0:
            await self.smart_respond(ctx, "The queue is empty.", ephemeral=True)
            return

        queue_length = len(player.queue)

        # Validate positions
        if from_position < 1 or from_position > queue_length:
            await self.smart_respond(ctx, f"Invalid 'from' position. Please use a number between 1 and {queue_length}.", ephemeral=True)
            return

        if to_position < 1 or to_position > queue_length:
            await self.smart_respond(ctx, f"Invalid 'to' position. Please use a number between 1 and {queue_length}.", ephemeral=True)
            return

        if from_position == to_position:
            await self.smart_respond(ctx, "Track is already at that position.", ephemeral=True)
            return

        # Convert to 0-based indexing
        from_idx = from_position - 1
        to_idx = to_position - 1

        # Move the track
        track = player.queue.pop(from_idx)
        player.queue.insert(to_idx, track)

        embed = self.create_embed(
            title="🔄 Track Moved",
            description=f"Moved **[{track.title}]({track.uri})**\n"
                       f"From position #{from_position} to #{to_position}",
            color=hikari.Color(0x4CAF50)
        )

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="clear",
        description="Clear the queue (keeps currently playing track)",
        permission_node="music.manage",
    )
    async def clear_queue(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await self.smart_respond(ctx, "No player found.", ephemeral=True)
            return

        if len(player.queue) == 0:
            await self.smart_respond(ctx, "The queue is already empty.", ephemeral=True)
            return

        tracks_removed = len(player.queue)
        player.queue.clear()

        embed = self.create_embed(
            title="🧹 Queue Cleared",
            description=f"Removed **{tracks_removed}** tracks from the queue",
            color=hikari.Color(0xFF9800)
        )

        if player.current:
            embed.add_field(
                name="▶️ Still Playing",
                value=f"**{player.current.title}** will continue playing",
                inline=False
            )

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="join",
        description="Join your voice channel",
        permission_node="music.play",
    )
    async def join_voice(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        # Check if user is in voice channel
        voice_state = ctx.bot.hikari_bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
        if not voice_state or not voice_state.channel_id:
            await self.smart_respond(ctx, "You must be in a voice channel for me to join.", ephemeral=True)
            return

        # Get or create player
        player = self.lavalink_client.player_manager.create(ctx.guild_id)

        # Check if already connected to the same channel
        if player.is_connected and player.channel_id == voice_state.channel_id:
            await self.smart_respond(ctx, "I'm already in your voice channel.", ephemeral=True)
            return

        # Connect to voice channel
        await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, voice_state.channel_id)

        # Get channel name for display
        try:
            channel = await ctx.bot.rest.fetch_channel(voice_state.channel_id)
            channel_name = channel.name
        except:
            channel_name = "Unknown Channel"

        embed = self.create_embed(
            title="🔗 Joined Voice Channel",
            description=f"Connected to **{channel_name}**",
            color=hikari.Color(0x00FF00)
        )

        embed.add_field(
            name="🎵 Ready to Play",
            value="Use `/play` to start playing music!",
            inline=False
        )

        await self.smart_respond(ctx, embed=embed)

    async def _check_voice_channel_empty(self, guild_id: int, channel_id: int) -> None:
        """Check if voice channel is empty and start disconnect timer if needed."""
        try:
            # Get voice states for the channel
            voice_states = [
                vs for vs in self.bot.hikari_bot.cache.get_voice_states_view_for_guild(guild_id).values()
                if vs.channel_id == channel_id and not vs.member.is_bot
            ]

            if len(voice_states) == 0:
                # Channel is empty, start disconnect timer
                await self._start_disconnect_timer(guild_id)
            else:
                # Channel has users, cancel any existing timer
                await self._cancel_disconnect_timer(guild_id)

        except Exception as e:
            logger.error(f"Error checking voice channel: {e}")

    async def _start_disconnect_timer(self, guild_id: int) -> None:
        """Start auto-disconnect timer for a guild."""
        # Cancel any existing timer
        await self._cancel_disconnect_timer(guild_id)

        # Start new timer (5 minutes = 300 seconds)
        async def disconnect_after_delay():
            await asyncio.sleep(300)  # 5 minutes
            try:
                player = self.lavalink_client.player_manager.get(guild_id)
                if player and player.is_connected:
                    # Double-check if channel is still empty
                    if player.channel_id:
                        voice_states = [
                            vs for vs in self.bot.hikari_bot.cache.get_voice_states_view_for_guild(guild_id).values()
                            if vs.channel_id == player.channel_id and not vs.member.is_bot
                        ]

                        if len(voice_states) == 0:
                            # Still empty, disconnect
                            await player.stop()
                            player.queue.clear()
                            await self.bot.hikari_bot.update_voice_state(guild_id, None)
                            logger.info(f"Auto-disconnected from empty voice channel in guild {guild_id}")

                # Clean up timer reference
                self.disconnect_timers.pop(guild_id, None)

            except Exception as e:
                logger.error(f"Error during auto-disconnect: {e}")

        # Store the task
        task = asyncio.create_task(disconnect_after_delay())
        self.disconnect_timers[guild_id] = task

    async def _cancel_disconnect_timer(self, guild_id: int) -> None:
        """Cancel auto-disconnect timer for a guild."""
        if guild_id in self.disconnect_timers:
            task = self.disconnect_timers.pop(guild_id)
            if not task.done():
                task.cancel()

    @command(
        name="disconnect",
        description="Disconnect from voice channel",
        aliases=["leave"],
        permission_node="music.manage",
    )
    async def disconnect(self, ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = self.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.is_connected:
            await self.smart_respond(ctx, "I'm not connected to a voice channel.", ephemeral=True)
            return

        # Cancel any disconnect timer
        await self._cancel_disconnect_timer(ctx.guild_id)

        # Get channel name for display
        channel_name = "Unknown Channel"
        if player.channel_id:
            try:
                channel = await ctx.bot.rest.fetch_channel(player.channel_id)
                channel_name = channel.name
            except:
                pass

        # Stop music and disconnect
        await player.stop()
        player.queue.clear()
        await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, None)

        embed = self.create_embed(
            title="👋 Disconnected",
            description=f"Left **{channel_name}** and cleared the queue",
            color=hikari.Color(0xFF9800)
        )

        await self.smart_respond(ctx, embed=embed)

    @command(
        name="search",
        description="Search for tracks and choose from multiple results",
        permission_node="music.play",
        arguments=[
            CommandArgument("query", hikari.OptionType.STRING, "Song name or artist to search for")
        ],
    )
    async def search_tracks(self, ctx: lightbulb.Context, query: str) -> None:
        if not ctx.guild_id:
            await self.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        # Check if user is in voice channel
        voice_state = ctx.bot.hikari_bot.cache.get_voice_state(ctx.guild_id, ctx.author.id)
        if not voice_state or not voice_state.channel_id:
            await self.smart_respond(ctx, "You must be in a voice channel to use this command.", ephemeral=True)
            return

        # Search for tracks
        try:
            search_result = await self.lavalink_client.get_tracks(f"ytsearch:{query}")

            if not search_result.tracks:
                embed = self.create_embed(
                    title="🔍 No Results",
                    description=f"No tracks found for: `{query}`",
                    color=hikari.Color(0xFF6B6B)
                )
                await self.smart_respond(ctx, embed=embed, ephemeral=True)
                return

            # Create search results embed
            embed = self.create_embed(
                title="🔍 Search Results",
                description=f"Found {len(search_result.tracks)} results for: **{query}**\n\nSelect a track from the dropdown below to add it to the queue.",
                color=hikari.Color(0x0099FF)
            )

            # Add track list to embed
            tracks_text = ""
            for i, track in enumerate(search_result.tracks[:5]):
                duration_minutes = track.duration // 60000
                duration_seconds = (track.duration % 60000) // 1000
                tracks_text += f"`{i + 1}.` **{track.title}**\n    └ By: {track.author} | Duration: `{duration_minutes}:{duration_seconds:02d}`\n\n"

            embed.add_field(
                name="🎵 Tracks Found",
                value=tracks_text,
                inline=False
            )

            embed.add_field(
                name="ℹ️ How to Use",
                value="• Use the dropdown menu below to select a track\n• Only you can select from your search results\n• Selection expires in 60 seconds",
                inline=False
            )

            # Create interactive view
            view = SearchResultView(self, ctx.guild_id, search_result.tracks, ctx.author.id)

            # Check if miru client is available
            miru_client = getattr(self.bot, "miru_client", None)
            if miru_client and view.children:
                message = await ctx.respond(embed=embed, components=view)
                miru_client.start_view(view)

                # Store message reference for timeout handling
                if hasattr(message, 'message'):
                    view.message = message.message
                elif hasattr(message, 'id'):
                    view.message = message
            else:
                # Fallback without interactive controls - just show the first result
                first_track = search_result.tracks[0]

                # Get or create player
                player = self.lavalink_client.player_manager.create(ctx.guild_id)

                # Connect to voice channel if not connected
                if not player.is_connected:
                    await ctx.bot.hikari_bot.update_voice_state(ctx.guild_id, voice_state.channel_id)

                # Add to queue and play
                player.add(requester=ctx.author.id, track=first_track)

                was_playing = player.is_playing
                if not was_playing:
                    await player.play()

                # Show result
                duration_minutes = first_track.duration // 60000
                duration_seconds = (first_track.duration % 60000) // 1000

                fallback_embed = self.create_embed(
                    title="🎵 Added First Result",
                    description=f"**[{first_track.title}]({first_track.uri})**\nBy: {first_track.author}\nDuration: `{duration_minutes}:{duration_seconds:02d}`",
                    color=hikari.Color(0x00FF00)
                )

                await self.smart_respond(ctx, embed=fallback_embed)

        except Exception as e:
            logger.error(f"Error in search command: {e}")
            embed = self.create_embed(
                title="❌ Search Error",
                description="Failed to search for tracks. Please try again.",
                color=hikari.Color(0xFF0000)
            )
            await self.smart_respond(ctx, embed=embed, ephemeral=True)

    async def _handle_playlist_add(self, ctx, search_result, player, channel_id: int) -> None:
        """Handle adding a playlist to the queue."""
        tracks = search_result.tracks

        # Connect if not connected
        if not player.is_connected:
            await self.bot.hikari_bot.update_voice_state(ctx.guild_id, channel_id)

        # Add all tracks to queue
        added_count = 0
        for track in tracks:
            player.add(requester=ctx.author.id, track=track)
            added_count += 1

        # Start playing if nothing was playing
        was_playing = player.is_playing
        if not was_playing and len(tracks) > 0:
            await player.play()

        # Calculate total duration
        total_duration = sum(track.duration for track in tracks)
        total_minutes = total_duration // 60000
        total_hours = total_minutes // 60
        remaining_minutes = total_minutes % 60

        # Create response embed
        embed = self.create_embed(
            title="📋 Playlist Added",
            color=hikari.Color(0x00FF00)
        )

        playlist_name = "Unknown Playlist"
        if hasattr(search_result, 'playlist_info') and search_result.playlist_info:
            # PlaylistInfo is an object, not a dict - access attributes directly
            playlist_name = getattr(search_result.playlist_info, 'name', 'Unknown Playlist') or 'Unknown Playlist'

        embed.add_field(
            name="📄 Playlist",
            value=f"**{playlist_name}**",
            inline=False
        )

        embed.add_field(
            name="🎵 Tracks Added",
            value=f"{added_count} tracks",
            inline=True
        )

        if total_hours > 0:
            duration_str = f"{total_hours}h {remaining_minutes}m"
        else:
            duration_str = f"{total_minutes}m"

        embed.add_field(
            name="⏱️ Total Duration",
            value=duration_str,
            inline=True
        )

        embed.add_field(
            name="👤 Requested by",
            value=ctx.author.mention,
            inline=True
        )

        status = "🎵 Now Playing" if not was_playing else "📋 Added to Queue"
        embed.add_field(
            name="📍 Status",
            value=status,
            inline=False
        )

        await self.smart_respond(ctx, embed=embed)

    async def _save_queue_to_db(self, guild_id: int) -> None:
        """Save the current queue to database for persistence."""
        if guild_id in self._restoring_queues:
            return  # Don't save while restoring

        try:
            player = self.lavalink_client.player_manager.get(guild_id)
            if not player:
                return

            async with self.bot.db.session() as session:
                from datetime import datetime
                from bot.database.models import MusicQueue, MusicSession

                # Clear existing queue entries
                await session.execute(
                    "DELETE FROM music_queues WHERE guild_id = :guild_id",
                    {"guild_id": guild_id}
                )

                # Save current queue
                for position, track in enumerate(player.queue):
                    queue_entry = MusicQueue(
                        guild_id=guild_id,
                        position=position,
                        track_identifier=track.identifier,
                        track_title=track.title,
                        track_author=track.author,
                        track_duration=track.duration,
                        track_uri=track.uri,
                        requester_id=track.requester
                    )
                    session.add(queue_entry)

                # Save or update session info
                session_data = await session.get(MusicSession, guild_id)
                if session_data:
                    session_data.is_playing = player.is_playing
                    session_data.is_paused = player.paused
                    session_data.volume = player.volume
                    repeat_mode = self.repeat_modes.get(guild_id, 0)
                    session_data.repeat_mode = "off" if repeat_mode == 0 else ("track" if repeat_mode == 1 else "queue")
                    session_data.current_track_position = player.position
                    session_data.last_activity = datetime.utcnow()
                else:
                    # Create new session
                    repeat_mode = self.repeat_modes.get(guild_id, 0)
                    session_data = MusicSession(
                        guild_id=guild_id,
                        voice_channel_id=player.channel_id or 0,
                        text_channel_id=0,  # We don't track this currently
                        is_playing=player.is_playing,
                        is_paused=player.paused,
                        volume=player.volume,
                        repeat_mode="off" if repeat_mode == 0 else ("track" if repeat_mode == 1 else "queue"),
                        current_track_position=player.position
                    )
                    session.add(session_data)

                await session.commit()
                logger.debug(f"Saved queue for guild {guild_id}: {len(player.queue)} tracks")

        except Exception as e:
            logger.error(f"Error saving queue for guild {guild_id}: {e}")

    async def _restore_queue_from_db(self, guild_id: int) -> bool:
        """Restore queue from database after bot restart."""
        if guild_id in self._restoring_queues:
            return False

        try:
            self._restoring_queues.add(guild_id)

            async with self.bot.db.session() as session:
                from bot.database.models import MusicQueue, MusicSession
                from sqlalchemy import select

                # Get session info
                session_data = await session.get(MusicSession, guild_id)
                if not session_data:
                    return False

                # Get queue tracks
                result = await session.execute(
                    select(MusicQueue)
                    .where(MusicQueue.guild_id == guild_id)
                    .order_by(MusicQueue.position)
                )
                queue_tracks = result.scalars().all()

                if not queue_tracks:
                    return False

                # Get or create player
                player = self.lavalink_client.player_manager.create(guild_id)

                # Restore session settings
                await player.set_volume(session_data.volume)
                if session_data.repeat_mode == "track":
                    self.repeat_modes[guild_id] = 1
                elif session_data.repeat_mode == "queue":
                    self.repeat_modes[guild_id] = 2
                else:
                    self.repeat_modes[guild_id] = 0

                # Restore queue tracks
                restored_count = 0
                for queue_track in queue_tracks:
                    try:
                        # Try to get the track from Lavalink
                        search_result = await self.lavalink_client.get_tracks(queue_track.track_uri)
                        if search_result.tracks:
                            track = search_result.tracks[0]
                            # Override requester to match stored data
                            track.requester = queue_track.requester_id
                            player.add(track=track)
                            restored_count += 1
                        else:
                            logger.warning(f"Could not restore track: {queue_track.track_title}")
                    except Exception as e:
                        logger.error(f"Error restoring track {queue_track.track_title}: {e}")

                logger.info(f"Restored queue for guild {guild_id}: {restored_count}/{len(queue_tracks)} tracks")
                return restored_count > 0

        except Exception as e:
            logger.error(f"Error restoring queue for guild {guild_id}: {e}")
            return False
        finally:
            self._restoring_queues.discard(guild_id)

    async def _clear_queue_from_db(self, guild_id: int) -> None:
        """Clear queue from database when player is stopped."""
        try:
            async with self.bot.db.session() as session:
                # Clear queue entries
                await session.execute(
                    "DELETE FROM music_queues WHERE guild_id = :guild_id",
                    {"guild_id": guild_id}
                )
                # Clear session
                await session.execute(
                    "DELETE FROM music_sessions WHERE guild_id = :guild_id",
                    {"guild_id": guild_id}
                )
                await session.commit()
                logger.debug(f"Cleared persistent queue for guild {guild_id}")
        except Exception as e:
            logger.error(f"Error clearing queue from database for guild {guild_id}: {e}")