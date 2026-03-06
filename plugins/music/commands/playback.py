import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..utils import handle_playlist_add, save_queue_to_db
from ..views import SourceSelectView


async def _broadcast_music_update(plugin, guild_id: int, update_type: str):
    """Broadcast music update to WebSocket clients."""
    try:
        from ..web import broadcast_music_update
        await broadcast_music_update(guild_id, plugin, update_type)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error broadcasting music update for guild {guild_id}: {e}")


def setup_playback_commands(plugin):
    """Setup playback-related commands on the plugin."""

    @command(
        name="play",
        description="Play a song",
        permission_node="basic.music.playback.control",
        aliases=["p"],
        arguments=[CommandArgument("query", hikari.OptionType.STRING, "Song name or URL to play")],
    )
    async def play(ctx: lightbulb.Context, query: str) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        voice_state = plugin.get_voice_state(ctx.guild_id, ctx.author.id)
        if not voice_state or not voice_state.channel_id:
            await plugin.smart_respond(ctx, "You must be in a voice channel to use this command.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.create(ctx.guild_id)

        if not player.is_connected:
            await plugin.update_voice_state(ctx.guild_id, voice_state.channel_id)

        if query.startswith(("http://", "https://")):
            search_result = await plugin.lavalink_client.get_tracks(query)

            if not search_result.tracks:
                await plugin.smart_respond(ctx, f"No tracks found for: `{query}`", flags=hikari.MessageFlag.EPHEMERAL)
                return

            if len(search_result.tracks) > 1:
                await handle_playlist_add(plugin, ctx, search_result, player, voice_state.channel_id)
                return

            track = search_result.tracks[0]
        else:
            search_result = await plugin.lavalink_client.get_tracks(f"ytmsearch:{query}")

            if not search_result.tracks:
                embed = plugin.create_embed(
                    title="🔍 No Results on YouTube Music",
                    description=f"Nothing found for: **{query}**\n\nTry a different source:",
                    color=hikari.Color(0xFF9800),
                )
                view = SourceSelectView(plugin, ctx.guild_id, query, ctx.author.id, voice_state.channel_id)
                miru_client = getattr(plugin.bot, "miru_client", None)
                if miru_client and view.children:
                    message = await ctx.respond(embed=embed, components=view)
                    miru_client.start_view(view, bind_to=message)
                else:
                    await plugin.smart_respond(ctx, embed=embed)
                return

            track = search_result.tracks[0]

        player.add(requester=ctx.author.id, track=track)

        was_playing = player.is_playing
        if not was_playing:
            await player.play()

        await save_queue_to_db(plugin, ctx.guild_id)

        # Broadcast update to WebSocket clients
        await _broadcast_music_update(plugin, ctx.guild_id, "queue_update")

        duration_minutes = track.duration // 60000
        duration_seconds = (track.duration % 60000) // 1000

        if was_playing:
            queue_position = len(player.queue)

            embed = plugin.create_embed(title="🎵 Added to Queue", color=hikari.Color(0x00FF00))

            embed.add_field(name="🎶 Track", value=f"**[{track.title}]({track.uri})**\nBy: {track.author}", inline=False)

            embed.add_field(name="📍 Position", value=f"#{queue_position} in queue", inline=True)

            embed.add_field(name="⏱️ Duration", value=f"`{duration_minutes}:{duration_seconds:02d}`", inline=True)

            embed.add_field(name="👤 Requested by", value=ctx.author.mention, inline=True)

            if queue_position > 1:
                current_remaining = player.current.duration - player.position if player.current else 0
                queue_before_duration = sum(t.duration for t in list(player.queue)[:-1])
                total_wait_time = current_remaining + queue_before_duration

                wait_minutes = total_wait_time // 60000
                wait_hours = wait_minutes // 60
                remaining_wait_minutes = wait_minutes % 60

                if wait_hours > 0:
                    wait_time_str = f"`{wait_hours}h {remaining_wait_minutes}m`"
                else:
                    wait_time_str = f"`{wait_minutes}m`"

                embed.add_field(name="⏰ Estimated Wait", value=wait_time_str, inline=True)
        else:
            embed = plugin.create_embed(title="🎵 Now Playing", color=hikari.Color(0x00FF00))

            embed.add_field(name="🎶 Track", value=f"**[{track.title}]({track.uri})**\nBy: {track.author}", inline=False)

            embed.add_field(name="⏱️ Duration", value=f"`{duration_minutes}:{duration_seconds:02d}`", inline=True)

            embed.add_field(name="👤 Requested by", value=ctx.author.mention, inline=True)

            status_parts = []
            status_parts.append(f"🔊 Volume: {player.volume}%")

            repeat_mode = plugin.repeat_modes.get(ctx.guild_id, 0)
            if repeat_mode == 1:
                status_parts.append("🔂 Repeat: Track")
            elif repeat_mode == 2:
                status_parts.append("🔁 Repeat: Queue")

            embed.add_field(name="ℹ️ Status", value="\n".join(status_parts), inline=True)

        if hasattr(track, "artwork_url") and track.artwork_url:
            embed.set_thumbnail(track.artwork_url)

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="pause",
        description="Pause the current track",
        permission_node="basic.music.playback.control",
    )
    async def pause(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.is_playing:
            await plugin.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if player.paused:
            await plugin.smart_respond(ctx, "The track is already paused.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.set_pause(True)

        # Broadcast update to WebSocket clients
        await _broadcast_music_update(plugin, ctx.guild_id, "playback_update")

        embed = plugin.create_embed(title="⏸️ Paused", description=f"Paused: **{player.current.title}**", color=hikari.Color(0xFFFF00))
        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="resume",
        description="Resume the current track",
        permission_node="basic.music.playback.control",
    )
    async def resume(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await plugin.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if not player.paused:
            await plugin.smart_respond(ctx, "The track is not paused.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.set_pause(False)

        # Broadcast update to WebSocket clients
        await _broadcast_music_update(plugin, ctx.guild_id, "playback_update")

        embed = plugin.create_embed(
            title="▶️ Resumed", description=f"Resumed: **{player.current.title}**", color=hikari.Color(0x00FF00)
        )
        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="stop",
        description="Stop the music and clear the queue",
        permission_node="basic.music.playback.control",
    )
    async def stop(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await plugin.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player.queue.clear()
        await player.stop()
        await plugin.update_voice_state(ctx.guild_id, None)

        from ..utils import clear_queue_from_db

        await clear_queue_from_db(plugin, ctx.guild_id)

        # Broadcast update to WebSocket clients
        await _broadcast_music_update(plugin, ctx.guild_id, "playback_update")

        embed = plugin.create_embed(
            title="⏹️ Stopped", description="Stopped the music and cleared the queue.", color=hikari.Color(0xFF0000)
        )
        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="skip",
        description="Skip the current track",
        permission_node="basic.music.playback.control",
    )
    async def skip(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.is_playing:
            await plugin.smart_respond(ctx, "Nothing is currently playing.", ephemeral=True)
            return

        current_track = player.current
        current_title = current_track.title if current_track else "Unknown Track"

        # Check repeat mode before skipping
        repeat_mode = plugin.repeat_modes.get(ctx.guild_id, 0)

        # Handle repeat track mode explicitly
        if repeat_mode == 1 and current_track:
            # Add the current track back to the front of the queue for repeat track
            player.add(track=current_track, index=0)

        next_track = None
        if len(player.queue) > 0:
            next_track = player.queue[0]

        await player.skip()

        # Small delay to ensure skip is processed
        import asyncio
        await asyncio.sleep(0.1)

        # Ensure playback continues if we have tracks in queue
        if not player.is_playing and player.queue:
            await player.play()

        await save_queue_to_db(plugin, ctx.guild_id)

        # Broadcast update to WebSocket clients
        await _broadcast_music_update(plugin, ctx.guild_id, "playback_update")

        embed = plugin.create_embed(title="⏭️ Track Skipped", color=hikari.Color(0x00FF00))

        embed.add_field(name="🎵 Skipped", value=f"**{current_title}**", inline=False)

        if next_track:
            next_duration_minutes = next_track.duration // 60000
            next_duration_seconds = (next_track.duration % 60000) // 1000

            try:
                next_user = await plugin.fetch_user(next_track.requester)
                next_requester = next_user.display_name or next_user.username
            except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError):
                next_requester = "Unknown"

            embed.add_field(
                name="▶️ Now Playing",
                value=f"**[{next_track.title}]({next_track.uri})**\n"
                f"By: {next_track.author}\n"
                f"Duration: `{next_duration_minutes}:{next_duration_seconds:02d}`\n"
                f"Requested by: {next_requester}",
                inline=False,
            )

            remaining_tracks = len(player.queue) - 1
            if remaining_tracks > 0:
                embed.add_field(name="📋 Queue Status", value=f"{remaining_tracks} tracks remaining", inline=True)

            repeat_mode = plugin.repeat_modes.get(ctx.guild_id, 0)
            if repeat_mode == 1:
                embed.add_field(name="🔂 Repeat Mode", value="Track repeat", inline=True)
            elif repeat_mode == 2:
                embed.add_field(name="🔁 Repeat Mode", value="Queue repeat", inline=True)
        else:
            embed.add_field(name="📭 Queue Empty", value="No more tracks in queue", inline=False)

            embed.add_field(name="💡 Tip", value="Use `/play` to add more music!", inline=False)

        embed.add_field(name="👤 Skipped by", value=ctx.author.mention, inline=True)

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="seek",
        description="Seek to a specific position in the track (format: mm:ss or seconds)",
        permission_node="basic.music.playback.control",
        arguments=[CommandArgument("position", hikari.OptionType.STRING, "Position to seek to (mm:ss or seconds)")],
    )
    async def seek(ctx: lightbulb.Context, position: str) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await plugin.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        try:
            if ":" in position:
                parts = position.split(":")
                if len(parts) != 2:
                    raise ValueError("Invalid format")
                minutes, seconds = int(parts[0]), int(parts[1])
                seek_position = (minutes * 60 + seconds) * 1000
            else:
                seek_position = int(position) * 1000
        except ValueError:
            await plugin.smart_respond(ctx, "Invalid position format. Use mm:ss or seconds.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if seek_position < 0 or seek_position > player.current.duration:
            await plugin.smart_respond(ctx, "Position is out of track bounds.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        await player.seek(seek_position)

        seek_minutes = seek_position // 60000
        seek_seconds = (seek_position % 60000) // 1000

        embed = plugin.create_embed(
            title="🎯 Seeked",
            description=f"Seeked to **{seek_minutes}:{seek_seconds:02d}** in **{player.current.title}**",
            color=hikari.Color(0x00FF00),
        )
        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="position",
        description="Show current position in the track",
        permission_node="basic.music.playback.control",
    )
    async def position(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or not player.current:
            await plugin.smart_respond(ctx, "Nothing is currently playing.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        current_pos = player.position
        duration = player.current.duration

        current_minutes = current_pos // 60000
        current_seconds = (current_pos % 60000) // 1000
        duration_minutes = duration // 60000
        duration_seconds = (duration % 60000) // 1000

        progress_percentage = current_pos / duration if duration > 0 else 0
        bar_length = 20
        filled_length = int(bar_length * progress_percentage)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        embed = plugin.create_embed(
            title="📍 Track Position",
            description=f"**{player.current.title}**\n"
            f"`{current_minutes}:{current_seconds:02d}` {bar} `{duration_minutes}:{duration_seconds:02d}`\n"
            f"Progress: {progress_percentage:.1%}",
            color=hikari.Color(0x0099FF),
        )
        await plugin.smart_respond(ctx, embed=embed)

    return [play, pause, resume, stop, skip, seek, position]
