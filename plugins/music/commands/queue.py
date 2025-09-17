import random

import hikari
import lightbulb

from bot.plugins.commands import CommandArgument, command

from ..utils import save_queue_to_db


def setup_queue_commands(plugin):
    """Setup queue management commands on the plugin."""

    @command(
        name="queue",
        description="Show the current queue with detailed information",
        aliases=["q"],
        permission_node="music.play",
        arguments=[
            CommandArgument("page", hikari.OptionType.INTEGER, "Page number (shows 5 tracks per page)", required=False, default=1)
        ],
    )
    async def queue_command(ctx: lightbulb.Context, page: int = 1) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await plugin.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        total_tracks = len(player.queue)
        if not player.current and total_tracks == 0:
            embed = plugin.create_embed(
                title="📋 Queue is Empty",
                description="No tracks in queue. Use `/play` to add some music!",
                color=hikari.Color(0x888888),
            )
            await plugin.smart_respond(ctx, embed=embed)
            return

        tracks_per_page = 5
        max_pages = max(1, (total_tracks + tracks_per_page - 1) // tracks_per_page)

        if page < 1 or page > max_pages:
            await plugin.smart_respond(
                ctx, f"Invalid page. Please use a page between 1 and {max_pages}.", flags=hikari.MessageFlag.EPHEMERAL
            )
            return

        start_idx = (page - 1) * tracks_per_page
        end_idx = min(start_idx + tracks_per_page, total_tracks)

        embed = plugin.create_embed(title="📋 Music Queue", color=hikari.Color(0x0099FF))

        if player.current:
            current_pos = player.position
            duration = player.current.duration
            current_minutes = current_pos // 60000
            current_seconds = (current_pos % 60000) // 1000
            duration_minutes = duration // 60000
            duration_seconds = (duration % 60000) // 1000

            status_emoji = "⏸️" if player.paused else "▶️"

            embed.add_field(
                name=f"{status_emoji} Now Playing",
                value=f"**[{player.current.title}]({player.current.uri})**\n"
                f"By: {player.current.author}\n"
                f"Position: `{current_minutes}:{current_seconds:02d}` / `{duration_minutes}:{duration_seconds:02d}`",
                inline=False,
            )

        if total_tracks > 0:
            queue_text = []
            for i in range(start_idx, end_idx):
                track = player.queue[i]
                duration_minutes = track.duration // 60000
                duration_seconds = (track.duration % 60000) // 1000

                try:
                    user = await ctx.bot.rest.fetch_user(track.requester)
                    requester_name = user.display_name or user.username
                except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError):
                    requester_name = "Unknown"

                queue_text.append(
                    f"`{i + 1}.` **[{track.title}]({track.uri})**\n"
                    f"    └ By: {track.author} | Duration: `{duration_minutes}:{duration_seconds:02d}` | Added by: {requester_name}"
                )

            if queue_text:
                embed.add_field(name=f"🎵 Up Next (Page {page}/{max_pages})", value="\n\n".join(queue_text), inline=False)

        summary_parts = []
        summary_parts.append(f"**{total_tracks}** tracks in queue")

        if total_tracks > 0:
            total_duration = sum(track.duration for track in player.queue)
            total_minutes = total_duration // 60000
            total_hours = total_minutes // 60
            remaining_minutes = total_minutes % 60

            if total_hours > 0:
                summary_parts.append(f"Total duration: `{total_hours}h {remaining_minutes}m`")
            else:
                summary_parts.append(f"Total duration: `{total_minutes}m`")

        repeat_mode = plugin.repeat_modes.get(ctx.guild_id, 0)
        if repeat_mode == 1:
            summary_parts.append("🔂 Repeat: Track")
        elif repeat_mode == 2:
            summary_parts.append("🔁 Repeat: Queue")

        embed.add_field(name="ℹ️ Queue Info", value="\n".join(summary_parts), inline=True)

        embed.add_field(name="🔊 Volume", value=f"{player.volume}%", inline=True)

        if max_pages > 1:
            embed.set_footer(text=f"Page {page} of {max_pages} • Use /queue <page> to view other pages")

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="shuffle",
        description="Shuffle the current queue",
        permission_node="music.play",
    )
    async def shuffle(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await plugin.smart_respond(ctx, "No player found.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        if len(player.queue) < 2:
            await plugin.smart_respond(ctx, "Need at least 2 tracks in the queue to shuffle.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        queue_list = list(player.queue)
        random.shuffle(queue_list)

        player.queue.clear()
        for track in queue_list:
            player.queue.append(track)

        await save_queue_to_db(plugin, ctx.guild_id)

        embed = plugin.create_embed(
            title="🔀 Queue Shuffled", description=f"Shuffled **{len(queue_list)}** tracks in the queue", color=hikari.Color(0x00FF00)
        )
        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="loop",
        description="Toggle loop modes: off -> track -> queue -> off",
        aliases=["repeat"],
        permission_node="music.play",
        arguments=[CommandArgument("mode", hikari.OptionType.STRING, "Loop mode: off, track, or queue", required=False)],
    )
    async def loop(ctx: lightbulb.Context, mode: str = None) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", flags=hikari.MessageFlag.EPHEMERAL)
            return

        current_mode = plugin.repeat_modes.get(ctx.guild_id, 0)

        if mode is None:
            new_mode = (current_mode + 1) % 3
        else:
            mode = mode.lower()
            if mode in ["off", "none", "0"]:
                new_mode = 0
            elif mode in ["track", "song", "1"]:
                new_mode = 1
            elif mode in ["queue", "all", "2"]:
                new_mode = 2
            else:
                await plugin.smart_respond(ctx, "Invalid mode. Use: `off`, `track`, or `queue`", flags=hikari.MessageFlag.EPHEMERAL)
                return

        plugin.repeat_modes[ctx.guild_id] = new_mode

        if new_mode == 0:
            embed = plugin.create_embed(title="🔁 Loop Off", description="Loop mode disabled", color=hikari.Color(0xFF0000))
        elif new_mode == 1:
            embed = plugin.create_embed(title="🔂 Loop Track", description="Current track will repeat", color=hikari.Color(0x00FF00))
        else:
            embed = plugin.create_embed(
                title="🔁 Loop Queue", description="Queue will repeat when finished", color=hikari.Color(0x0099FF)
            )

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="remove",
        description="Remove a track from the queue by position",
        aliases=["rm"],
        permission_node="music.manage",
        arguments=[CommandArgument("position", hikari.OptionType.INTEGER, "Position in queue to remove (1-based)")],
    )
    async def remove_track(ctx: lightbulb.Context, position: int) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or len(player.queue) == 0:
            await plugin.smart_respond(ctx, "The queue is empty.", ephemeral=True)
            return

        if position < 1 or position > len(player.queue):
            await plugin.smart_respond(
                ctx, f"Invalid position. Please use a number between 1 and {len(player.queue)}.", ephemeral=True
            )
            return

        removed_track = player.queue.pop(position - 1)
        await save_queue_to_db(plugin, ctx.guild_id)

        try:
            user = await ctx.bot.rest.fetch_user(removed_track.requester)
            requester_name = user.display_name or user.username
        except (hikari.NotFoundError, hikari.ForbiddenError, hikari.HTTPError):
            requester_name = "Unknown"

        embed = plugin.create_embed(
            title="🗑️ Track Removed",
            description=f"Removed **[{removed_track.title}]({removed_track.uri})**\n" f"Originally added by: {requester_name}",
            color=hikari.Color(0xFF6B6B),
        )

        remaining_tracks = len(player.queue)
        embed.add_field(name="📋 Queue Status", value=f"{remaining_tracks} tracks remaining in queue", inline=True)

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="move",
        description="Move a track to a different position in the queue",
        permission_node="music.manage",
        arguments=[
            CommandArgument("from_position", hikari.OptionType.INTEGER, "Current position of track (1-based)"),
            CommandArgument("to_position", hikari.OptionType.INTEGER, "New position for track (1-based)"),
        ],
    )
    async def move_track(ctx: lightbulb.Context, from_position: int, to_position: int) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player or len(player.queue) == 0:
            await plugin.smart_respond(ctx, "The queue is empty.", ephemeral=True)
            return

        queue_length = len(player.queue)

        if from_position < 1 or from_position > queue_length:
            await plugin.smart_respond(
                ctx, f"Invalid 'from' position. Please use a number between 1 and {queue_length}.", ephemeral=True
            )
            return

        if to_position < 1 or to_position > queue_length:
            await plugin.smart_respond(
                ctx, f"Invalid 'to' position. Please use a number between 1 and {queue_length}.", ephemeral=True
            )
            return

        if from_position == to_position:
            await plugin.smart_respond(ctx, "Track is already at that position.", ephemeral=True)
            return

        from_idx = from_position - 1
        to_idx = to_position - 1

        track = player.queue.pop(from_idx)
        player.queue.insert(to_idx, track)

        await save_queue_to_db(plugin, ctx.guild_id)

        embed = plugin.create_embed(
            title="🔄 Track Moved",
            description=f"Moved **[{track.title}]({track.uri})**\n" f"From position #{from_position} to #{to_position}",
            color=hikari.Color(0x4CAF50),
        )

        await plugin.smart_respond(ctx, embed=embed)

    @command(
        name="clear",
        description="Clear the queue (keeps currently playing track)",
        permission_node="music.manage",
    )
    async def clear_queue(ctx: lightbulb.Context) -> None:
        if not ctx.guild_id:
            await plugin.smart_respond(ctx, "This command can only be used in a server.", ephemeral=True)
            return

        player = plugin.lavalink_client.player_manager.get(ctx.guild_id)

        if not player:
            await plugin.smart_respond(ctx, "No player found.", ephemeral=True)
            return

        if len(player.queue) == 0:
            await plugin.smart_respond(ctx, "The queue is already empty.", ephemeral=True)
            return

        tracks_removed = len(player.queue)
        player.queue.clear()

        await save_queue_to_db(plugin, ctx.guild_id)

        embed = plugin.create_embed(
            title="🧹 Queue Cleared", description=f"Removed **{tracks_removed}** tracks from the queue", color=hikari.Color(0xFF9800)
        )

        if player.current:
            embed.add_field(name="▶️ Still Playing", value=f"**{player.current.title}** will continue playing", inline=False)

        await plugin.smart_respond(ctx, embed=embed)

    return [queue_command, shuffle, loop, remove_track, move_track, clear_queue]
